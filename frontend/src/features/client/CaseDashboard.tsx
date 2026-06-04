import { useState } from 'react'
import { Building2, Plus } from 'lucide-react'
import { useQueries } from '@tanstack/react-query'
import { useCases, qk } from '@/hooks/useDocuments'
import { api } from '@/lib/api'
import CaseCard from '@/features/client/CaseCard'
import ClientDocumentModal from '@/features/client/ClientDocumentModal'
import PendingDocumentsGrid from '@/features/client/PendingDocumentsGrid'
import type { PendingDoc } from '@/features/client/PendingDocumentsGrid'
import type { CaseOut, DocumentOut } from '@/lib/api'

interface Props {
  firstName: string
  onOpenNewAccount: () => void
  onOpenCase: (c: CaseOut) => void
}

type Tab = 'pending' | 'live' | 'documents'

function padCount(n: number) {
  return String(n).padStart(2, '0')
}

export default function CaseDashboard({ firstName, onOpenNewAccount, onOpenCase }: Props) {
  const { data: cases = [], isLoading } = useCases()
  const [activeTab,   setActiveTab]   = useState<Tab>('pending')
  const [selectedDoc, setSelectedDoc] = useState<PendingDoc | null>(null)

  const inProgress = cases.filter((c) => c.current_stage !== 'COMPLETE')
  const completed  = cases.filter((c) => c.current_stage === 'COMPLETE')

  const docQueries = useQueries({
    queries: cases.map((c) => ({
      queryKey: qk.documents(c.id),
      queryFn: (): Promise<DocumentOut[]> => api.get(`/cases/${c.id}/documents`).then((r) => r.data),
      staleTime: 20_000,
    })),
  })

  const docsLoading = docQueries.some((q) => q.isLoading)

  const pendingDocs: PendingDoc[] = docQueries.flatMap((q, i) => {
    if (!q.data) return []
    const c = cases[i]
    const caseName   = c?.case_name ?? c?.id ?? ''
    const clientName = c?.client_name ?? '—'
    return q.data
      .filter((d) => d.status !== 'APPROVED' && d.status !== 'NOT_REQUESTED')
      .map((d) => ({ ...d, caseName, clientName }))
  })

  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: 'pending',   label: 'Pending Applications', count: inProgress.length },
    { id: 'live',      label: 'Live Accounts',         count: completed.length },
    { id: 'documents', label: 'Pending Documents',     count: pendingDocs.length },
  ]

  const visibleCases = activeTab === 'pending' ? inProgress : completed

  return (
    <div>
      {/* Sticky header */}
      <div className="sticky top-0 z-10 border-b border-gray-200 bg-white px-4 pb-0 pt-5 dark:border-gray-800 dark:bg-gray-950 sm:px-6">
        {/* Title row */}
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400">
              Client Portal
            </p>
            <h1 className="text-lg font-semibold tracking-tight text-gray-900 dark:text-gray-100">
              Welcome, {firstName}
            </h1>
            <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
              Account overview and pending applications
            </p>
          </div>
          {/* Full-width on mobile, auto on sm+ */}
          <button
            onClick={onOpenNewAccount}
            className="flex w-full items-center justify-center gap-2 bg-primary px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-primary-hover sm:w-auto"
          >
            <Plus className="h-3.5 w-3.5" />
            Open New Account
          </button>
        </div>

        {/* Tab bar — scrollable on mobile */}
        <div className="flex gap-0 overflow-x-auto [&::-webkit-scrollbar]:hidden">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={[
                  'flex shrink-0 items-center gap-1.5 border-b-2 px-4 pb-3 pt-1 text-xs font-medium whitespace-nowrap transition-colors',
                  isActive
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300',
                ].join(' ')}
              >
                {tab.label}
                <span className={[
                  'font-mono text-[10px]',
                  isActive ? 'text-primary' : 'text-gray-400 dark:text-gray-500',
                ].join(' ')}>
                  ({padCount(tab.count)})
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Content area */}
      <div className="min-h-[calc(100vh-200px)] bg-gray-50 p-4 dark:bg-gray-950 sm:p-6">

        {/* Pending / Live tabs */}
        {activeTab !== 'documents' && (
          <>
            {isLoading && (
              <div className="flex justify-center py-16">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-200 border-t-primary dark:border-gray-700" />
              </div>
            )}

            {!isLoading && visibleCases.length > 0 && (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {visibleCases.map((c) => (
                  <CaseCard key={c.id} caseData={c} onClick={() => onOpenCase(c)} />
                ))}
              </div>
            )}

            {!isLoading && visibleCases.length === 0 && cases.length > 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Building2 className="mb-4 h-8 w-8 text-gray-300 dark:text-gray-700" />
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {activeTab === 'pending' ? 'No pending applications' : 'No live accounts yet'}
                </p>
                {activeTab === 'pending' && (
                  <button
                    onClick={onOpenNewAccount}
                    className="mt-4 flex items-center gap-2 bg-primary px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-primary-hover"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Open New Account
                  </button>
                )}
              </div>
            )}

            {!isLoading && cases.length === 0 && (
              <div className="border border-gray-200 bg-white p-12 text-center dark:border-gray-800 dark:bg-gray-900">
                <Building2 className="mx-auto mb-4 h-10 w-10 text-gray-300 dark:text-gray-700" />
                <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">No accounts yet</h3>
                <p className="mb-6 text-xs text-gray-500 dark:text-gray-400">Open your first investment account to get started</p>
                <button
                  onClick={onOpenNewAccount}
                  className="inline-flex items-center gap-2 bg-primary px-5 py-2.5 text-xs font-semibold text-white transition-colors hover:bg-primary-hover"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Open New Account
                </button>
              </div>
            )}
          </>
        )}

        {/* Pending Documents tab */}
        {activeTab === 'documents' && (
          <div className="h-[calc(100dvh-260px)] min-h-[300px] overflow-hidden border border-gray-200 dark:border-gray-800">
            <PendingDocumentsGrid
              docs={pendingDocs}
              isLoading={docsLoading}
              onDocClick={setSelectedDoc}
            />
          </div>
        )}
      </div>

      {selectedDoc && (
        <ClientDocumentModal
          doc={selectedDoc}
          caseId={selectedDoc.case_id}
          onClose={() => setSelectedDoc(null)}
        />
      )}
    </div>
  )
}
