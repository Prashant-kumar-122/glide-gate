import { format } from 'date-fns'
import { ChevronRight, Clock, CheckCircle, BadgeCheck } from 'lucide-react'
import type { CaseOut } from '@/lib/api'
import { useAccount } from '@/hooks/useDocuments'

function formatStageLabel(stage: string): string {
  const labels: Record<string, string> = {
    INTAKE:            'In Progress',
    KYC:               'KYC Review',
    PARALLEL_PRODUCTS: 'Doc Review',
    REVIEW:            'Under Review',
    COMPLETE:          'Live',
    ESCALATED:         'Escalated',
  }
  return labels[stage] ?? stage.replace(/_/g, ' ')
}

function formatProductName(code: string): string {
  return code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

function stageBadgeClass(stage: string): string {
  if (stage === 'COMPLETE')
    return 'border border-green-300 bg-green-50 text-green-700 dark:border-green-600/40 dark:bg-green-950/40 dark:text-green-400'
  if (stage === 'ESCALATED')
    return 'border border-red-300 bg-red-50 text-red-700 dark:border-red-600/40 dark:bg-red-950/40 dark:text-red-400'
  if (stage === 'KYC' || stage === 'REVIEW')
    return 'border border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-600/40 dark:bg-amber-950/40 dark:text-amber-400'
  return 'border border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-600/40 dark:bg-blue-950/40 dark:text-blue-400'
}

interface Props {
  caseData: CaseOut
  onClick: () => void
}

export default function CaseCard({ caseData, onClick }: Props) {
  const isComplete = caseData.current_stage === 'COMPLETE'
  const pct = Math.min(100, Math.max(0, caseData.percentage ?? 0))
  const { data: account } = useAccount(caseData.id, isComplete)

  return (
    <button
      onClick={onClick}
      className="w-full text-left border border-gray-200 bg-white p-4 transition-colors hover:border-gray-300 hover:bg-gray-50 group dark:border-gray-800 dark:bg-gray-900 dark:hover:border-gray-700 dark:hover:bg-gray-800/50"
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0">
          <div className="flex flex-wrap gap-1 mb-1">
            {caseData.selected_products.map((p) => (
              <span
                key={p}
                className="inline-flex items-center text-[10px] font-medium border border-gray-200 bg-gray-50 px-1.5 py-0.5 text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
              >
                {formatProductName(p)}
              </span>
            ))}
          </div>
          {caseData.case_name && (
            <p className="text-[10px] text-gray-500 dark:text-gray-400 truncate">{caseData.case_name}</p>
          )}
          {account && account.map((acc) => (
            <p key={acc.account_number} className="flex items-center gap-1 font-mono text-[10px] font-medium text-emerald-600 dark:text-emerald-400 truncate mt-0.5">
              <BadgeCheck className="w-3 h-3 shrink-0" />
              {formatProductName(acc.product)}: {acc.account_number}
            </p>
          ))}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={[
            'px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide',
            stageBadgeClass(caseData.status),
          ].join(' ')}>
            {formatStageLabel(caseData.status)}
          </span>
          <ChevronRight className="w-3.5 h-3.5 text-gray-400 group-hover:text-gray-600 transition-colors dark:text-gray-600 dark:group-hover:text-gray-400" />
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase tracking-wide">Progress</span>
          <span className="font-mono text-[10px] font-semibold tabular-nums text-gray-600 dark:text-gray-400">{pct}%</span>
        </div>
        <div className="h-1 bg-gray-100 dark:bg-gray-800">
          <div
            className={['h-full transition-all', isComplete ? 'bg-green-500' : 'bg-primary'].join(' ')}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Bottom row */}
      <div className="flex items-center justify-between text-[10px] text-gray-500 dark:text-gray-400">
        <span>
          {isComplete ? (
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
              <CheckCircle className="w-3 h-3" />
              Live Account
            </span>
          ) : (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Updated {format(new Date(caseData.updated_at), 'dd MMM yyyy')}
            </span>
          )}
        </span>
        <span className="font-mono text-gray-400 dark:text-gray-600">
          {format(new Date(caseData.created_at), 'dd MMM yyyy')}
        </span>
      </div>
    </button>
  )
}
