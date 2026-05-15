import { Search, AlertTriangle, CheckCircle } from 'lucide-react'
import { useCCStore } from '@/store/ccStore'
import ProgressBar from '@/components/ProgressBar'
import type { CaseOut } from '@/lib/api'

const STAGE_LABELS: Record<string, string> = {
  INTAKE: 'Intake',
  KYC: 'Identity Check',
  PARALLEL_PRODUCTS: 'Account Setup',
  REVIEW: 'Final Review',
  COMPLETE: 'Complete',
  ESCALATED: 'Escalated',
}

function caseDisplayName(c: CaseOut): string {
  if (c.case_name) return c.case_name
  if (c.selected_products.length > 0)
    return c.selected_products
      .map((p) => p.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()))
      .join(' & ')
  return c.client_name ?? 'Case'
}

const STAGE_BADGE: Record<string, string> = {
  INTAKE: 'bg-gray-100 text-gray-600',
  KYC: 'bg-blue-100 text-blue-700',
  PARALLEL_PRODUCTS: 'bg-indigo-100 text-indigo-700',
  REVIEW: 'bg-amber-100 text-amber-700',
  COMPLETE: 'bg-green-100 text-green-700',
  ESCALATED: 'bg-red-100 text-red-700',
}

function stageToProgress(stage: string): number {
  const map: Record<string, number> = {
    INTAKE: 15,
    KYC: 35,
    PARALLEL_PRODUCTS: 60,
    REVIEW: 80,
    COMPLETE: 100,
    ESCALATED: 75,
  }
  return map[stage] ?? 0
}

interface Props {
  cases: CaseOut[]
  isLoading: boolean
  isError: boolean
}

export default function ClientStatusTable({ cases, isLoading, isError }: Props) {
  const { selectedClientId, filterText, setSelectedClient, setFilterText } = useCCStore()

  const filtered = cases.filter((c) => {
    if (!filterText) return true
    const q = filterText.toLowerCase()
    return (
      caseDisplayName(c).toLowerCase().includes(q) ||
      (c.client_name ?? '').toLowerCase().includes(q) ||
      c.current_stage.toLowerCase().includes(q) ||
      c.selected_products.some((p) => p.toLowerCase().includes(q))
    )
  })

  return (
    <div className="flex h-full flex-col">
      {/* Search */}
      <div className="border-b border-gray-200 bg-white px-4 py-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search clients, stage, products…"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-gray-50 py-2 pl-9 pr-4 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
        </div>
        {filterText && (
          <p className="mt-1.5 text-[11px] text-gray-400">
            {filtered.length} of {cases.length} cases
          </p>
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="space-y-1 p-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded-lg bg-gray-100" />
            ))}
          </div>
        )}

        {isError && (
          <div className="p-4">
            <p className="rounded-lg bg-red-50 p-3 text-xs text-red-600">
              Failed to load clients. Is the backend running?
            </p>
          </div>
        )}

        {!isLoading && !isError && filtered.length === 0 && (
          <div className="flex flex-col items-center py-16 text-center">
            <Search className="h-8 w-8 text-gray-200" />
            <p className="mt-2 text-sm text-gray-400">No cases match your search</p>
          </div>
        )}

        {filtered.map((c) => {
          const isSelected = selectedClientId === c.id
          const progress = stageToProgress(c.current_stage)
          const badgeClass = STAGE_BADGE[c.current_stage] ?? 'bg-gray-100 text-gray-600'
          const stageLabel = STAGE_LABELS[c.current_stage] ?? c.current_stage
          const isEscalated = c.current_stage === 'ESCALATED' || c.status === 'ESCALATED'

          return (
            <button
              key={c.id}
              onClick={() => setSelectedClient(c.id)}
              className={[
                'w-full border-b border-gray-100 px-4 py-3 text-left transition-colors',
                isSelected ? 'bg-blue-50' : 'bg-white hover:bg-gray-50',
              ].join(' ')}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <p className="truncate text-sm font-semibold text-gray-900">
                      {caseDisplayName(c)}
                    </p>
                    {isEscalated && <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-500" />}
                    {c.current_stage === 'COMPLETE' && (
                      <CheckCircle className="h-3.5 w-3.5 shrink-0 text-green-500" />
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <span className={['rounded-full px-2 py-0.5 text-[10px] font-medium', badgeClass].join(' ')}>
                      {stageLabel}
                    </span>
                    <span className="text-[10px] text-gray-400">
                      {c.selected_products.length} product{c.selected_products.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                </div>
                <span className="text-xs font-semibold tabular-nums text-gray-500">{progress}%</span>
              </div>

              <div className="mt-2">
                <ProgressBar
                  value={progress}
                  size="sm"
                  color={
                    c.current_stage === 'COMPLETE'
                      ? 'success'
                      : isEscalated
                      ? 'warning'
                      : 'default'
                  }
                />
              </div>
            </button>
          )
        })}
      </div>

      {/* Footer */}
      {!isLoading && !isError && (
        <div className="border-t border-gray-100 bg-gray-50 px-4 py-2">
          <p className="text-[11px] text-gray-400">
            {cases.length} active case{cases.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}
    </div>
  )
}
