import { useWorkspaceStore } from '@/store/workspaceStore'
import { useWorkspaceSocket } from '@/hooks/useWorkspaceSocket'
import DocumentWorkspacePanel from '@/features/advisor/DocumentWorkspacePanel'
import DocumentDetailDrawer from '@/features/advisor/DocumentDetailDrawer'
import CaseListTable from '@/features/advisor/CaseListTable'
import { LayoutDashboard, X } from 'lucide-react'

export default function AdvisorWorkspace() {
  const { selectedCaseId, isDrawerOpen, openTabs, activeTabId, closeCaseTab, setActiveTab } =
    useWorkspaceStore()

  useWorkspaceSocket(selectedCaseId)

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col overflow-hidden bg-gray-900">
      {/* Tab bar */}
      <div className="flex shrink-0 items-end gap-0 border-b border-gray-700 bg-gray-900 px-2">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={[
            'flex items-center gap-2 border-b-2 px-4 pb-3 pt-3 text-sm font-medium transition-colors',
            activeTabId === 'dashboard'
              ? 'border-blue-500 text-white'
              : 'border-transparent text-gray-400 hover:text-gray-200',
          ].join(' ')}
        >
          <LayoutDashboard className="h-3.5 w-3.5" />
          Dashboard
        </button>

        {openTabs.map((tab) => (
          <div
            key={tab.caseId}
            onClick={() => setActiveTab(tab.caseId)}
            className={[
              'group flex cursor-pointer items-center gap-1.5 border-b-2 px-4 pb-3 pt-3 text-sm transition-colors',
              activeTabId === tab.caseId
                ? 'border-blue-500 text-white'
                : 'border-transparent text-gray-400 hover:text-gray-200',
            ].join(' ')}
          >
            <span className="font-medium">{tab.label}</span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                closeCaseTab(tab.caseId)
              }}
              className="rounded p-0.5 text-gray-500 transition-colors hover:bg-gray-700 hover:text-gray-200"
              aria-label="Close tab"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>

      {/* Content */}
      {activeTabId === 'dashboard' ? (
        <CaseListTable />
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {selectedCaseId && <DocumentWorkspacePanel caseId={selectedCaseId} />}
          {selectedCaseId && isDrawerOpen && <DocumentDetailDrawer caseId={selectedCaseId} />}
        </div>
      )}
    </div>
  )
}
