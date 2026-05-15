import { useEffect, useState } from 'react'
import { ChevronDown, Plus } from 'lucide-react'
import ConversationalChat from '@/features/client/ConversationalChat'
import ClientDocumentHub from '@/features/client/ClientDocumentHub'
import ClientProgressBar from '@/features/client/ClientProgressBar'
import CreateCaseModal from '@/features/client/CreateCaseModal'
import { useCases, useCaseProgress } from '@/hooks/useDocuments'
import { useWorkspaceSocket } from '@/hooks/useWorkspaceSocket'
import { useChatStore } from '@/store/chatStore'
import { useChatHistory } from '@/hooks/useClientChat'

export default function ClientPortal() {
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)

  const { data: cases, isLoading: casesLoading } = useCases()
  const { data: summary, isLoading: summaryLoading } = useCaseProgress(activeCaseId)
  const { data: history } = useChatHistory(activeCaseId)

  const clearMessages = useChatStore((s) => s.clearMessages)
  const addMessage = useChatStore((s) => s.addMessage)
  const setSessionId = useChatStore((s) => s.setSessionId)

  // Auto-select first case on load
  useEffect(() => {
    if (!activeCaseId && cases && cases.length > 0) {
      setActiveCaseId(cases[0].id)
      setSessionId(cases[0].id)
    }
  }, [cases, activeCaseId, setSessionId])

  // Hydrate chat store from server history whenever the active case changes
  useEffect(() => {
    if (!history) return
    clearMessages()
    for (const m of history) {
      addMessage({
        id: m.id,
        role: m.role === 'system' ? 'assistant' : m.role,
        content: m.content,
        timestamp: m.created_at,
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [history])

  // Real-time socket updates (document status changes, progress, etc.)
  useWorkspaceSocket(activeCaseId)

  function caseLabel(c: { case_name?: string; selected_products: string[] }, index: number) {
    if (c.case_name) return c.case_name
    if (c.selected_products.length > 0)
      return c.selected_products
        .map((p) => p.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()))
        .join(' & ')
    return `Case ${index + 1}`
  }

  function switchCase(caseId: string) {
    if (caseId === activeCaseId) return
    clearMessages()
    setActiveCaseId(caseId)
    setSessionId(caseId)
  }

  return (
    <div className="flex h-[calc(100vh-49px)] flex-col">
      {/* Top bar: case selector + new case button — shown whenever cases exist */}
      {!casesLoading && cases && cases.length > 0 && (
        <div className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-2">
          <div className="flex items-center gap-3">
            {cases.length > 1 && (
              <>
                <span className="text-xs font-medium text-gray-500">Active case:</span>
                <div className="relative">
                  <select
                    value={activeCaseId ?? ''}
                    onChange={(e) => switchCase(e.target.value)}
                    className="appearance-none rounded-lg border border-gray-300 bg-white py-1.5 pl-3 pr-8 text-sm text-gray-900 focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
                  >
                    {cases.map((c, i) => (
                      <option key={c.id} value={c.id}>
                        {caseLabel(c, i)} — {c.current_stage}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                </div>
              </>
            )}
            {cases.length === 1 && (
              <span className="text-xs text-gray-500">
                {caseLabel(cases[0], 0)} — {cases[0].current_stage}
              </span>
            )}
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100"
          >
            <Plus className="h-3.5 w-3.5" />
            New case
          </button>
        </div>
      )}

      {/* Loading */}
      {casesLoading && (
        <div className="flex flex-1 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-blue-500" />
        </div>
      )}

      {/* Empty state — prompt client to create their first case */}
      {!casesLoading && (!cases || cases.length === 0) && (
        <div className="flex flex-1 items-center justify-center">
          <div className="rounded-2xl border border-gray-200 bg-white p-10 text-center shadow-sm">
            <p className="text-base font-medium text-gray-700">Welcome to GlideGate</p>
            <p className="mt-1 text-sm text-gray-400">Let's start your onboarding journey.</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-4 rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700"
            >
              Create my first case
            </button>
          </div>
        </div>
      )}

      {/* Modal — shared by empty state and existing-cases "New case" button */}
      {showCreateModal && (
        <CreateCaseModal onCreated={() => setShowCreateModal(false)} />
      )}

      {/* Main portal — side-by-side layout */}
      {!casesLoading && activeCaseId && (
        <div className="flex flex-1 overflow-hidden">
          {/* Left: progress + chat */}
          <div className="flex w-[440px] shrink-0 flex-col border-r border-gray-200 bg-white">
            <div className="border-b border-gray-100 px-4 py-3">
              <ClientProgressBar summary={summary} isLoading={summaryLoading} />
            </div>
            <div className="flex-1 overflow-hidden">
              <ConversationalChat caseId={activeCaseId} />
            </div>
          </div>

          {/* Right: documents */}
          <div className="flex flex-1 flex-col overflow-hidden bg-gray-50">
            <div className="border-b border-gray-200 bg-white px-6 py-3">
              <h2 className="text-sm font-semibold text-gray-900">My Documents</h2>
              <p className="mt-0.5 text-xs text-gray-400">
                Upload and track your onboarding documents
              </p>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <ClientDocumentHub caseId={activeCaseId} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
