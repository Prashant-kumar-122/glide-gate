import { format } from 'date-fns'
import { ChevronRight, Clock, CheckCircle } from 'lucide-react'
import type { CaseOut } from '@/lib/api'

function formatStageLabel(stage: string): string {
  const labels: Record<string, string> = {
    INTAKE: 'In Progress',
    KYC: 'KYC Review',
    PARALLEL_PRODUCTS: 'Documents Review',
    REVIEW: 'Under Review',
    COMPLETE: 'Completed',
    ESCALATED: 'Escalated',
  }
  return labels[stage] ?? stage.replace(/_/g, ' ')
}

function formatProductName(code: string): string {
  return code.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

function stageBadgeClass(stage: string): string {
  if (stage === 'COMPLETE') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'
  if (stage === 'ESCALATED') return 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
  if (stage === 'KYC' || stage === 'REVIEW') return 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300'
  return 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
}

interface Props {
  caseData: CaseOut
  onClick: () => void
}

export default function CaseCard({ caseData, onClick }: Props) {
  const isComplete = caseData.current_stage === 'COMPLETE'
  const pct = Math.min(100, Math.max(0, caseData.percentage ?? 0))

  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-2xl border border-gray-200 bg-white p-5 hover:shadow-md transition-all group dark:border-gray-700 dark:bg-gray-800"
    >
      {/* Top row: products + stage badge */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0">
          <div className="flex flex-wrap gap-1.5 mb-1">
            {caseData.selected_products.map((p) => (
              <span
                key={p}
                className="inline-flex items-center text-xs font-medium bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full dark:bg-gray-700 dark:text-gray-200"
              >
                {formatProductName(p)}
              </span>
            ))}
          </div>
          {caseData.case_name && (
            <p className="text-xs text-gray-400 truncate">{caseData.case_name}</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={['text-xs font-semibold px-2.5 py-1 rounded-full', stageBadgeClass(caseData.status)].join(' ')}>
            {formatStageLabel(caseData.status)}
          </span>
          <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition-colors dark:text-gray-600 dark:group-hover:text-gray-400" />
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-gray-400">Progress</span>
          <span className="text-xs font-semibold text-gray-600 dark:text-gray-300">{pct}%</span>
        </div>
        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden dark:bg-gray-700">
          <div
            className={['h-full rounded-full transition-all', isComplete ? 'bg-emerald-500' : 'bg-blue-600'].join(' ')}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Bottom: date + stage icon */}
      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>
          {isComplete ? (
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
              <CheckCircle className="w-3.5 h-3.5" />
              Completed
            </span>
          ) : (
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              Updated {format(new Date(caseData.updated_at), 'dd MMM yyyy')}
            </span>
          )}
        </span>
        <span className="text-gray-300 dark:text-gray-600">
          {format(new Date(caseData.created_at), 'dd MMM yyyy')}
        </span>
      </div>
    </button>
  )
}
