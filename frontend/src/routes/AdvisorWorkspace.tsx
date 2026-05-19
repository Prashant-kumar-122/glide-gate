import { useWorkspaceStore } from '@/store/workspaceStore'
import { useWorkspaceSocket } from '@/hooks/useWorkspaceSocket'
import ClientRailNav from '@/features/advisor/ClientRailNav'
import DocumentWorkspacePanel from '@/features/advisor/DocumentWorkspacePanel'
import DocumentDetailDrawer from '@/features/advisor/DocumentDetailDrawer'
import { LayoutDashboard } from 'lucide-react'

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-12 text-center">
      <div className="rounded-full bg-blue-50 p-5">
        <LayoutDashboard className="h-8 w-8 text-blue-400" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Select a client</h2>
        <p className="mt-1 text-sm text-gray-500">
          Choose a client from the left panel to view their onboarding workspace.
        </p>
      </div>
    </div>
  )
}

export default function AdvisorWorkspace() {
  const { selectedCaseId, isDrawerOpen } = useWorkspaceStore()

  // Wire real-time socket updates for the active case
  useWorkspaceSocket(selectedCaseId)

  return (
    <div className="flex h-[calc(100vh-48px)]">
      {/* Left rail — client list */}
      <ClientRailNav />

      {/* Main workspace panel */}
      {selectedCaseId ? (
        <DocumentWorkspacePanel caseId={selectedCaseId} />
      ) : (
        <EmptyState />
      )}

      {/* Right drawer — document detail (conditionally rendered) */}
      {selectedCaseId && isDrawerOpen && (
        <DocumentDetailDrawer caseId={selectedCaseId} />
      )}
    </div>
  )
}
