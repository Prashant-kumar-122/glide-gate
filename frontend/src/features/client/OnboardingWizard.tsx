import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowLeft, ArrowRight, CheckCircle, Upload, Star, Users, Building2,
  Globe, Zap, FileText, Loader, Sparkles, X, ChevronDown, ChevronLeft,
  ChevronRight, AlertCircle, Calendar,
} from 'lucide-react'
import {
  useProducts, useQuestionnaireSchema, useCollectedFields,
  useUpdateCollectedField, useInitiateCase, useUpdateCaseProducts, useCases,
} from '@/hooks/useDocuments'
import { normalizeDateToISO } from '@/lib/dateUtils'
import { api } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import DocumentUploadStep from '@/features/client/DocumentUploadStep'
import type { ProductOut } from '@/lib/api'
import type { QuestionSchemaItem } from '@/hooks/useDocuments'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatSectionTitle(section: string): string {
  const overrides: Record<string, string> = {
    personal: 'Personal Information',
    financial: 'Financial Information',
    tax: 'Tax Information',
    risk: 'Risk Profile',
    employment: 'Employment Details',
    identity: 'Identity Verification',
    background: 'Background Information',
  }
  return overrides[section] ?? section.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

function sectionIcon(section: string) {
  const map: Record<string, typeof Users> = {
    personal: Users,
    financial: Building2,
    tax: Globe,
    risk: Zap,
    employment: FileText,
    identity: CheckCircle,
    background: FileText,
  }
  return map[section] ?? FileText
}

// ── Validation helpers ────────────────────────────────────────────────────────

function isRequired(field: QuestionSchemaItem): boolean {
  return (field.validation_rules as Record<string, unknown>)?.required === true
}

// Normalise a value for comparison: lowercase, replace hyphens/spaces with underscore
function normalise(v: unknown): string {
  return typeof v === 'string' ? v.toLowerCase().replace(/[-\s]+/g, '_') : String(v ?? '')
}

function isFieldVisible(field: QuestionSchemaItem, data: Record<string, unknown>): boolean {
  const si = field.show_if
  if (!si) return true
  const current = data[si.field]
  switch (si.operator) {
    case 'eq':
      return normalise(current) === normalise(si.value)
    case 'in':
      return Array.isArray(si.value) &&
        (si.value as unknown[]).some((v) => normalise(v) === normalise(current))
    case 'contains':
      return Array.isArray(current) &&
        (current as unknown[]).some((v) => normalise(v) === normalise(si.value))
    case 'gt':
      return typeof current === 'number' && current > (si.value as number)
    default:
      return true
  }
}

function validateFieldValue(field: QuestionSchemaItem, value: unknown): string | null {
  const rules = (field.validation_rules ?? {}) as Record<string, unknown>

  if (rules.required) {
    if (value === undefined || value === null || value === '')
      return 'This field is required.'
    if (Array.isArray(value) && value.length === 0)
      return 'Please select at least one option.'
  }

  if (value === undefined || value === null || value === '') return null

  if (field.field_type === 'multi_choice') return null

  const v = String(value).trim()

  if (typeof rules.min_length === 'number' && v.length < rules.min_length)
    return `Must be at least ${rules.min_length} character(s).`
  if (typeof rules.max_length === 'number' && v.length > rules.max_length)
    return `Must be ${rules.max_length} characters or fewer.`

  if (rules.alphanumeric) {
    if (!/^[a-zA-Z0-9]+$/.test(v))
      return 'Must contain only letters and numbers — no spaces or special characters.'
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

  if (rules.min_age !== undefined && field.field_type === 'date') {
    const d = new Date(v)
    if (isNaN(d.getTime())) return 'Please enter a valid date.'
    const today = new Date()
    const age =
      today.getFullYear() -
      d.getFullYear() -
      (today.getMonth() * 100 + today.getDate() < d.getMonth() * 100 + d.getDate() ? 1 : 0)
    if (typeof rules.min_age === 'number' && age < rules.min_age)
      return `You must be at least ${rules.min_age} years old to open an account.`
  }

  if (rules.future_date && field.field_type === 'date') {
    const d = new Date(v)
    if (isNaN(d.getTime())) return 'Please enter a valid date.'
    if (d <= new Date()) return 'The date must be in the future.'
  }

  return null
}

// ── Step definitions ──────────────────────────────────────────────────────────

interface WizardStep {
  id: string
  title: string
  icon: typeof Star
}

function buildSteps(sections: string[]): WizardStep[] {
  return [
    { id: 'products',  title: 'Select Products',  icon: Star },
    { id: 'documents', title: 'Upload Documents',  icon: Upload },
    ...sections.map((s) => ({ id: s, title: formatSectionTitle(s), icon: sectionIcon(s) })),
    { id: 'review',    title: 'Review & Submit',   icon: CheckCircle },
  ]
}

// ── Custom date picker ────────────────────────────────────────────────────────

const MONTH_NAMES = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
]
const MONTH_SHORT = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
const DAY_LABELS  = ['Su','Mo','Tu','We','Th','Fr','Sa']

type PickerMode = 'day' | 'month' | 'year'

function DatePickerField({
  value,
  onChange,
  error,
}: {
  value: unknown
  onChange: (v: unknown) => void
  error?: string
}) {
  const strVal = value !== undefined && value !== null ? normalizeDateToISO(String(value)) : ''
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<PickerMode>('day')
  const containerRef = useRef<HTMLDivElement>(null)
  const yearListRef  = useRef<HTMLDivElement>(null)

  const today    = new Date()
  const selected = strVal ? new Date(strVal + 'T00:00:00') : null

  const [viewYear,  setViewYear]  = useState(() => selected?.getFullYear()  ?? today.getFullYear())
  const [viewMonth, setViewMonth] = useState(() => selected?.getMonth()     ?? today.getMonth())

  // Close on outside click
  useEffect(() => {
    function onOut(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false); setMode('day')
      }
    }
    if (open) document.addEventListener('mousedown', onOut)
    return () => document.removeEventListener('mousedown', onOut)
  }, [open])

  // Auto-scroll year list to selected year when entering year mode
  useEffect(() => {
    if (mode === 'year' && yearListRef.current) {
      const btn = yearListRef.current.querySelector<HTMLButtonElement>('[data-selected="true"]')
      btn?.scrollIntoView({ block: 'center' })
    }
  }, [mode])

  function prevStep() {
    if (mode === 'month') setViewYear((y) => y - 1)
    else if (mode === 'day') {
      if (viewMonth === 0) { setViewMonth(11); setViewYear((y) => y - 1) }
      else setViewMonth((m) => m - 1)
    }
  }
  function nextStep() {
    if (mode === 'month') setViewYear((y) => y + 1)
    else if (mode === 'day') {
      if (viewMonth === 11) { setViewMonth(0); setViewYear((y) => y + 1) }
      else setViewMonth((m) => m + 1)
    }
  }

  function selectDate(date: Date) {
    onChange([
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, '0'),
      String(date.getDate()).padStart(2, '0'),
    ].join('-'))
    setOpen(false); setMode('day')
  }

  function isSame(a: Date, b: Date) {
    return a.getFullYear() === b.getFullYear() &&
           a.getMonth()    === b.getMonth()    &&
           a.getDate()     === b.getDate()
  }

  // Day-grid cells
  const firstDow     = new Date(viewYear, viewMonth, 1).getDay()
  const daysInMonth  = new Date(viewYear, viewMonth + 1, 0).getDate()
  const prevMonthDays = new Date(viewYear, viewMonth, 0).getDate()
  const cells: { date: Date; thisMonth: boolean }[] = []
  for (let i = firstDow - 1; i >= 0; i--)
    cells.push({ date: new Date(viewYear, viewMonth - 1, prevMonthDays - i), thisMonth: false })
  for (let d = 1; d <= daysInMonth; d++)
    cells.push({ date: new Date(viewYear, viewMonth, d), thisMonth: true })
  while (cells.length < 42)
    cells.push({ date: new Date(viewYear, viewMonth + 1, cells.length - firstDow - daysInMonth + 1), thisMonth: false })

  const displayValue = selected
    ? `${MONTH_NAMES[selected.getMonth()]} ${selected.getDate()}, ${selected.getFullYear()}`
    : ''

  const hasError = !!error
  const ALL_YEARS = Array.from({ length: 131 }, (_, i) => today.getFullYear() - 120 + i)

  return (
    <div className="space-y-1.5">
      <div ref={containerRef} className="relative">

        {/* Trigger */}
        <button
          type="button"
          onClick={() => { setOpen((o) => !o); setMode('day') }}
          className={[
            'w-full flex items-center justify-between border px-3 py-2.5 text-sm bg-white transition-colors focus:outline-none focus:ring-1 dark:bg-gray-950 dark:text-gray-100',
            hasError  ? 'border-red-400 focus:ring-red-400'
            : open    ? 'border-primary ring-1 ring-primary'
            : 'border-gray-200 focus:ring-primary dark:border-gray-700',
            displayValue ? 'text-gray-900 dark:text-gray-100' : 'text-gray-400 dark:text-gray-500',
          ].join(' ')}
        >
          <span>{displayValue || 'Select a date…'}</span>
          <Calendar className="w-4 h-4 text-gray-400 shrink-0" />
        </button>

        {open && (
          <div className="absolute left-0 top-full mt-2 z-50 w-72 border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">

            {/* ── Header ── */}
            <div className="flex items-center justify-between mb-3">
              {mode !== 'year' && (
                <button
                  type="button"
                  onClick={prevStep}
                  className="w-7 h-7 flex items-center justify-center hover:bg-gray-100 text-gray-500 transition-colors shrink-0 dark:hover:bg-gray-800 dark:text-gray-400"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              )}

              <div className={`flex items-center gap-1 ${mode === 'year' ? 'w-full justify-center' : 'flex-1 justify-center'}`}>
                {/* Month button — hidden in year mode */}
                {mode !== 'year' && (
                  <button
                    type="button"
                    onClick={() => setMode((m) => m === 'month' ? 'day' : 'month')}
                    className={[
                      'px-2 py-1 text-sm font-semibold transition-colors',
                      mode === 'month'
                        ? 'bg-primary text-white'
                        : 'text-gray-800 hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-800',
                    ].join(' ')}
                  >
                    {MONTH_NAMES[viewMonth]}
                  </button>
                )}
                {/* Year button */}
                <button
                  type="button"
                  onClick={() => setMode((m) => m === 'year' ? 'day' : 'year')}
                  className={[
                    'px-2 py-1 text-sm font-semibold transition-colors',
                    mode === 'year'
                      ? 'bg-primary text-white'
                      : 'text-gray-800 hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-800',
                  ].join(' ')}
                >
                  {viewYear}
                </button>
              </div>

              {mode !== 'year' && (
                <button
                  type="button"
                  onClick={nextStep}
                  className="w-7 h-7 flex items-center justify-center hover:bg-gray-100 text-gray-500 transition-colors shrink-0 dark:hover:bg-gray-800 dark:text-gray-400"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* ── Month grid ── */}
            {mode === 'month' && (
              <div className="grid grid-cols-3 gap-1.5 py-1">
                {MONTH_SHORT.map((m, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => { setViewMonth(i); setMode('day') }}
                    className={[
                      'py-2 text-sm font-medium transition-all',
                      viewMonth === i
                        ? 'bg-primary text-white'
                        : 'text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800',
                    ].join(' ')}
                  >
                    {m}
                  </button>
                ))}
              </div>
            )}

            {/* ── Year grid ── */}
            {mode === 'year' && (
              <div
                ref={yearListRef}
                className="grid grid-cols-4 gap-1 max-h-52 overflow-y-auto py-1 pr-0.5"
              >
                {ALL_YEARS.map((y) => (
                  <button
                    key={y}
                    type="button"
                    data-selected={y === viewYear ? 'true' : 'false'}
                    onClick={() => { setViewYear(y); setMode('day') }}
                    className={[
                      'py-1.5 text-xs font-medium transition-all',
                      y === viewYear
                        ? 'bg-primary text-white'
                        : y === today.getFullYear()
                        ? 'ring-1 ring-primary text-primary dark:text-primary'
                        : 'text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800',
                    ].join(' ')}
                  >
                    {y}
                  </button>
                ))}
              </div>
            )}

            {/* ── Day grid ── */}
            {mode === 'day' && (
              <>
                <div className="grid grid-cols-7 mb-1">
                  {DAY_LABELS.map((d) => (
                    <div key={d} className="text-center text-[10px] font-semibold text-gray-400 py-1">{d}</div>
                  ))}
                </div>
                <div className="grid grid-cols-7 gap-y-0.5">
                  {cells.map(({ date, thisMonth }, i) => {
                    const isSel   = selected ? isSame(date, selected) : false
                    const isToday = isSame(date, today)
                    return (
                      <button
                        key={i}
                        type="button"
                        onClick={() => selectDate(date)}
                        className={[
                          'h-8 w-8 mx-auto flex items-center justify-center text-xs font-medium transition-all',
                          isSel
                            ? 'bg-primary text-white'
                            : isToday && thisMonth
                            ? 'ring-1 ring-primary text-primary font-semibold'
                            : thisMonth
                            ? 'text-gray-800 hover:bg-gray-100 dark:text-gray-100 dark:hover:bg-gray-800'
                            : 'text-gray-300 hover:bg-gray-50 dark:text-gray-600 dark:hover:bg-gray-800',
                        ].join(' ')}
                      >
                        {date.getDate()}
                      </button>
                    )
                  })}
                </div>
              </>
            )}

            {/* ── Footer ── */}
            {mode === 'day' && (
              <div className="mt-3 pt-2.5 border-t border-gray-100 flex justify-between items-center dark:border-gray-700">
                <button
                  type="button"
                  onClick={() => { onChange(''); setOpen(false) }}
                  className="text-xs text-gray-400 hover:text-gray-600 transition-colors dark:hover:text-gray-300"
                >
                  Clear
                </button>
                <button
                  type="button"
                  onClick={() => { selectDate(today); setViewYear(today.getFullYear()); setViewMonth(today.getMonth()) }}
                  className="text-xs font-medium text-primary hover:text-primary-hover transition-colors"
                >
                  Today
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      {error && <FieldError message={error} />}
    </div>
  )
}

// ── Custom select dropdown ────────────────────────────────────────────────────

function CustomSelectField({
  options,
  value,
  onChange,
  error,
}: {
  options: string[]
  value: unknown
  onChange: (v: unknown) => void
  error?: string
}) {
  const strVal = value !== undefined && value !== null ? String(value) : ''
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onOut(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', onOut)
    return () => document.removeEventListener('mousedown', onOut)
  }, [open])

  const hasError = !!error

  return (
    <div className="space-y-1.5">
      <div ref={containerRef} className="relative">

        {/* Trigger */}
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className={[
            'w-full flex items-center justify-between border px-3 py-2.5 text-sm bg-white transition-colors focus:outline-none focus:ring-1 dark:bg-gray-950',
            hasError  ? 'border-red-400 focus:ring-red-400'
            : open    ? 'border-primary ring-1 ring-primary'
            : 'border-gray-200 focus:ring-primary dark:border-gray-700',
            strVal ? 'text-gray-900 dark:text-gray-100' : 'text-gray-400 dark:text-gray-500',
          ].join(' ')}
        >
          <span>{strVal || 'Select an option…'}</span>
          <ChevronDown className={`w-4 h-4 text-gray-400 shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
        </button>

        {/* Dropdown list */}
        {open && (
          <div className="absolute left-0 top-full mt-1.5 z-50 w-full border border-gray-200 bg-white overflow-hidden dark:border-gray-700 dark:bg-gray-900">
            <div className="max-h-56 overflow-y-auto py-1">
              {options.map((o) => {
                const isSelected = strVal === o
                return (
                  <button
                    key={o}
                    type="button"
                    onClick={() => { onChange(o); setOpen(false) }}
                    className={[
                      'w-full flex items-center justify-between px-4 py-2.5 text-sm text-left transition-colors',
                      isSelected
                        ? 'bg-blue-50 text-primary font-medium dark:bg-primary-subtle dark:text-blue-300'
                        : 'text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-800',
                    ].join(' ')}
                  >
                    <span>{o}</span>
                    {isSelected && (
                      <svg className="w-4 h-4 text-primary shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>
      {error && <FieldError message={error} />}
    </div>
  )
}

// ── Field renderer ────────────────────────────────────────────────────────────

function SchemaField({
  field,
  value,
  onChange,
  error,
}: {
  field: QuestionSchemaItem
  value: unknown
  onChange: (v: unknown) => void
  error?: string
}) {
  const hasError = !!error
  const ringClass = hasError
    ? 'border-red-400 focus:ring-red-400'
    : 'border-gray-200 focus:ring-primary'
  const base = `w-full border px-3 py-2.5 text-sm text-gray-900 bg-white focus:outline-none focus:ring-1 transition-colors dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100 ${ringClass}`
  const strVal = value !== undefined && value !== null ? String(value) : ''

  // ── Choice: radio buttons (≤3 opts) or styled dropdown (4+) ─────────────
  if (field.field_type === 'choice' && field.options?.length) {
    if (field.options.length <= 3) {
      return (
        <div className="space-y-1.5">
          <div className="flex flex-wrap gap-5">
            {field.options.map((o) => {
              const selected = strVal === o
              return (
                <label
                  key={o}
                  className="flex items-center gap-2 cursor-pointer select-none"
                >
                  <div
                    className={[
                      'w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 transition-all',
                      selected
                        ? 'border-primary'
                        : hasError
                        ? 'border-red-400'
                        : 'border-gray-400',
                    ].join(' ')}
                  >
                    {selected && <div className="w-2 h-2 rounded-full bg-primary" />}
                  </div>
                  <span className={`text-sm font-medium ${selected ? 'text-primary' : 'text-gray-700'}`}>{o}</span>
                  <input
                    type="radio"
                    name={field.question_key}
                    value={o}
                    checked={selected}
                    onChange={() => onChange(o)}
                    className="sr-only"
                  />
                </label>
              )
            })}
          </div>
          {error && <FieldError message={error} />}
        </div>
      )
    }

    // Custom dropdown for larger option sets
    return (
      <CustomSelectField
        options={field.options}
        value={value}
        onChange={onChange}
        error={error}
      />
    )
  }

  // ── Multi-choice: styled card-checkboxes ──────────────────────────────────
  if (field.field_type === 'multi_choice' && field.options?.length) {
    const selected: string[] = Array.isArray(value) ? (value as string[]) : strVal ? [strVal] : []
    return (
      <div className="space-y-1.5">
        <div className="space-y-2">
          {field.options.map((o) => {
            const checked = selected.includes(o)
            return (
              <label
                key={o}
                className={[
                  'flex items-center gap-3 px-4 py-3 border-2 cursor-pointer transition-all',
                  checked
                    ? 'border-primary bg-blue-50 dark:bg-primary-subtle'
                    : hasError
                    ? 'border-red-200 hover:border-red-300 bg-white dark:bg-gray-900 dark:border-red-700 dark:hover:border-red-600'
                    : 'border-gray-200 hover:border-primary/50 bg-white dark:bg-gray-900 dark:border-gray-700 dark:hover:border-primary',
                ].join(' ')}
              >
                <div
                  className={[
                    'w-4 h-4 border-2 flex items-center justify-center shrink-0 transition-all',
                    checked
                      ? 'border-primary bg-primary'
                      : hasError
                      ? 'border-red-300 dark:border-red-500'
                      : 'border-gray-300 dark:border-gray-500',
                  ].join(' ')}
                >
                  {checked && (
                    <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
                <span className={`text-sm font-medium ${checked ? 'text-primary dark:text-blue-300' : 'text-gray-700 dark:text-gray-200'}`}>{o}</span>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...selected, o]
                      : selected.filter((x) => x !== o)
                    onChange(next)
                  }}
                  className="sr-only"
                />
              </label>
            )
          })}
        </div>
        {error && <FieldError message={error} />}
      </div>
    )
  }

  // ── Date picker ───────────────────────────────────────────────────────────
  if (field.field_type === 'date') {
    return <DatePickerField value={value} onChange={onChange} error={error} />
  }

  // ── Signature field ───────────────────────────────────────────────────────
  if (field.question_key === 'full_name_signature') {
    return (
      <div className="space-y-1.5">
        <div className={`relative w-full border bg-gray-50 px-4 py-3 dark:bg-gray-900 ${hasError ? 'border-red-400' : 'border-gray-200 dark:border-gray-700'}`}>
          <input
            type="text"
            value={strVal}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Sign your full name"
            className="w-full bg-transparent focus:outline-none text-gray-800 dark:text-gray-100 text-2xl placeholder:text-gray-300 dark:placeholder:text-gray-500 placeholder:text-lg"
          />
          <div className="absolute bottom-0 left-4 right-4 border-b border-gray-300 dark:border-gray-600" />
        </div>
        {error && <FieldError message={error} />}
      </div>
    )
  }

  // ── Text / number ─────────────────────────────────────────────────────────
  return (
    <div className="space-y-1.5">
      <input
        type={field.field_type === 'number' ? 'number' : 'text'}
        value={strVal}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`Enter ${field.label.toLowerCase()}`}
        className={base}
      />
      {error && <FieldError message={error} />}
    </div>
  )
}

function FieldError({ message }: { message: string }) {
  return (
    <p className="flex items-center gap-1.5 text-xs font-medium text-red-500">
      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
      {message}
    </p>
  )
}

// ── Product card ──────────────────────────────────────────────────────────────

function ProductCard({
  product,
  selected,
  onToggle,
}: {
  product: ProductOut
  selected: boolean
  onToggle: () => void
}) {
  return (
    <button
      onClick={onToggle}
      className={[
        'w-full text-left border-2 p-4 transition-all',
        selected
          ? 'border-primary bg-blue-50 dark:bg-primary-subtle'
          : 'border-gray-200 bg-white hover:border-primary/50 dark:border-gray-700 dark:bg-gray-900 dark:hover:border-primary',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-gray-900 truncate dark:text-gray-100">{product.name}</p>
          {product.description && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{product.description}</p>
          )}
        </div>
        <div
          className={[
            'w-5 h-5 border-2 shrink-0 mt-0.5 flex items-center justify-center transition-all',
            selected ? 'border-primary bg-primary' : 'border-gray-300',
          ].join(' ')}
        >
          {selected && (
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </div>
      </div>
    </button>
  )
}

// ── Review step ───────────────────────────────────────────────────────────────

function ReviewStep({
  schemaFields,
  localData,
  onSubmit,
  isSubmitting,
}: {
  caseId: string
  schemaFields: QuestionSchemaItem[]
  localData: Record<string, unknown>
  onSubmit: () => void
  isSubmitting: boolean
}) {
  const sections = [...new Set(schemaFields.map((f) => f.section))]
  const filledCount = schemaFields.filter(
    (f) => localData[f.question_key] !== undefined && localData[f.question_key] !== '',
  ).length

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">Review &amp; Submit</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {filledCount} of {schemaFields.length} fields completed. Please review before submitting.
        </p>
      </div>

      {sections.map((section) => {
        const fields = schemaFields.filter((f) => f.section === section && localData[f.question_key])
        if (fields.length === 0) return null
        return (
          <div key={section} className="border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-900">
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
              {formatSectionTitle(section)}
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
              {fields.map((f) => (
                <div key={f.question_key}>
                  <p className="text-xs text-gray-400">{f.label}</p>
                  <p className="text-sm font-medium text-gray-800 mt-0.5 dark:text-gray-100">
                    {Array.isArray(localData[f.question_key])
                      ? (localData[f.question_key] as string[]).join(', ')
                      : String(localData[f.question_key])}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )
      })}

      <div className="bg-gray-50 border border-gray-200 p-4 dark:bg-gray-900 dark:border-gray-700">
        <p className="text-xs text-gray-500 leading-relaxed dark:text-gray-400">
          By submitting this application, I confirm that all information provided is accurate and
          complete to the best of my knowledge. I understand that providing false information may
          result in rejection of my application.
        </p>
      </div>

      <button
        onClick={onSubmit}
        disabled={isSubmitting}
        className="w-full flex items-center justify-center gap-2 bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isSubmitting ? (
          <><Loader className="w-4 h-4 animate-spin" />Submitting…</>
        ) : (
          <><CheckCircle className="w-4 h-4" />Submit Application</>
        )}
      </button>
    </div>
  )
}

// ── Main wizard ───────────────────────────────────────────────────────────────

interface Props {
  initialCaseId?: string
  initialSelectedProducts?: string[]
  onComplete: (caseId: string) => void
  onCancel: () => void
}

export default function OnboardingWizard({
  initialCaseId,
  initialSelectedProducts,
  onComplete,
  onCancel,
}: Props) {
  const isResuming = !!initialCaseId
  const [caseId, setCaseId] = useState<string | null>(initialCaseId ?? null)
  const [step, setStep] = useState(isResuming ? 1 : 0)
  const resumeStepApplied = useRef(false)

  const [selectedProducts, setSelectedProducts] = useState<string[]>(initialSelectedProducts ?? [])
  const [prefillCount, setPrefillCount] = useState(0)
  const [showPrefillBanner, setShowPrefillBanner] = useState(false)
  const [localData, setLocalData] = useState<Record<string, unknown>>({})
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [creatingCase, setCreatingCase] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  const { user } = useAuthStore()
  const { data: existingCases = [] } = useCases()
  const { data: products = [], isLoading: productsLoading } = useProducts()
  const { data: schemaData, isLoading: schemaLoading } = useQuestionnaireSchema(caseId)
  const { data: collectedData } = useCollectedFields(caseId)
  const updateField = useUpdateCollectedField(caseId)
  const initiateCase = useInitiateCase()
  const updateCaseProducts = useUpdateCaseProducts(caseId)

  // Initialise local form data from collected-fields when they load
  useEffect(() => {
    if (collectedData?.client_data) {
      setLocalData((prev) => ({ ...collectedData.client_data, ...prev }))
    }
  }, [collectedData])

  // Clear field errors whenever the user navigates to a new step
  useEffect(() => {
    setFieldErrors({})
  }, [step])

  const schemaSections = useMemo(
    () => [...new Set(schemaData?.fields.map((f) => f.section) ?? [])],
    [schemaData],
  )

  const steps = useMemo(() => buildSteps(schemaSections), [schemaSections])

  // When resuming, jump to the first incomplete section instead of always landing on documents
  useEffect(() => {
    if (!isResuming || resumeStepApplied.current) return
    if (!schemaData || !collectedData || schemaSections.length === 0) return

    resumeStepApplied.current = true
    const fieldData = collectedData.client_data ?? {}

    for (let i = 0; i < schemaSections.length; i++) {
      const section = schemaSections[i]
      const fields = schemaData.fields.filter((f) => f.section === section)
      const visibleFields = fields.filter((f) => isFieldVisible(f, fieldData))
      const requiredFields = visibleFields.filter(isRequired)

      const isComplete = requiredFields.every((f) => {
        const v = fieldData[f.question_key]
        return !(v === undefined || v === null || v === '' || (Array.isArray(v) && v.length === 0))
      })

      if (!isComplete) {
        // Step 0 = products, 1 = documents, 2+ = schema sections
        setStep(2 + i)
        return
      }
    }

    // All sections filled → go straight to review
    setStep(steps.length - 1)
  }, [isResuming, schemaData, collectedData, schemaSections, steps])


  const totalSteps = steps.length
  const progressPct = Math.round((step / Math.max(totalSteps - 1, 1)) * 100)
  const currentStep = steps[step]

  // ── Visible fields for current section ────────────────────────────────────

  const currentSectionFields = useMemo(() => {
    if (!currentStep || currentStep.id === 'products' || currentStep.id === 'documents' || currentStep.id === 'review') return []
    return (schemaData?.fields.filter((f) => f.section === currentStep.id) ?? []).filter(
      (f) => isFieldVisible(f, localData),
    )
  }, [currentStep, schemaData, localData])

  // ── Can proceed check ─────────────────────────────────────────────────────

  function canProceed(): boolean {
    if (step === 0) return selectedProducts.length > 0
    if (step === 1) return true
    if (currentStep?.id === 'review') return true

    const requiredFields = currentSectionFields.filter(isRequired)
    if (requiredFields.length === 0) return true

    return requiredFields.every((f) => {
      const v = localData[f.question_key]
      if (v === undefined || v === null || v === '') return false
      if (Array.isArray(v) && v.length === 0) return false
      return true
    })
  }

  // ── Navigation ────────────────────────────────────────────────────────────

  async function handleProductsContinue() {
    if (selectedProducts.length === 0) return

    // Resuming an existing case — update products then advance
    if (caseId) {
      setCreatingCase(true)
      setCreateError(null)
      try {
        await updateCaseProducts.mutateAsync(selectedProducts)
        setStep(1)
      } catch {
        setCreateError('Failed to update products. Please try again.')
      } finally {
        setCreatingCase(false)
      }
      return
    }

    setCreatingCase(true)
    setCreateError(null)
    try {
      const paddedId = String(existingCases.length).padStart(2, '0')
      const caseName = `${user?.firstName ?? ''} ${user?.lastName ?? ''} ${paddedId}`.trim()
      const newCase = await initiateCase.mutateAsync({
        case_name: caseName,
        selected_products: selectedProducts,
        assigned_advisor_id: null,
      })
      setCaseId(newCase.id)
      setStep(1)
    } catch {
      setCreateError('Failed to create case. Please try again.')
    } finally {
      setCreatingCase(false)
    }
  }

  async function handleSectionContinue() {
    if (!caseId) return

    // Validate all visible fields in this section
    const errors: Record<string, string> = {}
    for (const field of currentSectionFields) {
      const err = validateFieldValue(field, localData[field.question_key])
      if (err) errors[field.question_key] = err
      if (field.question_key === 'full_name_signature' && !errors['full_name_signature']) {
        const sig = String(localData['full_name_signature'] ?? '').trim()
        const firstName = String(localData['first_name'] ?? '').trim()
        const lastName = String(localData['last_name'] ?? '').trim()
        const fullName = `${firstName} ${lastName}`.trim()
        if (sig && fullName && sig.toLowerCase() !== fullName.toLowerCase()) {
          errors['full_name_signature'] = `Signature must match your full name: ${fullName}`
        }
      }
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }

    // Persist dirty fields
    const initial = collectedData?.client_data ?? {}
    const dirty = currentSectionFields
      .map((f) => f.question_key)
      .filter((k) => {
        const cur = localData[k]
        const orig = initial[k]
        return cur !== undefined && cur !== orig
      })

    if (dirty.length > 0) {
      await Promise.allSettled(
        dirty.map((k) => updateField.mutateAsync({ questionKey: k, value: localData[k] })),
      )
    }

    const nextStep = step + 1
    const pct = Math.round((nextStep / Math.max(totalSteps - 1, 1)) * 60)
    try {
      await api.patch(`/cases/${caseId}/percentage`, { percentage: pct })
    } catch {
      // non-critical — continue anyway
    }

    setStep(nextStep)
  }

  async function handleDocumentsContinue() {
    if (!caseId) return
    const nextStep = step + 1
    const pct = Math.round((nextStep / Math.max(totalSteps - 1, 1)) * 60)
    try {
      await api.patch(`/cases/${caseId}/percentage`, { percentage: pct })
    } catch {
      // non-critical
    }
    setStep(nextStep)
  }

  async function handleSubmit() {
    if (!caseId) return
    setIsSubmitting(true)
    try {
      await api.post(`/cases/${caseId}/submit-intake`)
    } catch {
      // Case data is saved regardless; orchestrator will be retried on resume
    } finally {
      setIsSubmitting(false)
      onComplete(caseId)
    }
  }

  function handleBack() {
    if (step === 0) {
      onCancel()
    } else {
      setStep((s) => s - 1)
    }
  }

  function handleDocumentAnalysed(count: number) {
    setPrefillCount(count)
    if (count > 0) setShowPrefillBanner(true)
  }

  function handleFieldChange(key: string, value: unknown) {
    setLocalData((prev) => ({ ...prev, [key]: value }))
    // Clear error for this field once the user starts editing
    if (fieldErrors[key]) {
      setFieldErrors((prev) => {
        const next = { ...prev }
        delete next[key]
        return next
      })
    }
  }

  // ── Content renderer ───────────────────────────────────────────────────────

  function renderContent() {
    if (!currentStep) return null

    // Step 0: product selection
    if (currentStep.id === 'products') {
      return (
        <div className="space-y-5">
          <div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">Select Products</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Choose the accounts you'd like to open. You can select multiple products.
            </p>
          </div>

          {createError && (
            <div className="bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:border-red-800 dark:text-red-300">
              {createError}
            </div>
          )}

          {productsLoading ? (
            <div className="flex justify-center py-12">
              <div className="h-7 w-7 rounded-full border-2 border-gray-200 border-t-primary animate-spin" />
            </div>
          ) : products.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No products available.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {products.map((p) => (
                <ProductCard
                  key={p.id}
                  product={p}
                  selected={selectedProducts.includes(p.product_code)}
                  onToggle={() => {
                    setSelectedProducts((prev) =>
                      prev.includes(p.product_code)
                        ? prev.filter((x) => x !== p.product_code)
                        : [...prev, p.product_code],
                    )
                  }}
                />
              ))}
            </div>
          )}

          {selectedProducts.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-1">
              {selectedProducts.map((code) => {
                const p = products.find((x) => x.product_code === code)
                return (
                  <span
                    key={code}
                    className="inline-flex items-center gap-1.5 text-xs font-medium bg-blue-50 text-primary px-2.5 py-1"
                  >
                    {p?.name ?? code}
                    <button
                      onClick={() => setSelectedProducts((prev) => prev.filter((x) => x !== code))}
                      className="hover:text-primary-hover"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )
              })}
            </div>
          )}
        </div>
      )
    }

    // Step 1: document upload
    if (currentStep.id === 'documents' && caseId) {
      return (
        <DocumentUploadStep
          caseId={caseId}
          onAnalysed={handleDocumentAnalysed}
          onSkip={() => setStep((s) => s + 1)}
        />
      )
    }

    // Review step
    if (currentStep.id === 'review' && caseId && schemaData) {
      return (
        <ReviewStep
          caseId={caseId}
          schemaFields={schemaData.fields}
          localData={localData}
          onSubmit={handleSubmit}
          isSubmitting={isSubmitting}
        />
      )
    }

    // Schema section steps
    if (caseId) {
      if (schemaLoading) {
        return (
          <div className="flex justify-center py-12">
            <div className="h-7 w-7 rounded-full border-2 border-gray-200 border-t-primary animate-spin" />
          </div>
        )
      }

      const hasErrors = Object.keys(fieldErrors).length > 0

      return (
        <div className="space-y-5">
          {/* Pre-fill banner */}
          {showPrefillBanner && prefillCount > 0 && (
            <div className="flex items-start gap-3 bg-violet-50 border border-violet-200 px-4 py-3">
              <Sparkles className="w-4 h-4 text-violet-500 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="text-xs text-violet-800">
                  <strong>{prefillCount} fields pre-filled</strong> from your documents.
                  Please review all values before continuing.
                </span>
              </div>
              <button
                onClick={() => setShowPrefillBanner(false)}
                className="text-violet-400 hover:text-violet-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Validation error banner */}
          {hasErrors && (
            <div className="flex items-center gap-3 bg-red-50 border border-red-200 px-4 py-3">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
              <span className="text-xs font-medium text-red-700">
                Please fill in all required fields before continuing.
              </span>
            </div>
          )}

          {currentSectionFields.length === 0 ? (
            <p className="text-sm text-gray-400 py-4">No fields for this section.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-5">
              {currentSectionFields.map((field) => (
                <div
                  key={field.question_key}
                  className={
                    field.field_type === 'multi_choice' ||
                    (field.field_type === 'choice' && (field.options?.length ?? 0) <= 3)
                      ? 'sm:col-span-2'
                      : ''
                  }
                >
                  <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">
                    {field.question_text || field.label}
                    {isRequired(field) && (
                      <span className="ml-0.5 text-red-500">*</span>
                    )}
                  </label>
                  <SchemaField
                    field={field}
                    value={localData[field.question_key]}
                    onChange={(v) => handleFieldChange(field.question_key, v)}
                    error={fieldErrors[field.question_key]}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    return null
  }

  const ready = canProceed()

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-gray-50 dark:bg-gray-950">
      {/* Top progress bar */}
      <div className="h-1 bg-gray-200 shrink-0 dark:bg-gray-700">
        <div
          className="h-full bg-primary transition-all duration-500"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Header */}
      <header className="shrink-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-primary flex items-center justify-center">
            <Building2 className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="font-bold text-sm text-gray-900 dark:text-white">GlideGate</div>
            <div className="text-gray-500 dark:text-gray-400 text-xs">New Account Application</div>
          </div>
        </div>
        <button
          onClick={onCancel}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 px-3 py-1.5 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Cancel
        </button>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — stepper */}
        <aside className="w-60 shrink-0 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden hidden lg:flex">
          <nav className="flex-1 px-4 py-8 overflow-y-auto">
            <div className="space-y-1">
              {steps.map((s, idx) => {
                const isCompleted = idx < step
                const isActive = idx === step
                const isPending = idx > step
                const Icon = s.icon
                return (
                  <button
                    key={s.id}
                    onClick={() => isCompleted && setStep(idx)}
                    disabled={isPending}
                    className={[
                      'w-full flex items-center gap-3 px-3 py-3 text-left transition-all',
                      isActive && 'bg-gray-100 dark:bg-white/10',
                      isCompleted && 'hover:bg-gray-50 dark:hover:bg-white/5 cursor-pointer',
                      isPending && 'cursor-default opacity-40',
                    ].filter(Boolean).join(' ')}
                  >
                    <div
                      className={[
                        'w-8 h-8 flex items-center justify-center shrink-0 text-xs font-bold transition-all',
                        isCompleted ? 'bg-success text-white' :
                        isActive ? 'bg-primary text-white' :
                        'bg-gray-200 dark:bg-white/10 text-gray-500 dark:text-gray-400',
                      ].join(' ')}
                    >
                      {isCompleted ? <CheckCircle className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                    </div>
                    <div className="min-w-0">
                      <div
                        className={[
                          'text-xs font-medium leading-tight truncate',
                          isActive ? 'text-gray-900 dark:text-white' : isCompleted ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500',
                        ].join(' ')}
                      >
                        {s.title}
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </nav>

          {/* Progress footer */}
          <div className="px-5 py-5 border-t border-gray-200 dark:border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400">Overall progress</span>
              <span className="text-xs font-bold text-gray-900 dark:text-white">{progressPct}%</span>
            </div>
            <div className="h-1.5 bg-gray-200 dark:bg-white/10 overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-500">
              Step {step + 1} of {totalSteps}
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Step header */}
          <div className="shrink-0 bg-white border-b border-gray-100 px-8 py-5 dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-gray-100 flex items-center justify-center dark:bg-gray-700">
                {currentStep && <currentStep.icon className="w-5 h-5 text-gray-600 dark:text-gray-300" />}
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">{currentStep?.title}</h1>
              </div>
              <div className="ml-auto flex items-center gap-2 text-xs text-gray-400">
                <span className="w-6 h-6 bg-gray-100 flex items-center justify-center font-bold text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                  {step + 1}
                </span>
                <span>of {totalSteps}</span>
              </div>
            </div>
          </div>

          {/* Scrollable form */}
          <div className="flex-1 overflow-y-auto px-8 py-8">
            <div className="max-w-2xl">{renderContent()}</div>
          </div>

          {/* Footer navigation */}
          <div className="shrink-0 bg-white border-t border-gray-100 px-8 py-5 flex items-center justify-between dark:bg-gray-800 dark:border-gray-700">
            <button
              onClick={handleBack}
              className="flex items-center gap-2 border border-gray-200 bg-white px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
            >
              <ArrowLeft className="w-4 h-4" />
              {step === 0 ? 'Cancel' : 'Back'}
            </button>

            <div className="flex items-center gap-3">
              {step > 0 && step < totalSteps - 1 && (
                <span className="text-xs text-gray-400">Auto-saved</span>
              )}

              {currentStep?.id !== 'review' && (
                step === 0 ? (
                  <button
                    onClick={handleProductsContinue}
                    disabled={!ready || creatingCase}
                    className="flex items-center gap-2 bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    {creatingCase ? (
                      <><Loader className="w-4 h-4 animate-spin" />Creating…</>
                    ) : (
                      <>Continue <ArrowRight className="w-4 h-4" /></>
                    )}
                  </button>
                ) : (
                  <button
                    onClick={
                      currentStep?.id === 'documents'
                        ? handleDocumentsContinue
                        : handleSectionContinue
                    }
                    className={[
                      'flex items-center gap-2 px-5 py-2.5 text-sm font-semibold transition-colors',
                      ready
                        ? 'bg-primary text-white hover:bg-primary-hover'
                        : 'bg-primary text-white hover:bg-primary-hover opacity-60',
                    ].join(' ')}
                  >
                    Continue <ArrowRight className="w-4 h-4" />
                  </button>
                )
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
