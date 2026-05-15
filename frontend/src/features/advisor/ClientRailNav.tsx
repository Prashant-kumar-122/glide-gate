import { Briefcase, Wifi, WifiOff } from 'lucide-react'
import { useWorkspaceStore } from '@/store/workspaceStore'
import ProgressBar from '@/components/ProgressBar'
import { useCases } from '@/hooks/useDocuments'
import type { CaseOut } from '@/lib/api'

const STAGE_LABELS: Record<string, string> = {
  INTAKE: 'Intake',
  KYC: 'KYC',
  PARALLEL_PRODUCTS: 'Products',
  REVIEW: 'Review',
  COMPLETE: 'Complete',
  ESCALATED: 'Escalated',
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

interface CaseItemProps {
  c: CaseOut
  isSelected: boolean
  badgeCount: number
  onSelect: () => void
}

function caseDisplayName(c: CaseOut): string {
  if (c.case_name) return c.case_name
  if (c.selected_products.length > 0)
    return c.selected_products
      .map((p) => p.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()))
      .join(' & ')
  return c.client_name ?? 'Case'
}

function CaseItem({ c, isSelected, badgeCount, onSelect }: CaseItemProps) {
  const progress = stageToProgress(c.current_stage)
  const stageLabel = STAGE_LABELS[c.current_stage] ?? c.current_stage

  return (
    <button
      onClick={onSelect}
      className={[
        'w-full rounded-xl px-3 py-3 text-left transition-all',
        isSelected
          ? 'bg-blue-600 text-white shadow-md'
          : 'bg-white text-gray-800 hover:bg-gray-50 border border-gray-200',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className={['truncate text-sm font-semibold', isSelected ? 'text-white' : 'text-gray-900'].join(' ')}>
            {caseDisplayName(c)}
          </p>
          <p className={['mt-0.5 text-xs', isSelected ? 'text-blue-200' : 'text-gray-400'].join(' ')}>
            {stageLabel}
          </p>
        </div>

        {badgeCount > 0 && (
          <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {badgeCount}
          </span>
        )}
      </div>

      <div className="mt-2">
        <ProgressBar
          value={progress}
          size="sm"
          color={
            c.current_stage === 'COMPLETE'
              ? 'success'
              : c.current_stage === 'ESCALATED'
              ? 'warning'
              : isSelected
              ? 'default'
              : 'default'
          }
        />
      </div>

      <p className={['mt-1 text-right text-[10px] tabular-nums', isSelected ? 'text-blue-200' : 'text-gray-400'].join(' ')}>
        {progress}%
      </p>
    </button>
  )
}

export default function ClientRailNav() {
  const { selectedCaseId, socketConnected, setSelectedClient, uploadBadgeCounts } =
    useWorkspaceStore()
  const { data: cases, isLoading, isError } = useCases()

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-gray-200 bg-gray-50">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <div className="flex items-center gap-2">
          <Briefcase className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-semibold text-gray-700">Cases</span>
        </div>
        <span title={socketConnected ? 'Live' : 'Disconnected'}>
          {socketConnected ? (
            <Wifi className="h-4 w-4 text-green-500" />
          ) : (
            <WifiOff className="h-4 w-4 text-gray-400" />
          )}
        </span>
      </div>

      {/* Client list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded-xl bg-gray-200" />
            ))}
          </div>
        )}

        {isError && (
          <p className="rounded-lg bg-red-50 p-3 text-xs text-red-600">
            Failed to load cases. Is the backend running?
          </p>
        )}

        {!isLoading && !isError && cases?.length === 0 && (
          <p className="pt-8 text-center text-xs text-gray-400">No active cases</p>
        )}

        {cases?.map((c) => (
          <CaseItem
            key={c.id}
            c={c}
            isSelected={selectedCaseId === c.id}
            badgeCount={uploadBadgeCounts[c.id] ?? 0}
            onSelect={() => setSelectedClient(c.client_id, c.id)}
          />
        ))}
      </div>

      {/* Footer stats */}
      {cases && cases.length > 0 && (
        <div className="border-t border-gray-200 px-4 py-2">
          <p className="text-xs text-gray-400">
            {cases.length} active case{cases.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}
    </aside>
  )
}
