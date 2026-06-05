import { useState } from 'react'
import { Check, X, Info, FileText, ExternalLink, Loader2 } from 'lucide-react'
import { useDecideTask } from '@/hooks/useTasks'
import { useDecideSalesReview } from '@/hooks/useSalesReview'
import { useUpdateDocumentStatus, useDocument, useValidateDocument } from '@/hooks/useDocuments'
import { api } from '@/lib/api'
import DecisionModal from './DecisionModal'
import AIValidationPanel from './AIValidationPanel'
import type { Decision } from './DecisionModal'
import type { TaskOut } from '@/lib/api'

interface TaskDetailViewProps {
  task: TaskOut
  caseId: string
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

const STATUS_BADGE: Record<string, string> = {
  PENDING: 'border-amber-600/50 bg-amber-950/20 text-amber-400',
  APPROVED: 'border-green-600/50 bg-green-950/20 text-green-400',
  REJECTED: 'border-red-600/50 bg-red-950/20 text-red-400',
  MORE_INFO_REQUESTED: 'border-sky-600/50 bg-sky-950/20 text-sky-400',
}

const TYPE_LABEL: Record<string, string> = {
  DOCUMENT_REVIEW: 'Document Review',
  SALES_REVIEW:    'Sales Review',
}

const TYPE_BADGE: Record<string, string> = {
  DOCUMENT_REVIEW: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
  SALES_REVIEW:    'bg-violet-500/10 border-violet-500/30 text-violet-400',
}

export default function TaskDetailView({ task, caseId }: TaskDetailViewProps) {
  const [pendingDecision, setPendingDecision] = useState<Decision | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const decideMutation = useDecideTask()
  const salesDecideMutation = useDecideSalesReview()
  const statusMutation = useUpdateDocumentStatus(caseId)

  const isDocTask = task.task_type === 'DOCUMENT_REVIEW'

  async function openPreview() {
    if (!task.document_id) return
    setPreviewing(true)
    try {
      const res = await api.get(`/documents/${task.document_id}/download`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data as Blob)
      const win = window.open(url, '_blank')
      // revoke after the new tab has had time to load
      setTimeout(() => URL.revokeObjectURL(url), 10_000)
      if (!win) alert('Pop-up blocked — please allow pop-ups for this site.')
    } finally {
      setPreviewing(false)
    }
  }
  const { data: fullDoc, isLoading: docLoading } = useDocument(isDocTask ? task.document_id : null)
  const validateMutation = useValidateDocument(caseId)

  const isPending = task.status === 'PENDING'
  const statusLabel = task.status === 'MORE_INFO_REQUESTED'
    ? 'More Info Req.'
    : task.status.charAt(0) + task.status.slice(1).toLowerCase()

  function handleConfirm(notes: string) {
    if (!pendingDecision) return

    if (task.task_type === 'DOCUMENT_REVIEW' && task.document_id) {
      const docStatus = pendingDecision === 'APPROVED' ? 'APPROVED' : 'NEEDS_REVISION'
      statusMutation.mutate({ docId: task.document_id, status: docStatus })
      decideMutation.mutate(
        { taskId: task.id, decision: pendingDecision, decision_notes: notes || undefined },
        { onSuccess: () => setPendingDecision(null) },
      )
    } else if (task.task_type === 'SALES_REVIEW' && task.review_id) {
      salesDecideMutation.mutate(
        { reviewId: task.review_id, decision: pendingDecision, decision_notes: notes || undefined },
        {
          onSuccess: () => {
            decideMutation.mutate(
              { taskId: task.id, decision: pendingDecision, decision_notes: notes || undefined },
              { onSuccess: () => setPendingDecision(null) },
            )
          },
        },
      )
    } else {
      decideMutation.mutate(
        { taskId: task.id, decision: pendingDecision, decision_notes: notes || undefined },
        { onSuccess: () => setPendingDecision(null) },
      )
    }
  }

  const isSubmitting =
    decideMutation.isPending || salesDecideMutation.isPending || statusMutation.isPending

  return (
    <>
      {pendingDecision && (
        <DecisionModal
          type={pendingDecision}
          onConfirm={handleConfirm}
          onCancel={() => setPendingDecision(null)}
          isLoading={isSubmitting}
        />
      )}

      {/* ── Task header strip ── */}
      <div className="shrink-0 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-5 py-3.5">
        <h2 className="text-base font-bold text-gray-900 dark:text-gray-100 truncate leading-tight">
          {task.title}
        </h2>
        <div className="flex flex-wrap items-center gap-1.5 mt-2">
          <span className={`inline-flex items-center px-2 py-0.5 text-[11px] font-medium border ${TYPE_BADGE[task.task_type] ?? 'bg-gray-500/10 border-gray-500/30 text-gray-400'}`}>
            {TYPE_LABEL[task.task_type] ?? task.task_type}
          </span>
          <span className={`inline-flex items-center px-2 py-0.5 text-[11px] font-medium border ${STATUS_BADGE[task.status] ?? 'border-gray-600/50 text-gray-400'}`}>
            {statusLabel}
          </span>
        </div>
        <p className="mt-2 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[11px]">
          <span className="text-gray-500 dark:text-gray-500">Task ID:</span>
          <span className="font-mono font-medium text-gray-700 dark:text-gray-400">{task.id.slice(0, 12)}</span>
          <span className="text-gray-400 dark:text-gray-600">·</span>
          <span className="text-gray-500 dark:text-gray-500">Role:</span>
          <span className="font-medium text-gray-700 dark:text-gray-400 capitalize">{task.assignee_role.replace('_', ' ')}</span>
          {task.case_name && (<>
            <span className="text-gray-400 dark:text-gray-600">·</span>
            <span className="text-gray-500 dark:text-gray-500">Case:</span>
            <span className="font-medium text-gray-700 dark:text-gray-400">{task.case_name}</span>
          </>)}
          {task.client_name && (<>
            <span className="text-gray-400 dark:text-gray-600">·</span>
            <span className="text-gray-500 dark:text-gray-500">Client:</span>
            <span className="font-medium text-gray-700 dark:text-gray-400">{task.client_name}</span>
          </>)}
          <span className="text-gray-400 dark:text-gray-600">·</span>
          <span className="text-gray-500 dark:text-gray-500">Created:</span>
          <span className="font-medium text-gray-700 dark:text-gray-400">{formatDate(task.created_at)}</span>
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-4 p-4 overflow-y-auto">
        {/* Right column first on mobile (status + actions above fold) */}
        <div className="flex flex-col gap-4 md:order-2 md:w-64 shrink-0">

          {/* Actions card */}
          <div className="border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-3">
              Actions
            </p>
            {isPending ? (
              <div className="flex flex-col gap-2">
                <button
                  disabled={isSubmitting}
                  onClick={() => setPendingDecision('APPROVED')}
                  className="flex items-center gap-2 w-full px-3 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white text-xs font-semibold transition-colors"
                >
                  <Check className="h-3.5 w-3.5" /> Approve
                </button>
                <button
                  disabled={isSubmitting}
                  onClick={() => setPendingDecision('REJECTED')}
                  className="flex items-center gap-2 w-full px-3 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-40 text-white text-xs font-semibold transition-colors"
                >
                  <X className="h-3.5 w-3.5" /> Reject
                </button>
                <button
                  disabled={isSubmitting}
                  onClick={() => setPendingDecision('MORE_INFO_REQUESTED')}
                  className="flex items-center gap-2 w-full px-3 py-2 bg-sky-600 hover:bg-sky-700 disabled:opacity-40 text-white text-xs font-semibold transition-colors"
                >
                  <Info className="h-3.5 w-3.5" /> Request Info
                </button>
                {(decideMutation.isError || salesDecideMutation.isError) && (
                  <p className="text-xs text-red-500">Decision failed. Please retry.</p>
                )}
              </div>
            ) : (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                This task has been decided.
              </p>
            )}
          </div>
        </div>

        {/* Left column */}
        <div className="flex flex-col gap-4 md:order-1 flex-1">
          {/* Document / form preview card */}
          <div className="border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-3">
              Linked Document
            </p>
            {task.document_snapshot ? (
              <div className="flex flex-col gap-2">
                <div className="flex items-start gap-3">
                  <FileText className="h-8 w-8 text-gray-400 shrink-0 mt-0.5" />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-gray-900 dark:text-gray-100 truncate">
                      {task.document_snapshot.filename}
                    </p>
                    <p className="text-[10px] text-gray-500 capitalize mt-0.5">
                      {task.document_snapshot.category}
                    </p>
                    <span className={`inline-flex items-center mt-1 px-2 py-0.5 text-[10px] font-medium border ${STATUS_BADGE[task.document_snapshot.status] ?? 'border-gray-600/50 text-gray-400'}`}>
                      {task.document_snapshot.status}
                    </span>
                  </div>
                </div>
                <button
                  onClick={openPreview}
                  disabled={previewing}
                  className="flex items-center gap-1.5 mt-1 text-xs text-primary hover:underline disabled:opacity-50"
                >
                  {previewing
                    ? <Loader2 className="h-3 w-3 animate-spin" />
                    : <ExternalLink className="h-3 w-3" />}
                  {previewing ? 'Opening…' : 'Open Document'}
                </button>
              </div>
            ) : (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                No form or document linked to this task.
              </p>
            )}
          </div>

          {/* Validation result card — DOCUMENT_REVIEW only */}
          {isDocTask && (
            <div className="border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
              <AIValidationPanel
                result={fullDoc?.validation_result}
                isLoading={docLoading}
                onRunValidation={task.document_id ? () => validateMutation.mutate(task.document_id!) : undefined}
                isRunning={validateMutation.isPending}
              />
            </div>
          )}

        </div>
      </div>
    </>
  )
}
