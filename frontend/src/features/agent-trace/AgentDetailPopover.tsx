import { X, Clock, CheckCircle, AlertTriangle, Loader } from 'lucide-react'
import { useTraceStore } from '@/store/traceStore'
import { AGENT_LABELS } from './agentPositions'
import { formatTaskLabel } from './taskLabels'
import type { AgentId } from './agentPositions'
import type { AgentTraceOut } from '@/lib/api'

const CANVAS_TO_A2A: Record<string, string> = {
  product_onboarding_cash: 'product_onboarding',
  product_onboarding_retirement: 'product_onboarding',
}

const STATUS_ICON: Record<string, React.ReactElement> = {
  SUCCESS: <CheckCircle className="h-3.5 w-3.5 text-green-500" />,
  FAILED: <AlertTriangle className="h-3.5 w-3.5 text-red-500" />,
  ESCALATED: <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />,
  PARTIAL: <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />,
}

const STATE_BADGE: Record<string, string> = {
  idle: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
  active: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  escalated: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  complete: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
}

interface Props {
  agentId: string
  traceData?: AgentTraceOut
  onClose: () => void
}

export function AgentDetailPopover({ agentId, traceData, onClose }: Props) {
  const nodeState = useTraceStore((s) => s.nodeStates[agentId] ?? 'idle')
  const label = AGENT_LABELS[agentId as AgentId] ?? agentId

  const a2aId = CANVAS_TO_A2A[agentId] ?? agentId
  const agentInfo = traceData?.agents.find(
    (a) => a.agent_type === a2aId || a.agent_type === agentId || a.id === agentId,
  )
  const recentTasks = (
    traceData?.tasks.filter(
      (t) => t.from_agent === a2aId || t.to_agent === a2aId ||
             t.from_agent === agentId || t.to_agent === agentId,
    ) ?? []
  )
    .slice()
    .reverse()

  return (
    <div className="border-b border-gray-200 p-4 dark:border-gray-700">
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{label}</p>
          {agentInfo?.description && (
            <p className="truncate text-[10px] text-gray-400">{agentInfo.description}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span
            className={[
              'px-2 py-0.5 text-[10px] font-medium capitalize',
              STATE_BADGE[nodeState] ?? STATE_BADGE.idle,
            ].join(' ')}
          >
            {nodeState}
          </span>
          <button
            onClick={onClose}
            className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Recent tasks */}
      {recentTasks.length > 0 ? (
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
            Tasks ({recentTasks.length})
          </p>
          <ul className="max-h-48 space-y-1.5 overflow-y-auto">
            {recentTasks.map((task) => (
              <li key={task.id} className="flex items-center gap-2 bg-gray-50 px-2 py-1.5 dark:bg-gray-800">
                {STATUS_ICON[task.status] ?? <Loader className="h-3.5 w-3.5 text-gray-400" />}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[10px] font-medium text-gray-700 dark:text-gray-200">
                    {formatTaskLabel(task.task_type)}
                  </p>
                  <p className="text-[9px] text-gray-400">
                    {task.from_agent} → {task.to_agent}
                  </p>
                </div>
                {task.duration_ms !== undefined && (
                  <span className="flex shrink-0 items-center gap-0.5 text-[9px] text-gray-400">
                    <Clock className="h-2.5 w-2.5" />
                    {task.duration_ms}ms
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-[11px] text-gray-400">
          No tasks recorded yet for this agent.
        </p>
      )}
    </div>
  )
}
