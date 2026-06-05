import { useRef, useEffect, useState } from 'react'
import { useWorkspaceStore } from '@/store/workspaceStore'
import { useWorkspaceSocket } from '@/hooks/useWorkspaceSocket'
import { useAuthStore } from '@/store/authStore'
import { useTasks } from '@/hooks/useTasks'
import { useCases } from '@/hooks/useDocuments'
import CaseOverviewPanel from '@/features/advisor/CaseOverviewPanel'
import DocumentDetailDrawer from '@/features/advisor/DocumentDetailDrawer'
import CaseListTable from '@/features/advisor/CaseListTable'
import TaskListPanel from '@/features/advisor/TaskListPanel'

import WorkflowTracker from '@/features/advisor/WorkflowTracker'
import { LayoutDashboard, X } from 'lucide-react'

export default function AdvisorWorkspace() {
  const { selectedCaseId, isDrawerOpen, openTabs, activeTabId, closeCaseTab, setActiveTab } =
    useWorkspaceStore()
  const scrollRef = useRef<HTMLDivElement>(null)
  const activeTabRef = useRef<HTMLDivElement>(null)
  const [activeView, setActiveView] = useState<'cases' | 'tasks'>('cases')

  const userRole = useAuthStore(s => s.user?.role) as 'advisor' | 'sales_manager' | undefined
  const role: 'advisor' | 'sales_manager' = userRole === 'sales_manager' ? 'sales_manager' : 'advisor'
  const { data: tasks = [] } = useTasks(role)
  const { data: cases = [] } = useCases()

  const pendingTaskCount = tasks.filter(t => t.status === 'PENDING').length

  useWorkspaceSocket(selectedCaseId)

  useEffect(() => {
    activeTabRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
  }, [activeTabId])

  return (
    <div className="flex h-[calc(100vh-44px)] flex-col overflow-hidden bg-white dark:bg-gray-950">
      {/* Tab bar */}
      <div className="flex shrink-0 items-end border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950">
        {/* Dashboard tab */}
        <div className="shrink-0 px-1">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={[
              'flex items-center gap-1.5 border-b-2 px-4 pb-2.5 pt-2.5 text-xs font-medium transition-colors whitespace-nowrap',
              activeTabId === 'dashboard'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-300',
            ].join(' ')}
          >
            <LayoutDashboard className="h-3 w-3" />
            Dashboard
          </button>
        </div>

        <div className="h-4 w-px bg-gray-200 dark:bg-gray-800 self-center shrink-0" />

        {/* Scrollable case tabs */}
        <div
          ref={scrollRef}
          className="flex min-w-0 flex-1 items-end overflow-x-auto [&::-webkit-scrollbar]:h-[2px] [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-gray-300 dark:[&::-webkit-scrollbar-thumb]:bg-gray-700"
        >
          {openTabs.map((tab) => {
            const isActive = activeTabId === tab.caseId
            return (
              <div
                key={tab.caseId}
                ref={isActive ? activeTabRef : undefined}
                onClick={() => setActiveTab(tab.caseId)}
                className={[
                  'group flex shrink-0 cursor-pointer items-center gap-1.5 border-b-2 px-4 pb-2.5 pt-2.5 text-xs transition-colors whitespace-nowrap',
                  isActive
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-300',
                ].join(' ')}
              >
                <span className="font-medium">{tab.label}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    closeCaseTab(tab.caseId)
                  }}
                  className="rounded-sm p-0.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
                  aria-label="Close tab"
                >
                  <X className="h-2.5 w-2.5" />
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {/* Content */}
      {activeTabId === 'dashboard' ? (
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* View toggle */}
          <div className="flex shrink-0 items-center gap-1 border-b border-gray-200 dark:border-gray-800 px-4 py-2">
            <button
              onClick={() => setActiveView('tasks')}
              className={[
                'flex items-center gap-1.5 border-b-2 px-3 pb-1.5 pt-1.5 text-xs font-medium transition-colors',
                activeView === 'tasks'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-300',
              ].join(' ')}
            >
              My Tasks
              {pendingTaskCount > 0 && (
                <span className="inline-flex items-center justify-center h-4 min-w-[16px] px-1 text-[10px] font-bold bg-amber-500 text-white rounded-full">
                  {pendingTaskCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveView('cases')}
              className={[
                'flex items-center gap-1.5 border-b-2 px-3 pb-1.5 pt-1.5 text-xs font-medium transition-colors',
                activeView === 'cases'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-300',
              ].join(' ')}
            >
              All Cases
              <span className="inline-flex items-center justify-center h-4 min-w-[16px] px-1 text-[10px] font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full">
                {cases.length}
              </span>
            </button>
          </div>

          {activeView === 'tasks' ? <TaskListPanel /> : <CaseListTable />}
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden md:flex-row">
          {selectedCaseId && <WorkflowTracker caseId={selectedCaseId} />}
          {selectedCaseId && <CaseOverviewPanel caseId={selectedCaseId} />}
          {selectedCaseId && isDrawerOpen && <DocumentDetailDrawer caseId={selectedCaseId} />}
        </div>
      )}
    </div>
  )
}
