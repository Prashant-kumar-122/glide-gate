import { useState } from 'react'
import { CheckCircle, XCircle, Info, Loader2 } from 'lucide-react'
import ConfirmationModal from '@/components/ConfirmationModal'
import { useDecideReview } from '@/hooks/usePendingReviews'
import type { ReviewOut } from '@/lib/api'

type Decision = 'APPROVED' | 'REJECTED' | 'MORE_INFO_REQUESTED'

interface Props {
  review: ReviewOut
  onDecided?: () => void
}

const DECISION_CONFIG: Record<
  Decision,
  { label: string; icon: typeof CheckCircle; variant: 'default' | 'warning' | 'danger'; message: string }
> = {
  APPROVED: {
    label: 'Approve',
    icon: CheckCircle,
    variant: 'default',
    message: 'Approve this case — product onboarding will resume automatically.',
  },
  REJECTED: {
    label: 'Reject',
    icon: XCircle,
    variant: 'danger',
    message: 'Reject this case — the client will be notified and the case closed.',
  },
  MORE_INFO_REQUESTED: {
    label: 'Request Info',
    icon: Info,
    variant: 'warning',
    message: 'Request additional information — the case stays on hold pending client response.',
  },
}

export function ReviewActionBar({ review, onDecided }: Props) {
  const [pendingDecision, setPendingDecision] = useState<Decision | null>(null)
  const [notes, setNotes] = useState('')
  const decide = useDecideReview()

  const isDecided = review.status !== 'PENDING'

  if (isDecided) {
    const statusLabel: Record<string, string> = {
      APPROVED: 'Approved',
      REJECTED: 'Rejected',
      MORE_INFO_REQUESTED: 'More Information Requested',
    }

    return (
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Decision recorded:{' '}
          <span className="font-semibold text-gray-900 dark:text-gray-100">
            {statusLabel[review.status] ?? review.status}
          </span>
        </p>
        {review.decision_notes && (
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{review.decision_notes}</p>
        )}
        {review.decided_at && (
          <p className="mt-1 text-xs text-gray-400">
            {new Date(review.decided_at).toLocaleString()}
          </p>
        )}
      </div>
    )
  }

  const handleConfirm = async () => {
    if (!pendingDecision) return
    await decide.mutateAsync({
      reviewId: review.id,
      decision: pendingDecision,
      decision_notes: notes.trim() || undefined,
    })
    setPendingDecision(null)
    setNotes('')
    onDecided?.()
  }

  const cfg = pendingDecision ? DECISION_CONFIG[pendingDecision] : null

  return (
    <>
      <div className="p-4 border-t border-gray-200 space-y-3 dark:border-gray-700">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Reviewer Decision
        </p>
        <div className="flex gap-2">
          {(Object.keys(DECISION_CONFIG) as Decision[]).map((decision) => {
            const c = DECISION_CONFIG[decision]
            const Icon = c.icon
            const colorClass =
              decision === 'APPROVED'
                ? 'border-green-300 text-green-700 hover:bg-green-50 dark:border-green-700 dark:text-green-300 dark:hover:bg-green-950'
                : decision === 'REJECTED'
                ? 'border-red-300 text-red-700 hover:bg-red-50 dark:border-red-700 dark:text-red-300 dark:hover:bg-red-950'
                : 'border-blue-300 text-blue-700 hover:bg-blue-50 dark:border-blue-700 dark:text-blue-300 dark:hover:bg-blue-950'

            return (
              <button
                key={decision}
                onClick={() => setPendingDecision(decision)}
                disabled={decide.isPending}
                className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border text-sm font-medium transition-colors disabled:opacity-50 ${colorClass}`}
              >
                {decide.isPending && pendingDecision === decision ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Icon size={14} />
                )}
                {c.label}
              </button>
            )
          })}
        </div>
        {decide.isError && (
          <p className="text-xs text-red-600 dark:text-red-400">Failed to record decision. Please try again.</p>
        )}
      </div>

      <ConfirmationModal
        isOpen={pendingDecision !== null}
        title={cfg ? `Confirm: ${cfg.label}` : ''}
        message={
          <div>
            <p>{cfg?.message}</p>
            <div className="mt-3">
              <label className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300">
                Notes <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
                placeholder="Add decision notes for the audit trail…"
              />
            </div>
          </div>
        }
        variant={cfg?.variant ?? 'default'}
        confirmLabel={cfg?.label ?? 'Confirm'}
        loading={decide.isPending}
        onConfirm={handleConfirm}
        onCancel={() => { setPendingDecision(null); setNotes('') }}
      />
    </>
  )
}
