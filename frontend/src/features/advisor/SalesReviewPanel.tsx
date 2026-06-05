import { useState } from 'react'
import {
  ShieldCheck,
  ShieldX,
  Info,
  Bot,
  Check,
  X,
  AlertTriangle,
  RefreshCw,
  Clock,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { useSalesReviewsByCase, useDecideSalesReview } from '@/hooks/useSalesReview'

type Decision = 'APPROVED' | 'REJECTED' | 'MORE_INFO_REQUESTED'

// ── Decision confirmation modal ───────────────────────────────────────────────

function DecisionModal({
  type,
  onConfirm,
  onCancel,
  isLoading,
}: {
  type: Decision
  onConfirm: (notes: string) => void
  onCancel: () => void
  isLoading: boolean
}) {
  const [notes, setNotes] = useState('')

  const cfg = {
    APPROVED: {
      title: 'Approve — Initiate KYC',
      desc: 'Approving will trigger the KYC compliance check immediately.',
      icon: <ShieldCheck className="h-5 w-5 text-emerald-500" />,
      btn: 'bg-emerald-600 hover:bg-emerald-700 text-white',
      label: 'Confirm Approval',
      required: false,
      placeholder: 'Optional approval notes…',
    },
    REJECTED: {
      title: 'Reject Application',
      desc: 'The case will be moved back to review and the advisor notified.',
      icon: <ShieldX className="h-5 w-5 text-red-500" />,
      btn: 'bg-red-600 hover:bg-red-700 text-white',
      label: 'Confirm Rejection',
      required: true,
      placeholder: 'Reason for rejection (required)…',
    },
    MORE_INFO_REQUESTED: {
      title: 'Request More Information',
      desc: 'The case will be held pending additional information from the client or advisor.',
      icon: <Info className="h-5 w-5 text-sky-500" />,
      btn: 'bg-sky-600 hover:bg-sky-700 text-white',
      label: 'Send Request',
      required: true,
      placeholder: 'Describe what additional information is needed (required)…',
    },
  }[type]

  const canSubmit = !cfg.required || notes.trim().length > 3

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md mx-4 border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900 p-6 max-h-[90dvh] overflow-y-auto">
        <div className="flex items-start gap-3 mb-4">
          {cfg.icon}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{cfg.title}</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{cfg.desc}</p>
          </div>
        </div>
        <textarea
          className="w-full h-24 border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 resize-none focus:outline-none focus:ring-1 focus:ring-primary"
          placeholder={cfg.placeholder}
          value={notes}
          onChange={e => setNotes(e.target.value)}
        />
        <div className="flex gap-2 mt-4 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-xs font-medium border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            Cancel
          </button>
          <button
            disabled={!canSubmit || isLoading}
            onClick={() => onConfirm(notes.trim())}
            className={`px-4 py-2 text-xs font-semibold transition-colors disabled:opacity-40 ${cfg.btn}`}
          >
            {isLoading ? 'Processing…' : cfg.label}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────

interface SalesReviewPanelProps {
  caseId: string
  userRole?: string
}

export default function SalesReviewPanel({ caseId, userRole }: SalesReviewPanelProps) {
  const { data: reviews = [], isLoading, isError, refetch } = useSalesReviewsByCase(caseId)
  const decideMutation = useDecideSalesReview()
  const [pendingDecision, setPendingDecision] = useState<Decision | null>(null)
  const [summaryExpanded, setSummaryExpanded] = useState(false)

  const isSalesManager = userRole === 'sales_manager' || userRole === 'admin'
  const activeReview = reviews.find(r => r.status === 'PENDING') ?? reviews[0] ?? null
  const isPending = activeReview?.status === 'PENDING'
  const isDecided = activeReview && !isPending

  function handleDecision(notes: string) {
    if (!pendingDecision || !activeReview) return
    decideMutation.mutate(
      { reviewId: activeReview.id, decision: pendingDecision, decision_notes: notes || undefined },
      { onSuccess: () => setPendingDecision(null) },
    )
  }

  // ── Loading / error states ────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20 px-4 py-3">
        <div className="h-4 w-4 border-2 border-amber-500 border-t-transparent animate-spin flex-shrink-0" />
        <span className="text-sm text-amber-700 dark:text-amber-300">Loading sales review…</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex items-center justify-between border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20 px-4 py-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />
          <span className="text-sm text-red-700 dark:text-red-300">Could not load review data.</span>
        </div>
        <button onClick={() => refetch()} className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:underline">
          <RefreshCw className="h-3 w-3" /> Retry
        </button>
      </div>
    )
  }

  if (!activeReview) {
    return (
      <div className="flex items-center justify-between border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20 px-4 py-3">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
          <span className="text-sm text-amber-700 dark:text-amber-300">
            Sales Manager review is being prepared…
          </span>
        </div>
        <button onClick={() => refetch()} className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400 hover:underline">
          <RefreshCw className="h-3 w-3" /> Refresh
        </button>
      </div>
    )
  }

  // ── Decided state (read-only) ────────────────────────────────────────────

  if (isDecided) {
    const decidedStatus = activeReview.status as Decision
    const statusColors = {
      APPROVED: 'border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20',
      REJECTED: 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20',
      MORE_INFO_REQUESTED: 'border-sky-200 bg-sky-50 dark:border-sky-800 dark:bg-sky-900/20',
    }[decidedStatus] ?? 'border-gray-200 bg-gray-50'
    const statusLabel = {
      APPROVED: 'Approved — KYC initiated',
      REJECTED: 'Rejected by Sales Manager',
      MORE_INFO_REQUESTED: 'More information requested',
    }[decidedStatus] ?? activeReview.status

    return (
      <div className={`border px-4 py-3 ${statusColors}`}>
        <div className="flex items-start gap-2">
          <ShieldCheck className="h-4 w-4 mt-0.5 flex-shrink-0 text-gray-500 dark:text-gray-400" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">{statusLabel}</p>
            {activeReview.decision_notes && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{activeReview.decision_notes}</p>
            )}
          </div>
        </div>
      </div>
    )
  }

  // ── Pending state ────────────────────────────────────────────────────────

  const docPct = activeReview.case_snapshot.total_documents > 0
    ? Math.round((activeReview.case_snapshot.approved_documents / activeReview.case_snapshot.total_documents) * 100)
    : 0
  const riskScore = activeReview.risk_score

  return (
    <>
      {pendingDecision && (
        <DecisionModal
          type={pendingDecision}
          onConfirm={handleDecision}
          onCancel={() => setPendingDecision(null)}
          isLoading={decideMutation.isPending}
        />
      )}

      <div className="border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20">

        {/* Header row */}
        <div className="flex items-start justify-between gap-3 px-4 pt-4 pb-3">
          <div className="flex items-start gap-2 min-w-0">
            <Clock className="h-4 w-4 mt-0.5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-sm font-semibold text-amber-800 dark:text-amber-200">
                Awaiting Sales Manager Review
              </p>
              <p className="text-xs text-amber-600 dark:text-amber-400 mt-0.5">
                {activeReview.case_snapshot.selected_products.map(p => p.replace(/_/g, ' ')).join(', ')}
                {riskScore != null && (
                  <> · Risk score: <span className={`font-medium ${riskScore < 35 ? 'text-emerald-600' : riskScore < 60 ? 'text-amber-700 dark:text-amber-300' : 'text-red-600'}`}>{riskScore.toFixed(0)}</span></>
                )}
                {` · Docs: ${activeReview.case_snapshot.approved_documents}/${activeReview.case_snapshot.total_documents} (${docPct}%)`}
              </p>
            </div>
          </div>
          {/* Toggle AI summary */}
          <button
            onClick={() => setSummaryExpanded(v => !v)}
            className="flex items-center gap-1 text-xs text-amber-700 dark:text-amber-300 hover:underline flex-shrink-0"
          >
            <Bot className="h-3.5 w-3.5" />
            AI Summary
            {summaryExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        </div>

        {/* AI summary (collapsible) */}
        {summaryExpanded && activeReview.ai_risk_summary && (
          <div className="mx-4 mb-3 border border-amber-200 dark:border-amber-700 bg-white dark:bg-gray-800 px-3 py-2.5">
            <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
              {activeReview.ai_risk_summary}
            </p>
          </div>
        )}

        {/* Decision buttons — sales_manager only */}
        {isSalesManager ? (
          <div className="flex flex-wrap items-center gap-2 border-t border-amber-200 dark:border-amber-700 px-4 py-3">
            <span className="text-xs font-medium text-amber-700 dark:text-amber-300 mr-1">Your decision:</span>
            <button
              onClick={() => setPendingDecision('APPROVED')}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition-colors"
            >
              <Check className="h-3.5 w-3.5" /> Approve
            </button>
            <button
              onClick={() => setPendingDecision('MORE_INFO_REQUESTED')}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold transition-colors"
            >
              <Info className="h-3.5 w-3.5" /> Request Info
            </button>
            <button
              onClick={() => setPendingDecision('REJECTED')}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold transition-colors"
            >
              <X className="h-3.5 w-3.5" /> Reject
            </button>
            {decideMutation.isError && (
              <span className="text-xs text-red-600 dark:text-red-400">
                {(decideMutation.error as Error)?.message ?? 'Decision failed'}
              </span>
            )}
          </div>
        ) : (
          <div className="border-t border-amber-200 dark:border-amber-700 px-4 py-2.5">
            <p className="text-xs text-amber-600 dark:text-amber-400">
              Waiting for Sales Manager to approve, reject, or request more information.
            </p>
          </div>
        )}
      </div>
    </>
  )
}
