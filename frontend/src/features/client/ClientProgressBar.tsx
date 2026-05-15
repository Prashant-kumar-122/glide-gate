import { CheckCircle, Clock, AlertTriangle } from 'lucide-react'
import ProgressBar from '@/components/ProgressBar'
import type { CaseSummary } from '@/lib/api'

const CLIENT_STAGE_LABELS: Record<string, string> = {
  INTAKE: 'Getting Started',
  KYC: 'Identity Verification',
  PARALLEL_PRODUCTS: 'Account Setup',
  REVIEW: 'Final Review',
  COMPLETE: 'All Done!',
  ESCALATED: 'Under Review',
}

const STAGE_PROGRESS: Record<string, number> = {
  INTAKE: 15,
  KYC: 35,
  PARALLEL_PRODUCTS: 60,
  REVIEW: 80,
  COMPLETE: 100,
  ESCALATED: 75,
}

interface ClientProgressBarProps {
  summary: CaseSummary | undefined
  isLoading?: boolean
}

export default function ClientProgressBar({ summary, isLoading }: ClientProgressBarProps) {
  if (isLoading) {
    return <div className="h-24 animate-pulse rounded-2xl bg-gray-100" />
  }

  const stage = summary?.current_stage ?? 'INTAKE'
  const progress = summary?.overall_progress ?? STAGE_PROGRESS[stage] ?? 0
  const stageLabel = CLIENT_STAGE_LABELS[stage] ?? stage
  const isComplete = stage === 'COMPLETE'
  const isEscalated = stage === 'ESCALATED' || summary?.escalated

  return (
    <div
      className={[
        'rounded-2xl border p-4',
        isComplete
          ? 'border-green-200 bg-green-50'
          : isEscalated
          ? 'border-amber-200 bg-amber-50'
          : 'border-blue-100 bg-white',
      ].join(' ')}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          {summary?.client_name && (
            <p className="text-sm font-semibold text-gray-900">
              Welcome, {summary.client_name.split(' ')[0]}!
            </p>
          )}
          <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1.5">
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
              isComplete ? 'text-green-600' : isEscalated ? 'text-amber-600' : 'text-blue-600',
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
