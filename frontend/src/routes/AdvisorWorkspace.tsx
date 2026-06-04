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
  const scrollRef   = useRef<HTMLDivElement>(null)
  const activeTabRef = useRef<HTMLDivElement>(null)

  useWorkspaceSocket(selectedCaseId)

  useEffect(() => {
    activeTabRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
  }, [activeTabId])

  return (
    <div className="flex h-[calc(100vh-44px)] flex-col overflow-hidden bg-white dark:bg-gray-950">
      {/* Tab bar — professional underline style */}
      <div className="flex shrink-0 items-end border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950">
        {/* Dashboard tab — always pinned left */}
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

        {/* Divider */}
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
