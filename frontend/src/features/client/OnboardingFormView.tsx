import { useState } from 'react'
import { ClipboardList, Pencil, Check, X } from 'lucide-react'
import type { QuestionSchemaItem } from '@/hooks/useDocuments'
import { useUpdateCollectedField } from '@/hooks/useDocuments'

const SYSTEM_KEYS = new Set(['selected_products', 'version', 'created_at', 'updated_at'])

// Fields the client cannot edit — add question_key values here to lock a field
const NON_EDITABLE_KEYS = new Set<string>([
  'full_name_signature',
  'final_confirmation',
])

function hasValue(v: unknown): boolean {
  if (v === null || v === undefined) return false
  if (typeof v === 'string' && v.trim() === '') return false
  if (Array.isArray(v) && v.length === 0) return false
  return true
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return ''
  if (Array.isArray(v)) return v.join(', ')
  if (typeof v === 'number') return v.toLocaleString()
  return String(v)
}

function formatKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

function sectionTitle(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

function isSignature(key: string): boolean {
  return key.toLowerCase().includes('signature')
}

// ── Client-side validation (mirrors backend validate_value) ───────────────────

function validateField(
  value: string | string[],
  item: QuestionSchemaItem,
): string | null {
  const rules = item.validation_rules
  if (!rules) return null

  if (item.field_type === 'multi_choice') {
    if ((value as string[]).length === 0) return 'Please select at least one option.'
    return null
  }

  const v = String(value).trim()

  // Only enforce min_length when the rule is explicitly set — do NOT default to 1
  if (typeof rules.min_length === 'number' && v.length < rules.min_length)
    return `Must be at least ${rules.min_length} character(s).`
  if (typeof rules.max_length === 'number' && v.length > rules.max_length)
    return `Must be ${rules.max_length} characters or fewer.`

  if (rules.alphanumeric) {
    if (!/^[a-zA-Z0-9]+$/.test(v)) return 'Must contain only letters and numbers — no spaces or special characters.'
    if (typeof rules.max_alphanumeric === 'number' && v.length > rules.max_alphanumeric)
      return `Must be ${rules.max_alphanumeric} characters or fewer.`
  }

  if (rules.min_digits !== undefined || rules.max_digits !== undefined) {
    const digits = v.replace(/\D/g, '')
    if (typeof rules.min_digits === 'number' && digits.length < rules.min_digits)
      return `Must contain at least ${rules.min_digits} digits.`
    if (typeof rules.max_digits === 'number' && digits.length > rules.max_digits)
      return `Must contain no more than ${rules.max_digits} digits.`
  }

  if (rules.postal_code) {
    if (!/^[a-zA-Z0-9][\s\-a-zA-Z0-9]{2,9}$/.test(v))
      return 'Please enter a valid postal code (e.g. 10001 or SW1A 1AA).'
  }

  if (rules.min_age !== undefined && item.field_type === 'date') {
    const parts = v.split('/')
    if (parts.length !== 3) return 'Please enter a valid date in DD/MM/YYYY format.'
    const dob = new Date(+parts[2], +parts[1] - 1, +parts[0])
    const today = new Date()
    const age =
      today.getFullYear() -
      dob.getFullYear() -
      (today.getMonth() * 100 + today.getDate() < dob.getMonth() * 100 + dob.getDate() ? 1 : 0)
    if (typeof rules.min_age === 'number' && age < rules.min_age)
      return `You must be at least ${rules.min_age} years old to open an account.`
  }

  if (rules.future_date && item.field_type === 'date') {
    const parts = v.split('/')
    if (parts.length !== 3) return 'Please enter a valid date in DD/MM/YYYY format.'
    const d = new Date(+parts[2], +parts[1] - 1, +parts[0])
    if (d <= new Date()) return 'The expiration date must be in the future.'
  }

  return null
}

// ── Edit inputs ───────────────────────────────────────────────────────────────

interface ChoiceInputProps {
  options: string[]
  value: string
  onChange: (v: string) => void
}

function ChoiceInput({ options, value, onChange }: ChoiceInputProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-blue-300 bg-white px-3 py-1.5 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
    >
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  )
}

interface MultiChoiceInputProps {
  options: string[]
  values: string[]
  onChange: (v: string[]) => void
}

function MultiChoiceInput({ options, values, onChange }: MultiChoiceInputProps) {
  function toggle(opt: string) {
    onChange(values.includes(opt) ? values.filter((v) => v !== opt) : [...values, opt])
  }
  return (
    <div className="space-y-1.5 rounded-lg border border-blue-300 bg-white px-3 py-2">
      {options.map((opt) => (
        <label key={opt} className="flex cursor-pointer items-center gap-2">
          <input
            type="checkbox"
            checked={values.includes(opt)}
            onChange={() => toggle(opt)}
            className="h-3.5 w-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-800">{opt}</span>
        </label>
      ))}
    </div>
  )
}

