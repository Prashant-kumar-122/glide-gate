import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Wifi, WifiOff, Users } from 'lucide-react'
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

  return (
    <div className="flex h-[calc(100vh-49px)] flex-col overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
        <div className="flex items-center gap-2">
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
          <span>{socketStatus === 'connected' ? 'Live' : 'Reconnecting…'}</span>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: searchable client list */}
        <div className="flex w-80 shrink-0 flex-col border-r border-gray-200 bg-white">
          <ClientStatusTable cases={cases} isLoading={isLoading} isError={isError} />
        </div>

        {/* Right: selected client detail */}
        <div className="flex flex-1 flex-col overflow-hidden bg-gray-50">
          <ClientDetailPanel
            summary={summary}
            summaryLoading={summaryLoading && !!selectedClientId}
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
