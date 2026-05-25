import { User, Package, BadgeCheck } from 'lucide-react'
import ProductTrackSummary from './ProductTrackSummary'
import CallSummaryCard from './CallSummaryCard'
import CCActionBar from './CCActionBar'
import { useAccount } from '@/hooks/useDocuments'
import type { CaseSummary, CallSummary } from '@/lib/api'

const STAGE_LABELS: Record<string, string> = {
  INTAKE: 'Intake',
  KYC: 'Identity Check',
  PARALLEL_PRODUCTS: 'Account Setup',
  REVIEW: 'Final Review',
  COMPLETE: 'Complete',
  ESCALATED: 'Escalated',
}

const STAGE_COLORS: Record<string, string> = {
  INTAKE: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
  KYC: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  PARALLEL_PRODUCTS: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300',
  REVIEW: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  COMPLETE: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  ESCALATED: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
}

interface Props {
  summary?: CaseSummary
  summaryLoading?: boolean
  caseName?: string | null
  callSummary?: CallSummary
  callSummaryLoading?: boolean
  callSummaryError?: boolean
  onRefreshCallSummary?: () => void
}

export default function ClientDetailPanel({
  summary,
  summaryLoading,
  caseName,
  callSummary,
  callSummaryLoading,
  callSummaryError,
  onRefreshCallSummary,
}: Props) {
  if (summaryLoading) {
    return (
      <div className="flex h-full flex-col gap-4 p-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-28 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-700" />
        ))}
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <User className="mx-auto h-10 w-10 text-gray-200 dark:text-gray-700" />
          <p className="mt-3 text-sm font-medium text-gray-400">Select a client to view details</p>
          <p className="mt-1 text-xs text-gray-300 dark:text-gray-600">Stage, product tracks, and AI summary will appear here</p>
        </div>
      </div>
    )
  }

  const badgeClass = STAGE_COLORS[summary.current_stage] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
  const stageLabel = STAGE_LABELS[summary.current_stage] ?? summary.current_stage
  const { data: account } = useAccount(summary.case_id, summary.current_stage === 'COMPLETE')

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      {/* Client header */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-700 dark:bg-blue-900 dark:text-blue-300">
              {(summary.client_name ?? 'C').charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-base font-semibold text-gray-900 dark:text-gray-100">
                {summary.client_name ?? 'Client'}
              </p>
              <p className="text-xs text-gray-400">
                <span className="font-medium text-gray-500 dark:text-gray-400">Case name: </span>
                {caseName ?? `#${summary.case_id.slice(0, 8)}`}
              </p>
              {account && account.map((acc) => (
                <p key={acc.account_number} className="mt-0.5 flex items-center gap-1 text-xs font-mono font-medium text-emerald-600 dark:text-emerald-400">
                  <BadgeCheck className="w-3 h-3 shrink-0" />
                  {acc.product.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}: {acc.account_number}
                </p>
              ))}
            </div>
          </div>
          <span className={['rounded-full px-2.5 py-1 text-xs font-medium', badgeClass].join(' ')}>
            {stageLabel}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-3 border-t border-gray-100 pt-4 dark:border-gray-700">
          <div className="text-center">
            <p className="text-xl font-bold tabular-nums text-gray-900 dark:text-gray-100">{summary.overall_progress}%</p>
            <p className="mt-0.5 text-[10px] text-gray-400">Overall Progress</p>
          </div>
          <div className="text-center">
            <p className="text-xl font-bold tabular-nums text-gray-900 dark:text-gray-100">
              {summary.documents_approved}/{summary.documents_total}
            </p>
            <p className="mt-0.5 text-[10px] text-gray-400">Docs Approved</p>
          </div>
          <div className="text-center">
            {summary.escalated ? (
              <p className="text-xl font-bold text-amber-500">!</p>
            ) : (
              <p className="text-xl font-bold text-green-500">✓</p>
            )}
            <p className="mt-0.5 text-[10px] text-gray-400">
              {summary.escalated ? 'Escalated' : 'On Track'}
            </p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
          Actions
        </p>
        <CCActionBar summary={summary} />
      </div>

      {/* Product tracks */}
      {summary.products && summary.products.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-3 flex items-center gap-2">
            <Package className="h-4 w-4 text-gray-400" />
            <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
              Product Tracks
            </p>
          </div>
          <ProductTrackSummary tracks={summary.products} />
        </div>
      )}

      {/* AI call summary */}
      <CallSummaryCard
        summary={callSummary}
        isLoading={callSummaryLoading}
        isError={callSummaryError}
        onRefresh={onRefreshCallSummary}
      />
    </div>
  )
}