// ── Component ─────────────────────────────────────────────────────────────────

interface RenderedField {
  question_key: string
  label: string
}

interface OnboardingFormViewProps {
  caseId: string | null
  clientData: Record<string, unknown>
  schema: QuestionSchemaItem[]
  isLoading?: boolean
}

export default function OnboardingFormView({
  caseId,
  clientData,
  schema,
  isLoading,
}: OnboardingFormViewProps) {
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [editMultiValues, setEditMultiValues] = useState<string[]>([])
  const [editError, setEditError] = useState<string | null>(null)
  const updateField = useUpdateCollectedField(caseId)

  // Full schema item lookup for field_type / options / validation_rules
  const schemaMap = new Map<string, QuestionSchemaItem>()
  for (const item of schema) schemaMap.set(item.question_key, item)

  function startEdit(questionKey: string) {
    const item = schemaMap.get(questionKey)
    const raw = clientData[questionKey]
    setEditingKey(questionKey)
    setEditError(null)
    if (item?.field_type === 'multi_choice') {
      setEditMultiValues(Array.isArray(raw) ? (raw as string[]) : [])
      setEditValue('')
    } else {
      setEditValue(raw === null || raw === undefined ? '' : String(raw))
      setEditMultiValues([])
    }
  }

  function cancelEdit() {
    setEditingKey(null)
    setEditValue('')
    setEditMultiValues([])
    setEditError(null)
  }

  function saveEdit() {
    if (!editingKey) return
    const item = schemaMap.get(editingKey)
    const isMulti = item?.field_type === 'multi_choice'
    const rawValue = isMulti ? editMultiValues : editValue

    if (item) {
      const err = validateField(rawValue, item)
      if (err) { setEditError(err); return }
    }

    // Preserve numeric type for number fields
    let valueToSave: unknown = rawValue
    if (!isMulti && (item?.field_type === 'number')) {
      const n = parseFloat((rawValue as string).replace(/,/g, ''))
      if (!isNaN(n)) valueToSave = n
    }

    updateField.mutate(
      { questionKey: editingKey, value: valueToSave },
      {
        onSuccess: () => {
          setEditingKey(null)
          setEditValue('')
          setEditMultiValues([])
          setEditError(null)
        },
      },
    )
  }

  function handleEditKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') saveEdit()
    if (e.key === 'Escape') cancelEdit()
  }

  // ── Section / field grouping ───────────────────────────────────────────────

  const sectionOrder: string[] = []
  for (const item of schema) {
    if (!sectionOrder.includes(item.section)) sectionOrder.push(item.section)
  }

  const sectionMap = new Map<string, RenderedField[]>()
  for (const item of schema) {
    if (!hasValue(clientData[item.question_key])) continue
    if (!sectionMap.has(item.section)) sectionMap.set(item.section, [])
    sectionMap.get(item.section)!.push({ question_key: item.question_key, label: item.label })
  }

  for (const [key, value] of Object.entries(clientData)) {
    if (SYSTEM_KEYS.has(key) || !hasValue(value) || schemaMap.has(key)) continue
    if (!sectionMap.has('other')) sectionMap.set('other', [])
    sectionMap.get('other')!.push({ question_key: key, label: formatKey(key) })
  }

  const orderedSections: string[] = [
    ...sectionOrder.filter((s) => sectionMap.has(s)),
    ...(sectionMap.has('other') ? ['other'] : []),
  ]

  const totalAnswered = [...sectionMap.values()].reduce((sum, fields) => sum + fields.length, 0)

  // ── Skeleton ──────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-3 p-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-3 h-4 w-32 rounded bg-gray-200 dark:bg-gray-700" />
            <div className="space-y-2">
              <div className="h-8 rounded-lg bg-gray-100 dark:bg-gray-700" />
              <div className="h-8 rounded-lg bg-gray-100 dark:bg-gray-700" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  // ── Empty state ───────────────────────────────────────────────────────────
  if (orderedSections.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="rounded-full bg-blue-50 p-4 dark:bg-blue-950">
          <ClipboardList className="h-7 w-7 text-blue-400" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200">Your answers will appear here</p>
          <p className="mt-1 text-xs text-gray-400">
            As you chat with the assistant, your responses are captured in this form
          </p>
        </div>
      </div>
    )
  }

  // ── Filled state ──────────────────────────────────────────────────────────
  return (
    <div className="flex h-full flex-col">
      {/* Summary bar */}
      <div className="shrink-0 border-b border-gray-100 px-4 py-2.5 dark:border-gray-700">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-blue-700">{totalAnswered}</span>
          <span className="text-xs text-gray-400">
            field{totalAnswered !== 1 ? 's' : ''} collected
          </span>
        </div>
      </div>

      {/* Scrollable sections */}
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {orderedSections.map((sectionKey) => {
          const fields = sectionMap.get(sectionKey) ?? []
          return (
            <div
              key={sectionKey}
              className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
            >
              <div className="border-b border-gray-100 bg-gray-50 px-4 py-2 dark:border-gray-700 dark:bg-gray-700/50">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {sectionTitle(sectionKey)}
                </h3>
              </div>

              <div className="divide-y divide-gray-50 dark:divide-gray-700">
                {fields.map(({ question_key, label }) => {
                  const isEditing = editingKey === question_key
                  const item = schemaMap.get(question_key)

                  return (
                    <div key={question_key} className="group px-4 py-3">
                      {/* Label row */}
                      <div className="mb-1 flex items-center justify-between">
                        <p className="text-[10px] font-medium uppercase tracking-wide text-gray-400">
                          {label}
                        </p>
                        {!isEditing && !NON_EDITABLE_KEYS.has(question_key) && (
                          <button
                            onClick={() => startEdit(question_key)}
                            title={`Correct ${label}`}
                            className="invisible group-hover:visible flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-blue-500 hover:bg-blue-50 transition-colors dark:hover:bg-blue-950"
                          >
                            <Pencil className="h-2.5 w-2.5" />
                            Correct
                          </button>
                        )}
                      </div>

                      {/* Value — edit mode or readonly */}
                      {isEditing ? (
                        <div className="space-y-1.5">
                          {/* Field-type-aware input */}
                          {item?.field_type === 'choice' && item.options ? (
                            <ChoiceInput
                              options={item.options}
                              value={editValue}
                              onChange={(v) => { setEditValue(v); setEditError(null) }}
                            />
                          ) : item?.field_type === 'multi_choice' && item.options ? (
                            <MultiChoiceInput
                              options={item.options}
                              values={editMultiValues}
                              onChange={(v) => { setEditMultiValues(v); setEditError(null) }}
                            />
                          ) : (
                            <input
                              autoFocus
                              type={item?.field_type === 'number' ? 'number' : 'text'}
                              placeholder={item?.field_type === 'date' ? 'DD/MM/YYYY' : isSignature(question_key) ? 'Sign here…' : undefined}
                              value={editValue}
                              onChange={(e) => { setEditValue(e.target.value); setEditError(null) }}
                              onKeyDown={handleEditKeyDown}
                              className="w-full rounded-lg border border-blue-300 bg-white px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                              style={isSignature(question_key)
                                ? { fontFamily: "'Dancing Script', cursive", fontSize: '1.25rem', color: '#1e3a5f' }
                                : { fontSize: '0.875rem' }
                              }
                            />
                          )}

                          {/* Validation error */}
                          {editError && (
                            <p className="text-[11px] font-medium text-red-500">{editError}</p>
                          )}

                          {/* Save / Cancel */}
                          <div className="flex justify-end gap-1.5">
                            <button
                              onClick={cancelEdit}
                              className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-2.5 py-1 text-[11px] font-medium text-gray-500 hover:bg-gray-50 transition-colors dark:border-gray-600 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600"
                            >
                              <X className="h-3 w-3" />
                              Cancel
                            </button>
                            <button
                              onClick={saveEdit}
                              disabled={updateField.isPending}
                              className="flex items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-blue-700 disabled:opacity-60 transition-colors"
                            >
                              <Check className="h-3 w-3" />
                              {updateField.isPending ? 'Saving…' : 'Save'}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className={[
                          'rounded-lg border border-gray-100 bg-gray-50 px-3 py-1.5 dark:border-gray-700 dark:bg-gray-700',
                          isSignature(question_key) ? 'bg-white dark:bg-gray-800' : '',
                        ].join(' ')}>
                          <p
                            className="break-words text-gray-800 dark:text-gray-100"
                            style={isSignature(question_key)
                              ? { fontFamily: "'Dancing Script', cursive", fontSize: '1.25rem', lineHeight: '1.6', color: '#1e3a5f' }
                              : { fontSize: '0.875rem' }
                            }
                          >
                            {formatValue(clientData[question_key])}
                          </p>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
