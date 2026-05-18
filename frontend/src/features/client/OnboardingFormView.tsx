import { ClipboardList } from 'lucide-react'
import type { QuestionSchemaItem } from '@/hooks/useDocuments'

// Keys injected by the system — never shown to the client
const SYSTEM_KEYS = new Set(['selected_products', 'version', 'created_at', 'updated_at'])

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

// snake_case → Title Case (fallback when key isn't in the schema)
function formatKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

// snake_case section key → display title
function sectionTitle(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

interface RenderedField {
  question_key: string
  label: string
}

interface RenderedSection {
  key: string
  title: string
  fields: RenderedField[]
}

interface OnboardingFormViewProps {
  clientData: Record<string, unknown>
  schema: QuestionSchemaItem[]
  isLoading?: boolean
}

export default function OnboardingFormView({
  clientData,
  schema,
  isLoading,
}: OnboardingFormViewProps) {
  // Build lookup: question_key → { section, label } from DB schema
  const schemaMap = new Map<string, { section: string; label: string }>()
  for (const item of schema) {
    schemaMap.set(item.question_key, { section: item.section, label: item.label })
  }

  // Derive section insertion order from schema (preserves DB order_index order)
  const sectionOrder: string[] = []
  for (const item of schema) {
    if (!sectionOrder.includes(item.section)) sectionOrder.push(item.section)
  }

  // Group answered fields into sections — walk schema in order_index order
  // so fields always render in the same sequence as the questionnaire.
  const sectionMap = new Map<string, RenderedField[]>()

  for (const item of schema) {
    const value = clientData[item.question_key]
    if (!hasValue(value)) continue

    if (!sectionMap.has(item.section)) sectionMap.set(item.section, [])
    sectionMap.get(item.section)!.push({ question_key: item.question_key, label: item.label })
  }

  // Append any client_data keys that have no matching schema entry into 'other'
  for (const [key, value] of Object.entries(clientData)) {
    if (SYSTEM_KEYS.has(key) || !hasValue(value) || schemaMap.has(key)) continue

    if (!sectionMap.has('other')) sectionMap.set('other', [])
    sectionMap.get('other')!.push({ question_key: key, label: formatKey(key) })
  }

  // Ensure 'other' always appears last
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
          <div key={i} className="animate-pulse rounded-xl border border-gray-200 bg-white p-4">
            <div className="mb-3 h-4 w-32 rounded bg-gray-200" />
            <div className="space-y-2">
              <div className="h-8 rounded-lg bg-gray-100" />
              <div className="h-8 rounded-lg bg-gray-100" />
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
        <div className="rounded-full bg-blue-50 p-4">
          <ClipboardList className="h-7 w-7 text-blue-400" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-700">Your answers will appear here</p>
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
      <div className="shrink-0 border-b border-gray-100 px-4 py-2.5">
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
              className="overflow-hidden rounded-xl border border-gray-200 bg-white"
            >
              {/* Section header */}
              <div className="border-b border-gray-100 bg-gray-50 px-4 py-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {sectionTitle(sectionKey)}
                </h3>
              </div>

              {/* Field rows */}
              <div className="divide-y divide-gray-50">
                {fields.map(({ question_key, label }) => (
                  <div key={question_key} className="px-4 py-3">
                    <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-gray-400">
                      {label}
                    </p>
                    <div className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-1.5">
                      <p className="break-words text-sm text-gray-800">
                        {formatValue(clientData[question_key])}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
