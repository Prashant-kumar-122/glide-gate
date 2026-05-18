import { useEffect, useRef, useState, useCallback } from 'react'
import { ChevronDown, Plus } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import ConversationalChat from '@/features/client/ConversationalChat'
import ClientDocumentHub from '@/features/client/ClientDocumentHub'
import ClientProgressBar from '@/features/client/ClientProgressBar'
import OnboardingFormView from '@/features/client/OnboardingFormView'
import CreateCaseModal from '@/features/client/CreateCaseModal'
import { useCases, useCaseProgress, useCollectedFields, useQuestionnaireSchema } from '@/hooks/useDocuments'
import { useWorkspaceSocket } from '@/hooks/useWorkspaceSocket'
import { useChatStore } from '@/store/chatStore'
import { useChatHistory, useGreeting } from '@/hooks/useClientChat'

const MIN_COL = 240
const MAX_COL = 700

function ResizeDivider({ onMouseDown }: { onMouseDown: (e: React.MouseEvent) => void }) {
  return (
    <div
      onMouseDown={onMouseDown}
      className="group relative z-10 flex w-[5px] shrink-0 cursor-col-resize items-center justify-center bg-transparent select-none"
    >
      {/* visible line */}
      <div className="absolute inset-y-0 left-[2px] w-px bg-gray-200 group-hover:bg-blue-400 group-active:bg-blue-500 transition-colors" />
      {/* grip dots */}
      <div className="relative flex flex-col gap-[3px] opacity-0 group-hover:opacity-100 transition-opacity">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="h-1 w-1 rounded-full bg-blue-400" />
        ))}
      </div>
    </div>
  )
}

export default function ClientPortal() {
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)

  // ── Column resize ─────────────────────────────────────────────────────────
  const [leftWidth, setLeftWidth] = useState(380)
  const [centerWidth, setCenterWidth] = useState(360)
  const resizing = useRef<'left' | 'center' | null>(null)
  const startX = useRef(0)
  const startWidth = useRef(0)

  const startResize = useCallback(
    (which: 'left' | 'center') => (e: React.MouseEvent) => {
      e.preventDefault()
      resizing.current = which
      startX.current = e.clientX
      startWidth.current = which === 'left' ? leftWidth : centerWidth
    },
    [leftWidth, centerWidth],
  )

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!resizing.current) return
      const delta = e.clientX - startX.current
      const next = Math.max(MIN_COL, Math.min(MAX_COL, startWidth.current + delta))
      if (resizing.current === 'left') setLeftWidth(next)
      else setCenterWidth(next)
    }
    function onUp() { resizing.current = null }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    return () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
  }, [])

  const queryClient = useQueryClient()
  const { data: cases, isLoading: casesLoading } = useCases()
  const { data: summary, isLoading: summaryLoading } = useCaseProgress(activeCaseId)
  const { data: history } = useChatHistory(activeCaseId)
  const { data: collectedData, isLoading: collectedLoading } = useCollectedFields(activeCaseId)
  const { data: schemaData } = useQuestionnaireSchema(activeCaseId)

  // Invalidate collected fields immediately when questionnaire progress changes
  const questionnairePct = useChatStore((s) => s.questionnairePct)
  useEffect(() => {
    if (activeCaseId) {
      queryClient.invalidateQueries({ queryKey: ['cases', activeCaseId, 'collected-fields'] })
    }
  }, [questionnairePct, activeCaseId, queryClient])

  const clearMessages = useChatStore((s) => s.clearMessages)
  const addMessage = useChatStore((s) => s.addMessage)
  const setSessionId = useChatStore((s) => s.setSessionId)

  const greeting = useGreeting(activeCaseId)
  // Track which cases have already received their greeting so we never fire twice
  const greetedCases = useRef<Set<string>>(new Set())

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
    // If this is a fresh conversation, trigger the assistant's opening greeting
    if (history.length === 0 && activeCaseId && !greetedCases.current.has(activeCaseId)) {
      greetedCases.current.add(activeCaseId)
      greeting.mutate({ onChunk: undefined, onDone: undefined })
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
        <CreateCaseModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(newCaseId) => {
            setShowCreateModal(false)
            switchCase(newCaseId)
          }}
        />
      )}

      {/* Main portal — three-panel resizable layout */}
      {!casesLoading && activeCaseId && (
        <div className="flex flex-1 overflow-hidden">
          {/* Left: progress + chat */}
          <div
            className="flex shrink-0 flex-col bg-white"
            style={{ width: leftWidth }}
          >
            <div className="border-b border-gray-100 px-4 py-3">
              <ClientProgressBar summary={summary} isLoading={summaryLoading} />
            </div>
            <div className="flex-1 overflow-hidden">
              <ConversationalChat caseId={activeCaseId} />
            </div>
          </div>

          <ResizeDivider onMouseDown={startResize('left')} />

          {/* Center: collected answers form (readonly) */}
          <div
            className="flex shrink-0 flex-col bg-white"
            style={{ width: centerWidth }}
          >
            <div className="shrink-0 border-b border-gray-200 px-4 py-3">
              <h2 className="text-sm font-semibold text-gray-900">Onboarding Details</h2>
              <p className="mt-0.5 text-xs text-gray-400">
                Answers collected from your conversation
              </p>
            </div>
            <div className="flex-1 overflow-hidden">
              <OnboardingFormView
                clientData={collectedData?.client_data ?? {}}
                schema={schemaData?.fields ?? []}
                isLoading={collectedLoading}
              />
            </div>
          </div>

          <ResizeDivider onMouseDown={startResize('center')} />

          {/* Right: documents */}
          <div className="flex flex-1 flex-col overflow-hidden bg-gray-50">
            <div className="shrink-0 border-b border-gray-200 bg-white px-6 py-3">
              <h2 className="text-sm font-semibold text-gray-900">My Documents</h2>
              <p className="mt-0.5 text-xs text-gray-400">
                Upload and track your onboarding documents
              </p>
            </div>
            <div className="flex-1 overflow-y-auto p-5">
              <ClientDocumentHub caseId={activeCaseId} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
