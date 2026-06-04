import { useRef, useEffect } from 'react'
import { useWorkspaceStore } from '@/store/workspaceStore'
import { useWorkspaceSocket } from '@/hooks/useWorkspaceSocket'
import DocumentWorkspacePanel from '@/features/advisor/DocumentWorkspacePanel'
import DocumentDetailDrawer from '@/features/advisor/DocumentDetailDrawer'
import CaseListTable from '@/features/advisor/CaseListTable'
import WorkflowTracker from '@/features/advisor/WorkflowTracker'
import { LayoutDashboard, X } from 'lucide-react'

export default function AdvisorWorkspace() {
  const { selectedCaseId, isDrawerOpen, openTabs, activeTabId, closeCaseTab, setActiveTab } =
    useWorkspaceStore()
  const scrollRef = useRef<HTMLDivElement>(null)
  const activeTabRef = useRef<HTMLDivElement>(null)

  useWorkspaceSocket(selectedCaseId)

  // Scroll active tab into view whenever it changes
  useEffect(() => {
    activeTabRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
  }, [activeTabId])

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col overflow-hidden bg-white dark:bg-gray-900">
      {/* Tab bar */}
      <div className="flex shrink-0 items-end border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
        {/* Dashboard — always visible, never scrolls away */}
        <div className="shrink-0 px-2">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={[
              'flex items-center gap-2 border-b-2 px-4 pb-3 pt-3 text-sm font-medium transition-colors whitespace-nowrap',
              activeTabId === 'dashboard'
                ? 'border-blue-500 text-gray-900 dark:text-white'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
            ].join(' ')}
          >
            <LayoutDashboard className="h-3.5 w-3.5" />
            Dashboard
          </button>
        </div>

        {/* Scrollable case tabs */}
        <div
          ref={scrollRef}
          className="flex min-w-0 flex-1 items-end overflow-x-auto [&::-webkit-scrollbar]:h-[3px] [&::-webkit-scrollbar-track]:bg-white dark:[&::-webkit-scrollbar-track]:bg-gray-900 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 dark:[&::-webkit-scrollbar-thumb]:bg-gray-600"
        >
          {openTabs.map((tab) => {
            const isActive = activeTabId === tab.caseId
            return (
              <div
                key={tab.caseId}
                ref={isActive ? activeTabRef : undefined}
                onClick={() => setActiveTab(tab.caseId)}
                className={[
                  'group flex shrink-0 cursor-pointer items-center gap-1.5 border-b-2 px-4 pb-3 pt-3 text-sm transition-colors whitespace-nowrap',
                  isActive
                    ? 'border-blue-500 text-gray-900 dark:text-white'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
                ].join(' ')}
              >
                <span className="font-medium">{tab.label}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    closeCaseTab(tab.caseId)
                  }}
                  className="rounded p-0.5 text-gray-500 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-200"
                  aria-label="Close tab"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {/* Content */}
      {activeTabId === 'dashboard' ? (
        <CaseListTable />
      ) : (
        <div className="flex flex-1 flex-col overflow-y-auto md:flex-row md:overflow-hidden">
          {selectedCaseId && <WorkflowTracker caseId={selectedCaseId} />}
          {selectedCaseId && <DocumentWorkspacePanel caseId={selectedCaseId} />}
          {selectedCaseId && isDrawerOpen && <DocumentDetailDrawer caseId={selectedCaseId} />}
        </div>
      )}
    </div>
  )
}
