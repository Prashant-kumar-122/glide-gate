import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { useTasks, useTaskDetail } from '@/hooks/useTasks'
import { useCaseProgress, useCaseDetail, useQuestionnaireSchema, useCollectedFields } from '@/hooks/useDocuments'
import { useComments } from '@/hooks/useComments'
import { useAuthStore } from '@/store/authStore'
import { useWorkspaceStore } from '@/store/workspaceStore'
import DocumentWorkspacePanel from './DocumentWorkspacePanel'
import ParallelProductTracks from './ParallelProductTracks'
import TaskRow from './TaskRow'
import TaskDetailView from './TaskDetailView'
import OnboardingFormView from '@/features/client/OnboardingFormView'
import type { TaskOut } from '@/lib/api'

type InnerTab = 'overview' | 'products' | 'documents' | 'application' | string // string = taskId

interface CaseOverviewPanelProps {
  caseId: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function relativeTime(dateStr: string): string {
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const days = Math.floor(diffMs / 86_400_000)
  if (days > 0) return `${days}d ago`
  const hours = Math.floor(diffMs / 3_600_000)
  if (hours > 0) return `${hours}h ago`
  return `${Math.floor(diffMs / 60_000)}m ago`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

const STAGE_BADGE: Record<string, string> = {
  INTAKE:            'bg-gray-500/10 border-gray-500/30 text-gray-400',
  REVIEW:            'bg-amber-500/10 border-amber-500/30 text-amber-400',
  SALES_REVIEW:      'bg-amber-500/10 border-amber-500/30 text-amber-400',
  KYC:               'bg-blue-500/10 border-blue-500/30 text-blue-400',
  PARALLEL_PRODUCTS: 'bg-violet-500/10 border-violet-500/30 text-violet-400',
  COMPLETE:          'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
  ESCALATED:         'bg-red-500/10 border-red-500/30 text-red-400',
}

const STAGE_LABEL: Record<string, string> = {
  INTAKE:            'Intake',
  REVIEW:            'Advisor Review',
  SALES_REVIEW:      'Sales Review',
  KYC:               'KYC',
  PARALLEL_PRODUCTS: 'Products',
  COMPLETE:          'Complete',
  ESCALATED:         'Escalated',
}

// ── Case summary strip ────────────────────────────────────────────────────────

function CaseSummaryStrip({ caseId }: { caseId: string }) {
  const { data: summary } = useCaseProgress(caseId)
  const { data: detail } = useCaseDetail(caseId)
  const { data: comments = [] } = useComments(caseId)

  if (!summary && !detail) return null

  const productsLabel = summary?.products?.length
    ? summary.products.map(p => p.product_name.replace(/_/g, ' ')).join(' & ')
    : detail?.selected_products?.length
    ? detail.selected_products.map(p => p.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())).join(' & ')
    : null

  const clientName = summary?.case_name || detail?.case_name || productsLabel || summary?.client_name || detail?.client_name || '…'
  const stage        = summary?.current_stage ?? detail?.current_stage ?? ''

  const products     = summary?.products ?? []
  const shortId      = detail?.id?.slice(0, 8) ?? '…'
  const assignedTo   = detail?.assigned_advisor_name ?? '—'
  const createdLabel = detail?.created_at ? formatDate(detail.created_at) : '—'
  const updatedLabel = detail?.updated_at ? relativeTime(detail.updated_at) : '—'


  const progress = summary?.overall_progress ?? 0
  const progressColor =
    progress >= 80 ? 'bg-emerald-500' :
    progress >= 40 ? 'bg-primary' :
    'bg-amber-500'

  return (
    <div className="shrink-0 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
      <div className="flex items-start justify-between gap-4 px-5 py-3.5">

        {/* Left — name · badges · metadata */}
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-bold text-gray-900 dark:text-gray-100 truncate leading-tight">
            {clientName}
          </h2>

          {/* Badge row — products only */}
          <div className="flex flex-wrap items-center gap-1.5 mt-2">
            {products.slice(0, 2).map(p => (
              <span
                key={p.product_code}
                className="inline-flex items-center px-2 py-0.5 text-[11px] font-medium border bg-blue-500/10 border-blue-500/30 text-blue-400 dark:text-blue-300"
              >
                {p.product_name.replace(/_/g, ' ')}
              </span>
            ))}
          </div>

          {/* Metadata row */}
          <p className="mt-2 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[11px]">
            <span className="text-gray-500 dark:text-gray-500">Entity ID:</span>
            <span className="font-medium text-gray-700 dark:text-gray-400">{shortId}</span>
            <span className="text-gray-400 dark:text-gray-600">·</span>
            <span className="text-gray-500 dark:text-gray-500">Assigned To:</span>
            <span className="font-medium text-gray-700 dark:text-gray-400">{assignedTo}</span>
            <span className="text-gray-400 dark:text-gray-600">·</span>
            <span className="text-gray-500 dark:text-gray-500">Created:</span>
            <span className="font-medium text-gray-700 dark:text-gray-400">{createdLabel}</span>
            <span className="text-gray-400 dark:text-gray-600">·</span>
            <span className="text-gray-500 dark:text-gray-500">Updated:</span>
            <span className="font-medium text-gray-700 dark:text-gray-400">{updatedLabel}</span>
          </p>
        </div>

        {/* Right — progress + stage */}
        <div className="shrink-0 text-right flex flex-col items-end gap-1.5">
          <p className="font-mono text-2xl font-bold tabular-nums text-gray-900 dark:text-gray-100 leading-none">
            {progress}%
          </p>
          <p className="text-[10px] text-gray-400">completion</p>
          {stage && (
            <span className={`inline-flex items-center px-2 py-0.5 text-[11px] font-medium border ${STAGE_BADGE[stage] ?? 'bg-gray-500/10 border-gray-500/30 text-gray-400'}`}>
              {STAGE_LABEL[stage] ?? stage}
            </span>
          )}
        </div>

      </div>

      {/* Progress bar */}
      <div className="h-1 w-full bg-gray-100 dark:bg-gray-800">
        <div
          className={`h-1 transition-all duration-500 ${progressColor}`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  )
}

// ── Overview tab content ──────────────────────────────────────────────────────

function OverviewTab({
  tasks,
  isLoading,
  onOpenTask,
}: {
  tasks: TaskOut[]
  isLoading: boolean
  onOpenTask: (task: TaskOut) => void
}) {
  const [filter, setFilter] = useState<'pending' | 'completed'>('pending')

  const pending = tasks.filter(t => t.status === 'PENDING')
  const completed = tasks.filter(t => t.status !== 'PENDING')
  const displayed = filter === 'pending' ? pending : completed

  return (
    <div className="flex flex-col flex-1 overflow-y-auto p-4 gap-4">
      {/* Sub-tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-800">
        {(['pending', 'completed'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={[
              'px-4 py-2 text-xs font-medium border-b-2 transition-colors capitalize',
              filter === f
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
            ].join(' ')}
          >
            {f === 'pending' ? `Pending (${pending.length})` : `Completed (${completed.length})`}
          </button>
        ))}
      </div>

      {/* Task rows */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2].map(i => (
            <div key={i} className="h-14 animate-pulse bg-gray-100 dark:bg-gray-800" />
          ))}
        </div>
      ) : displayed.length === 0 ? (
        <p className="text-xs text-gray-500 dark:text-gray-400 py-4 text-center">
          No {filter} tasks.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {displayed.map(t => (
            <TaskRow key={t.id} task={t} onOpen={() => onOpenTask(t)} />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Task detail sub-tab wrapper ────────────────────────────────────────────────

function TaskDetailTab({ taskId, caseId }: { taskId: string; caseId: string }) {
  const { data: task, isLoading } = useTaskDetail(taskId)

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="h-5 w-5 border-2 border-primary border-t-transparent animate-spin" />
      </div>
    )
  }
  if (!task) {
    return (
      <div className="p-6 text-xs text-gray-500">Task not found.</div>
    )
  }
  return <TaskDetailView task={task} caseId={caseId} />
}

// ── Main component ────────────────────────────────────────────────────────────

export default function CaseOverviewPanel({ caseId }: CaseOverviewPanelProps) {
  const [activeTab, setActiveTab] = useState<InnerTab>('overview')
  const [openTaskTabs, setOpenTaskTabs] = useState<TaskOut[]>([])
  const userRole = useAuthStore(s => s.user?.role) as 'advisor' | 'sales_manager' | undefined
  const role: 'advisor' | 'sales_manager' = userRole === 'sales_manager' ? 'sales_manager' : 'advisor'
  const { data: allTasks = [], isLoading: tasksLoading } = useTasks(role, caseId)
  const { pendingTaskId, setPendingTaskId } = useWorkspaceStore()

  const pendingCount = allTasks.filter(t => t.status === 'PENDING').length

  // Auto-open task sub-tab when navigating from My Tasks dashboard
  useEffect(() => {
    if (!pendingTaskId || allTasks.length === 0) return
    const task = allTasks.find(t => t.id === pendingTaskId)
    if (task) {
      setOpenTaskTabs(prev => prev.find(t => t.id === task.id) ? prev : [...prev, task])
      setActiveTab(task.id)
      setPendingTaskId(null)
    }
  }, [pendingTaskId, allTasks, setPendingTaskId])

  function openTaskTab(task: TaskOut) {
    if (!openTaskTabs.find(t => t.id === task.id)) {
      setOpenTaskTabs(prev => [...prev, task])
    }
    setActiveTab(task.id)
  }

  function closeTaskTab(taskId: string) {
    setOpenTaskTabs(prev => prev.filter(t => t.id !== taskId))
    if (activeTab === taskId) setActiveTab('overview')
  }

  const staticTabs = [
    { id: 'overview' as const,  label: `Tasks${pendingCount > 0 ? ` (${pendingCount})` : ''}` },
    { id: 'products' as const,  label: 'Product Tracks' },
    { id: 'documents' as const, label: 'Documents' },
    { id: 'application' as const, label: 'Application' },
  ]

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Case summary strip — always visible */}
      <CaseSummaryStrip caseId={caseId} />

      {/* Inner tab bar */}
      <div className="flex shrink-0 overflow-x-auto border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 [&::-webkit-scrollbar]:h-[2px]">
        {staticTabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={[
              'shrink-0 whitespace-nowrap border-b-2 px-4 py-2.5 text-xs font-medium transition-colors',
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
            ].join(' ')}
          >
            {tab.label}
          </button>
        ))}

        {openTaskTabs.map(task => (
          <div
            key={task.id}
            className={[
              'shrink-0 flex items-center gap-1 whitespace-nowrap border-b-2 pl-4 pr-2 py-2.5 text-xs font-medium cursor-pointer transition-colors',
              activeTab === task.id
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
            ].join(' ')}
            onClick={() => setActiveTab(task.id)}
          >
            <span className="truncate max-w-[120px]">
              {task.title.length > 18 ? task.title.slice(0, 18) + '…' : task.title}
            </span>
            <button
              onClick={e => { e.stopPropagation(); closeTaskTab(task.id) }}
              className="rounded-sm p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
              aria-label="Close tab"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {activeTab === 'overview' && (
          <OverviewTab tasks={allTasks} isLoading={tasksLoading} onOpenTask={openTaskTab} />
        )}
        {activeTab === 'products' && (
          <ProductsTab caseId={caseId} />
        )}
        {activeTab === 'documents' && (
          <DocumentWorkspacePanel caseId={caseId} />
        )}
        {activeTab === 'application' && (
          <ApplicationTab caseId={caseId} />
        )}
        {openTaskTabs.map(task => (
          activeTab === task.id && (
            <TaskDetailTab key={task.id} taskId={task.id} caseId={caseId} />
          )
        ))}
      </div>
    </div>
  )
}

// ── Products tab ─────────────────────────────────────────────────────────────

function ProductsTab({ caseId }: { caseId: string }) {
  const { data: summary, isLoading } = useCaseProgress(caseId)
  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-5">
      <ParallelProductTracks tracks={summary?.products ?? []} isLoading={isLoading} />
    </div>
  )
}

// ── Application tab (thin wrapper around the existing form view) ──────────────

function ApplicationTab({ caseId }: { caseId: string }) {
  const { data: schemaData, isLoading: schemaLoading } = useQuestionnaireSchema(caseId)
  const { data: collectedData, isLoading: collectedLoading } = useCollectedFields(caseId)
  return (
    <OnboardingFormView
      caseId={caseId}
      clientData={collectedData?.client_data ?? {}}
      schema={schemaData?.fields ?? []}
      isLoading={schemaLoading || collectedLoading}
      readOnly
      hideReadOnlyLabel
    />
  )
}
