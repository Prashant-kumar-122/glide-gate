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
      <div className="rounded-full bg-blue-50 p-5">
        <LayoutDashboard className="h-8 w-8 text-blue-400" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Select a client</h2>
        {/* Context-aware hint: different text for mobile vs desktop */}
        <p className="mt-1 text-sm text-gray-500 lg:hidden">
          Tap <span className="font-medium text-gray-700">Cases</span> above to browse and select a client.
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

  // Wire real-time socket updates for the active case
  useWorkspaceSocket(selectedCaseId)

  return (
    <div className="flex h-[calc(100vh-48px)] overflow-hidden">
      {/* Mobile sidebar backdrop — covers main content when sidebar is open */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Left rail — mobile: fixed slide-in overlay; desktop: static sidebar */}
      <ClientRailNav
        isMobileOpen={mobileSidebarOpen}
        onMobileClose={() => setMobileSidebarOpen(false)}
      />

      {/* Main content wrapper — takes all remaining width */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Mobile-only top bar: cases toggle button */}
        <div className="flex shrink-0 items-center gap-3 border-b border-gray-100 bg-white px-3 py-2 lg:hidden">
          <button
            onClick={() => setMobileSidebarOpen(true)}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-50 active:bg-gray-100"
            aria-label="Open cases panel"
          >
            <PanelLeft className="h-3.5 w-3.5" />
            Cases
          </button>
          {selectedCaseId && (
            <span className="truncate text-xs text-gray-400">Workspace</span>
          )}
        </div>

        {/* Content row: workspace panel + detail drawer side by side */}
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
