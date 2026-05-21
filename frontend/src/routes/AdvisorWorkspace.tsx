import { useState } from 'react'
import { useWorkspaceStore } from '@/store/workspaceStore'
import { useWorkspaceSocket } from '@/hooks/useWorkspaceSocket'
import ClientRailNav from '@/features/advisor/ClientRailNav'
import DocumentWorkspacePanel from '@/features/advisor/DocumentWorkspacePanel'
import DocumentDetailDrawer from '@/features/advisor/DocumentDetailDrawer'
import { LayoutDashboard, PanelLeft } from 'lucide-react'

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center sm:p-12">
      <div className="rounded-full bg-blue-50 p-5 dark:bg-blue-950">
        <LayoutDashboard className="h-8 w-8 text-blue-400" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Select a client</h2>
        <p className="mt-1 text-sm text-gray-500 lg:hidden">
          Tap <span className="font-medium text-gray-700 dark:text-gray-300">Cases</span> above to browse and select a client.
        </p>
        <p className="mt-1 hidden text-sm text-gray-500 lg:block">
          Choose a client from the left panel to view their onboarding workspace.
        </p>
      </div>
    </div>
  )
}

export default function AdvisorWorkspace() {
  const { selectedCaseId, isDrawerOpen } = useWorkspaceStore()
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  useWorkspaceSocket(selectedCaseId)

  return (
    <div className="flex h-[calc(100vh-48px)] overflow-hidden">
      {/* Mobile sidebar backdrop */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <ClientRailNav
        isMobileOpen={mobileSidebarOpen}
        onMobileClose={() => setMobileSidebarOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Mobile-only top bar */}
        <div className="flex shrink-0 items-center gap-3 border-b border-gray-100 bg-white px-3 py-2 lg:hidden dark:border-gray-700 dark:bg-gray-800">
          <button
            onClick={() => setMobileSidebarOpen(true)}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-50 active:bg-gray-100 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700"
            aria-label="Open cases panel"
          >
            <PanelLeft className="h-3.5 w-3.5" />
            Cases
          </button>
          {selectedCaseId && (
            <span className="truncate text-xs text-gray-400">Workspace</span>
          )}
        </div>

        <div className="flex flex-1 overflow-hidden">
          {selectedCaseId ? (
            <DocumentWorkspacePanel caseId={selectedCaseId} />
          ) : (
            <EmptyState />
          )}

          {selectedCaseId && isDrawerOpen && (
            <DocumentDetailDrawer caseId={selectedCaseId} />
          )}
        </div>
      </div>
    </div>
  )
}
