import type { TaskOut } from '@/lib/api'

interface TaskRowProps {
  task: TaskOut
  onOpen: (taskId: string) => void
}

function relativeTime(dateStr: string): string {
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const days = Math.floor(diffMs / 86_400_000)
  if (days > 0) return `${days}d ago`
  const hours = Math.floor(diffMs / 3_600_000)
  if (hours > 0) return `${hours}h ago`
  return `${Math.floor(diffMs / 60_000)}m ago`
}

const STATUS_BADGE: Record<string, string> = {
  PENDING: 'border-amber-600/50 text-amber-400',
  APPROVED: 'border-green-600/50 text-green-400',
  REJECTED: 'border-red-600/50 text-red-400',
  MORE_INFO_REQUESTED: 'border-sky-600/50 text-sky-400',
}

const STATUS_DOT: Record<string, string> = {
  PENDING: 'bg-amber-500',
  APPROVED: 'bg-green-500',
  REJECTED: 'bg-red-500',
  MORE_INFO_REQUESTED: 'bg-sky-500',
}

const TYPE_LABEL: Record<string, string> = {
  DOCUMENT_REVIEW: 'Doc Review',
  SALES_REVIEW: 'Sales Review',
}

export default function TaskRow({ task, onOpen }: TaskRowProps) {
  const badge = STATUS_BADGE[task.status] ?? 'border-gray-600/50 text-gray-400'
  const dot = STATUS_DOT[task.status] ?? 'bg-gray-500'
  const statusLabel = task.status === 'MORE_INFO_REQUESTED'
    ? 'More Info'
    : task.status.charAt(0) + task.status.slice(1).toLowerCase()

  return (
    <div className="flex items-start justify-between gap-3 border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-gray-900 dark:text-gray-100 truncate">
            {task.title}
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide border border-blue-600/50 text-blue-400 shrink-0">
            {TYPE_LABEL[task.task_type] ?? task.task_type}
          </span>
          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide border shrink-0 ${badge}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
            {statusLabel}
          </span>
        </div>
        <p className="mt-1 text-[10px] text-gray-500 dark:text-gray-400">
          {task.assignee_id ? `Assignee: ${task.assignee_id.slice(0, 8)}` : 'Unassigned'}
          {' · '}Created {relativeTime(task.created_at)}
        </p>
      </div>
      <button
        onClick={() => onOpen(task.id)}
        className="shrink-0 flex items-center gap-1 border border-gray-600/50 px-3 py-1.5 text-[10px] font-medium uppercase tracking-wide text-gray-400 hover:border-primary/60 hover:text-primary transition-colors"
      >
        Review Task &rsaquo;
      </button>
    </div>
  )
}
