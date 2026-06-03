import { useRef, useEffect, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Wifi, WifiOff, Users, X } from 'lucide-react'
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
  const { selectedClientId, socketStatus, openTabs, activeTabId, closeClientTab, setActiveTab } = useCCStore()
  const scrollRef = useRef<HTMLDivElement>(null)
  const activeTabRef = useRef<HTMLDivElement>(null)

  const { data: cases = [] } = useAllCases()
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

  useEffect(() => {
    activeTabRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
  }, [activeTabId])

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col overflow-hidden bg-gray-900">
      {/* Tab bar */}
      <div className="flex shrink-0 items-end border-b border-gray-700 bg-gray-900">
        {/* Clients — always visible, never scrolls away */}
        <div className="shrink-0 px-2">
          <button
            onClick={() => setActiveTab('clients')}
            className={[
              'flex items-center gap-2 border-b-2 px-4 pb-3 pt-3 text-sm font-medium transition-colors whitespace-nowrap',
              activeTabId === 'clients'
                ? 'border-blue-500 text-white'
                : 'border-transparent text-gray-400 hover:text-gray-200',
            ].join(' ')}
          >
            <Users className="h-3.5 w-3.5" />
            Clients
          </button>
        </div>

        {/* Scrollable client tabs */}
        <div
          ref={scrollRef}
          className="flex min-w-0 flex-1 items-end overflow-x-auto [&::-webkit-scrollbar]:h-[3px] [&::-webkit-scrollbar-track]:bg-gray-900 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-600"
        >
          {openTabs.map((tab) => {
            const isActive = activeTabId === tab.clientId
            return (
              <div
                key={tab.clientId}
                ref={isActive ? activeTabRef : undefined}
                onClick={() => setActiveTab(tab.clientId)}
                className={[
                  'group flex shrink-0 cursor-pointer items-center gap-1.5 border-b-2 px-4 pb-3 pt-3 text-sm transition-colors whitespace-nowrap',
                  isActive
                    ? 'border-blue-500 text-white'
                    : 'border-transparent text-gray-400 hover:text-gray-200',
                ].join(' ')}
              >
                <span className="font-medium">{tab.label}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    closeClientTab(tab.clientId)
                  }}
                  className="rounded p-0.5 text-gray-500 transition-colors hover:bg-gray-700 hover:text-gray-200"
                  aria-label="Close tab"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            )
          })}
        </div>

        {/* Socket status */}
        <div className="shrink-0 flex items-center gap-1.5 px-4 pb-3 pt-3 text-xs text-gray-400">
          {socketStatus === 'connected' ? (
            <Wifi className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <WifiOff className="h-3.5 w-3.5 text-gray-500" />
          )}
          <span className="hidden sm:inline">{socketStatus === 'connected' ? 'Live' : 'Reconnecting…'}</span>
        </div>
      </div>

      {/* Content */}
      {activeTabId === 'clients' ? (
        <ClientStatusTable />
      ) : (
        <div className="flex-1 overflow-y-auto">
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
      )}
    </div>
  )
}
