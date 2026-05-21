import { CheckCircle, Clock, AlertTriangle } from 'lucide-react'
import ProgressBar from '@/components/ProgressBar'
import { useChatStore } from '@/store/chatStore'
import type { CaseSummary } from '@/lib/api'

const CLIENT_STAGE_LABELS: Record<string, string> = {
  INTAKE: 'Getting Started',
  KYC: 'Identity Verification',
  PARALLEL_PRODUCTS: 'Account Setup',
  REVIEW: 'Final Review',
  COMPLETE: 'All Done!',
  ESCALATED: 'Under Review',
}

const INTAKE_MAX = 60
const KYC_MAX = 70

interface ClientProgressBarProps {
  summary: CaseSummary | undefined
  isLoading?: boolean
}

export default function ClientProgressBar({ summary, isLoading }: ClientProgressBarProps) {
  const questionnairePct = useChatStore((s) => s.questionnairePct)

  if (isLoading) {
    return <div className="h-24 animate-pulse rounded-2xl bg-gray-100 dark:bg-gray-700" />
  }

  const stage = summary?.current_stage ?? 'INTAKE'

  let progress: number
  if (stage === 'INTAKE') {
    if (questionnairePct > 0) {
      progress = Math.round((questionnairePct / 100) * INTAKE_MAX)
    } else {
      progress = summary?.questionnaire_pct ?? 0
    }
  } else if (stage === 'KYC') {
    progress = KYC_MAX
  } else if (stage === 'PARALLEL_PRODUCTS') {
    const docRatio =
      summary && summary.documents_total > 0
        ? summary.documents_approved / summary.documents_total
        : 0
    progress = Math.round(KYC_MAX + docRatio * (100 - KYC_MAX))
  } else if (stage === 'REVIEW') {
    progress = 95
  } else if (stage === 'COMPLETE') {
    progress = 100
  } else if (stage === 'ESCALATED') {
    progress = 75
  } else {
    progress = summary?.overall_progress ?? 0
  }

  const stageLabel = CLIENT_STAGE_LABELS[stage] ?? stage
  const isComplete = stage === 'COMPLETE'
  const isEscalated = stage === 'ESCALATED' || summary?.escalated

  return (
    <div
      className={[
        'rounded-2xl border p-4',
        isComplete
          ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950'
          : isEscalated
          ? 'border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950'
          : 'border-blue-100 bg-white dark:border-gray-700 dark:bg-gray-800',
      ].join(' ')}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          {summary?.client_name && (
            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Welcome, {summary.client_name.split(' ')[0]}!
            </p>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 flex items-center gap-1.5">
            {isComplete ? (
              <CheckCircle className="h-3.5 w-3.5 text-green-500" />
            ) : isEscalated ? (
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
            ) : (
              <Clock className="h-3.5 w-3.5 text-blue-400" />
            )}
            {stageLabel}
          </p>
        </div>
        <div className="text-right">
          <p
            className={[
              'text-2xl font-bold tabular-nums',
              isComplete ? 'text-green-600 dark:text-green-400' : isEscalated ? 'text-amber-600 dark:text-amber-400' : 'text-blue-600 dark:text-blue-400',
            ].join(' ')}
          >
            {progress}%
          </p>
          <p className="text-[10px] text-gray-400">complete</p>
        </div>
      </div>

      <ProgressBar
        value={progress}
        size="sm"
        color={isComplete ? 'success' : isEscalated ? 'warning' : 'default'}
      />

      {summary && summary.documents_total > 0 && (
        <p className="mt-1.5 text-[10px] text-gray-400">
          {summary.documents_approved} of {summary.documents_total} document
          {summary.documents_total !== 1 ? 's' : ''} approved
        </p>
      )}
    </div>
  )
}
