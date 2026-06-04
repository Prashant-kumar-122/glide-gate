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
  const [activeTab, setActiveTab] = useState<Tab>('pending')
  const [selectedDoc, setSelectedDoc] = useState<PendingDoc | null>(null)

  const inProgress = cases.filter((c) => c.current_stage !== 'COMPLETE')
  const completed   = cases.filter((c) => c.current_stage === 'COMPLETE')

  // Fetch documents for all cases to build the pending-documents tab
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
    const caseName = c?.case_name ?? c?.id ?? ''
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
      {/* ── Sticky header ── */}
      <div className="sticky top-0 z-10 border-b border-gray-200 bg-white px-6 pb-0 pt-5 dark:border-gray-700 dark:bg-gray-900">

        {/* Title row */}
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              Welcome, {firstName}
            </h1>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
              Overview of your accounts and applications
            </p>
          </div>
          <button
            onClick={onOpenNewAccount}
            className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Open New Account
          </button>
        </div>

        {/* Tab bar */}
        <div className="flex gap-1">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={[
                  'border-b-2 px-4 pb-3 pt-1 text-sm whitespace-nowrap transition-colors',
                  isActive
                    ? 'border-blue-500 font-bold text-gray-900 dark:text-white'
                    : 'border-transparent font-medium text-gray-400 hover:text-gray-600 dark:hover:text-gray-200',
                ].join(' ')}
              >
                {tab.label} ({padCount(tab.count)})
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Content area ── */}
      <div className="min-h-[calc(100vh-200px)] bg-gray-50 p-6 dark:bg-gray-950">

        {/* ── Pending Applications / Live Accounts tabs ── */}
        {activeTab !== 'documents' && (
          <>
            {isLoading && (
              <div className="flex justify-center py-16">
                <div className="h-7 w-7 animate-spin rounded-full border-2 border-gray-200 border-t-blue-500 dark:border-gray-700" />
              </div>
            )}

            {!isLoading && visibleCases.length > 0 && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {visibleCases.map((c) => (
                  <CaseCard key={c.id} caseData={c} onClick={() => onOpenCase(c)} />
                ))}
              </div>
            )}

            {!isLoading && visibleCases.length === 0 && cases.length > 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <Building2 className="mb-4 h-10 w-10 text-gray-200 dark:text-gray-700" />
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  {activeTab === 'pending' ? 'No pending applications' : 'No live accounts yet'}
                </p>
                {activeTab === 'pending' && (
                  <button
                    onClick={onOpenNewAccount}
                    className="mt-4 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700"
                  >
                    <Plus className="h-4 w-4" />
                    Open New Account
                  </button>
                )}
              </div>
            )}

            {!isLoading && cases.length === 0 && (
              <div className="rounded-2xl border border-gray-200 bg-white p-16 text-center dark:border-gray-700 dark:bg-gray-800">
                <Building2 className="mx-auto mb-4 h-12 w-12 text-gray-200 dark:text-gray-700" />
                <h3 className="mb-2 font-semibold text-gray-600 dark:text-gray-300">No accounts yet</h3>
                <p className="mb-6 text-sm text-gray-400">Open your first investment account to get started</p>
                <button
                  onClick={onOpenNewAccount}
                  className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-700"
                >
                  <Plus className="h-4 w-4" />
                  Open New Account
                </button>
              </div>
            )}
          </>
        )}

        {/* ── Pending Documents tab ── */}
        {activeTab === 'documents' && (
          <div className="h-[calc(100vh-260px)] overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700">
            <PendingDocumentsGrid
              docs={pendingDocs}
              isLoading={docsLoading}
              onDocClick={setSelectedDoc}
            />
          </div>
        )}
      </div>

      {/* ── Document modal ── */}
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
