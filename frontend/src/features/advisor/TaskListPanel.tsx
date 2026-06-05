import { useMemo, useCallback, useState } from 'react'
import type { ColDef, ICellRendererParams, CellStyle } from 'ag-grid-community'
import { BaseGrid, TruncatedCell } from '@/components/grid/BaseGrid'
import { useTasks } from '@/hooks/useTasks'
import type { TaskOut } from '@/lib/api'
import { useWorkspaceStore } from '@/store/workspaceStore'
import { useAuthStore } from '@/store/authStore'
import { Search, X } from 'lucide-react'

// ── Helpers ───────────────────────────────────────────────────────────────────

function relativeTime(dateStr: string): string {
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const days = Math.floor(diffMs / 86_400_000)
  if (days > 0) return `${days}d ago`
  const hours = Math.floor(diffMs / 3_600_000)
  if (hours > 0) return `${hours}h ago`
  return `${Math.floor(diffMs / 60_000)}m ago`
}

const TASK_TYPE_LABEL: Record<string, string> = {
  DOCUMENT_REVIEW: 'Doc Review',
  SALES_REVIEW:    'Sales Review',
}

const STATUS_DOT: Record<string, string> = {
  PENDING:             'bg-amber-500',
  APPROVED:            'bg-emerald-500',
  REJECTED:            'bg-red-500',
  MORE_INFO_REQUESTED: 'bg-sky-500',
}

const STATUS_TEXT: Record<string, string> = {
  PENDING:             'text-amber-400',
  APPROVED:            'text-emerald-400',
  REJECTED:            'text-red-400',
  MORE_INFO_REQUESTED: 'text-sky-400',
}

const STATUS_LABEL: Record<string, string> = {
  PENDING:             'Pending',
  APPROVED:            'Approved',
  REJECTED:            'Rejected',
  MORE_INFO_REQUESTED: 'More Info',
}

// ── Cell renderers ────────────────────────────────────────────────────────────

function TypeCell({ value }: ICellRendererParams<TaskOut, string>) {
  if (!value) return null
  return (
    <span style={{ color: 'rgb(var(--blue-400))' }}>
      {TASK_TYPE_LABEL[value] ?? value}
    </span>
  )
}

function StatusCell({ value }: ICellRendererParams<TaskOut, string>) {
  if (!value) return null
  const dot  = STATUS_DOT[value]  ?? 'bg-gray-500'
  const text = STATUS_TEXT[value] ?? 'text-gray-400'
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium ${text}`}>
      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dot}`} />
      {STATUS_LABEL[value] ?? value}
    </span>
  )
}

function OpenCell({ data, context }: ICellRendererParams<TaskOut>) {
  if (!data) return null
  return (
    <button
      onClick={() => context.openTask(data)}
      className="text-xs font-medium text-primary hover:underline"
    >
      Open in Case ›
    </button>
  )
}

function NoTasksOverlay() {
  return <span className="text-xs text-gray-500">No tasks found</span>
}

// ── Main component ────────────────────────────────────────────────────────────

export default function TaskListPanel() {
  const userRole = useAuthStore(s => s.user?.role) as 'advisor' | 'sales_manager' | undefined
  const role: 'advisor' | 'sales_manager' = userRole === 'sales_manager' ? 'sales_manager' : 'advisor'
  const { data: tasks = [], isLoading } = useTasks(role)
  const { openCaseTab } = useWorkspaceStore()
  const [search, setSearch] = useState('')

  const openTask = useCallback((task: TaskOut) => {
    openCaseTab(task.case_id, '', task.case_name ?? task.case_id.slice(0, 8))
  }, [openCaseTab])

  const context = useMemo(() => ({ openTask }), [openTask])

  const colDefs = useMemo<ColDef<TaskOut>[]>(() => [
    {
      headerName: 'Client',
      field: 'client_name',
      flex: 1.2,
      minWidth: 130,
      filter: 'agTextColumnFilter',
      cellRenderer: TruncatedCell,
      cellRendererParams: { style: { fontWeight: '600' } },
      valueFormatter: (p) => p.value ?? '—',
    },
    {
      headerName: 'Case Name',
      field: 'case_name',
      flex: 1.2,
      minWidth: 130,
      filter: 'agTextColumnFilter',
      cellRenderer: TruncatedCell,
      valueFormatter: (p) => p.value ?? p.data?.case_id?.slice(0, 8) ?? '—',
    },
    {
      headerName: 'Task',
      field: 'title',
      flex: 2,
      minWidth: 200,
      filter: 'agTextColumnFilter',
      cellRenderer: TruncatedCell,
    },
    {
      headerName: 'Type',
      field: 'task_type',
      width: 130,
      cellRenderer: TypeCell,
      filter: false,
    },
    {
      headerName: 'Status',
      field: 'status',
      width: 140,
      cellRenderer: StatusCell,
      filter: false,
    },
    {
      headerName: 'Created',
      field: 'created_at',
      width: 110,
      filter: false,
      valueFormatter: (p) => relativeTime(p.value),
      cellRendererParams: { style: { color: 'rgb(var(--gray-400))', fontVariantNumeric: 'tabular-nums' } },
    },
    {
      headerName: '',
      field: 'id',
      width: 120,
      sortable: false,
      filter: false,
      resizable: false,
      cellRenderer: OpenCell,
      cellStyle: { display: 'flex', alignItems: 'center', justifyContent: 'flex-end' } as CellStyle,
    },
  ], [])

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-white dark:bg-gray-950 p-4 sm:p-6">
      {/* Toolbar */}
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3 w-3 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search tasks…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-48 border border-gray-200 bg-white py-1.5 pl-8 pr-8 text-xs text-gray-800 placeholder-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:placeholder-gray-600"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
        {!isLoading && tasks.length > 0 && (
          <p className="font-mono text-xs text-gray-500 dark:text-gray-400">
            <span className="font-semibold text-gray-800 dark:text-gray-100">{tasks.length}</span> tasks
          </p>
        )}
      </div>

      {/* Grid — same wrapper pattern as CaseListTable */}
      <div className="flex-1 overflow-hidden border border-gray-200 dark:border-gray-800">
        <BaseGrid<TaskOut>
          rowData={isLoading ? undefined : tasks}
          columnDefs={colDefs}
          context={context}
          quickFilterText={search}
          noRowsOverlayComponent={NoTasksOverlay}
        />
      </div>
    </div>
  )
}
