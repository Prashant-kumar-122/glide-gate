import { AlertTriangle, Clock, CheckCircle, XCircle, Info } from 'lucide-react'
import type { ReviewOut } from '@/lib/api'
import { usePendingReviews } from '@/hooks/usePendingReviews'

const STATUS_CONFIG = {
  PENDING: { icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50', label: 'Pending' },
  APPROVED: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50', label: 'Approved' },
  REJECTED: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50', label: 'Rejected' },
  MORE_INFO_REQUESTED: { icon: Info, color: 'text-blue-600', bg: 'bg-blue-50', label: 'More Info' },
} as const

const RISK_BAND_COLOR: Record<string, string> = {
  LOW: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  MEDIUM: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  HIGH: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  VERY_HIGH: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
}

interface Props {
  selectedReviewId: string | null
  onSelect: (review: ReviewOut) => void
}

export function EscalationQueue({ selectedReviewId, onSelect }: Props) {
  const { data: reviews, isLoading, isError } = usePendingReviews()

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-20 bg-gray-100 animate-pulse dark:bg-gray-700" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-4 text-sm text-red-600 flex items-center gap-2 dark:text-red-400">
        <AlertTriangle size={16} />
        Failed to load escalation queue.
      </div>
    )
  }

  if (!reviews || reviews.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500 dark:text-gray-400">
        <CheckCircle size={32} className="mx-auto mb-2 text-green-400" />
        <p className="text-sm font-medium">No pending escalations</p>
        <p className="text-xs mt-1">All cases are proceeding normally.</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-gray-100 dark:divide-gray-700">
      {reviews.map((review) => {
        const cfg = STATUS_CONFIG[review.status] ?? STATUS_CONFIG.PENDING
        const Icon = cfg.icon
        const riskBand = review.evidence_packet?.kyc_result?.risk_band ?? 'UNKNOWN'
        const isSelected = selectedReviewId === review.id

        return (
          <button
            key={review.id}
            onClick={() => onSelect(review)}
            className={`w-full text-left px-4 py-3 transition-colors hover:bg-gray-50 focus:outline-none dark:hover:bg-gray-800 ${
              isSelected ? 'bg-amber-50 border-l-4 border-amber-500 dark:bg-amber-950' : ''
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <Icon size={16} className={cfg.color + ' shrink-0'} />
                <span className="text-sm font-medium text-gray-900 truncate dark:text-gray-100">
                  Case {review.case_id.slice(0, 8)}…
                </span>
              </div>
              <span
                className={`text-xs font-semibold px-2 py-0.5 shrink-0 ${
                  RISK_BAND_COLOR[riskBand] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                }`}
              >
                {riskBand}
              </span>
            </div>
            {review.escalation_reason && (
              <p className="mt-1 text-xs text-gray-600 line-clamp-2 pl-6 dark:text-gray-300">
                {review.escalation_reason}
              </p>
            )}
            <p className="mt-1 text-xs text-gray-400 pl-6">
              {new Date(review.assigned_at).toLocaleString()}
            </p>
          </button>
        )
      })}
    </div>
  )
}
