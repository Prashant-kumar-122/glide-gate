import { useEffect, useRef, useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Wifi, WifiOff, Users, ChevronLeft } from 'lucide-react'
import { getSocket } from '@/lib/socket'
import { useCCStore } from '@/store/ccStore'
import { useAllCases, useClientDetail } from '@/hooks/useAllCases'
import { useCallSummary, ccQk } from '@/hooks/useCallSummary'
import { qk } from '@/hooks/useDocuments'
import ClientStatusTable from '@/features/contact-centre/ClientStatusTable'
import ClientDetailPanel from '@/features/contact-centre/ClientDetailPanel'

const CC_REFRESH_EVENTS = [
  'case_stage_changed',
  'kyc_result',
  'product_track_update',
  'progress_update',
  'escalation_triggered',
  'review_decided',
] as const

function useCCSocket(onRefresh: React.MutableRefObject<() => void>) {
  const setSocketStatus = useCCStore((s) => s.setSocketStatus)

  useEffect(() => {
    const socket = getSocket()

    function onConnect() { setSocketStatus('connected') }
    function onDisconnect() { setSocketStatus('disconnected') }
    const handler = () => onRefresh.current()

    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    if (socket.connected) setSocketStatus('connected')
    CC_REFRESH_EVENTS.forEach((ev) => socket.on(ev, handler))

    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      CC_REFRESH_EVENTS.forEach((ev) => socket.off(ev, handler))
    }
  }, [setSocketStatus, onRefresh])
}

export default function ContactCentre() {
  const qc = useQueryClient()
  const { selectedClientId, socketStatus } = useCCStore()
  const [mobileView, setMobileView] = useState<'list' | 'detail'>('list')

  const { data: cases = [], isLoading, isError } = useAllCases()
  const selectedCase = cases.find((c) => c.id === selectedClientId) ?? null
  const { data: summary, isLoading: summaryLoading } = useClientDetail(selectedCase?.id ?? null)
  const {
    data: callSummary,
    isLoading: callSummaryLoading,
    isError: callSummaryError,
    refetch: refetchCallSummary,
  } = useCallSummary(selectedCase?.id ?? null)

  const onRefreshRef = useRef<() => void>(() => {})
  onRefreshRef.current = useCallback(() => {
    qc.invalidateQueries({ queryKey: qk.cases })
    if (selectedCase?.id) {
      qc.invalidateQueries({ queryKey: qk.caseSummary(selectedCase.id) })
    }
  }, [qc, selectedCase?.id])

  useCCSocket(onRefreshRef)

  // Auto-switch to detail view on mobile when a client is selected
  useEffect(() => {
    if (selectedClientId) setMobileView('detail')
  }, [selectedClientId])

  return (
    <div className="flex h-[calc(100vh-49px)] flex-col overflow-hidden">
      {/* Top bar */}
      <div className="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4 py-3 sm:px-6">
        <div className="flex items-center gap-2">
          {/* Mobile back button — visible only in detail view */}
          {mobileView === 'detail' && (
            <button
              onClick={() => setMobileView('list')}
              className="mr-1 rounded-lg p-1.5 text-gray-500 transition-colors hover:bg-gray-100 md:hidden"
              aria-label="Back to client list"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          )}
          <Users className="h-4 w-4 text-gray-500" />
          <h1 className="text-sm font-semibold text-gray-800">Contact Centre</h1>
          {cases.length > 0 && (
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500">
              {cases.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          {socketStatus === 'connected' ? (
            <Wifi className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <WifiOff className="h-3.5 w-3.5 text-gray-400" />
          )}
          <span className="hidden sm:inline">{socketStatus === 'connected' ? 'Live' : 'Reconnecting…'}</span>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Client list:
            Mobile — full width, hidden when detail view is active
            md+    — fixed 320px sidebar, always visible */}
        <div
          className={[
            'shrink-0 flex-col border-r border-gray-200 bg-white',
            mobileView === 'list' ? 'flex w-full' : 'hidden',
            'md:flex md:w-80',
          ].join(' ')}
        >
          <ClientStatusTable cases={cases} isLoading={isLoading} isError={isError} />
        </div>

        {/* Client detail:
            Mobile — full width, hidden when list view is active
            md+    — flex-1, always visible */}
        <div
          className={[
            'flex-col overflow-hidden bg-gray-50',
            mobileView === 'detail' ? 'flex flex-1' : 'hidden',
            'md:flex md:flex-1',
          ].join(' ')}
        >
          <ClientDetailPanel
            summary={summary}
            summaryLoading={summaryLoading && !!selectedClientId}
            caseName={selectedCase?.case_name}
            callSummary={callSummary}
            callSummaryLoading={callSummaryLoading && !!selectedClientId}
            callSummaryError={callSummaryError}
            onRefreshCallSummary={() => {
              if (selectedCase?.id) {
                qc.invalidateQueries({ queryKey: ccQk.callSummary(selectedCase.id) })
                void refetchCallSummary()
              }
            }}
          />
        </div>
      </div>
    </div>
  )
}
