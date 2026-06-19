import { useEffect, useRef, useState } from 'react'
import { Package, CheckCircle, AlertTriangle, Loader2, Zap } from 'lucide-react'
import ProgressBar from '@/components/ProgressBar'
import type { ProductTrack } from '@/lib/api'


const STATUS_COLORS: Record<string, string> = {
  PENDING: 'text-gray-400',
  IN_PROGRESS: 'text-blue-600 dark:text-blue-400',
  COMPLETE: 'text-green-600 dark:text-green-400',
  FAILED: 'text-red-600 dark:text-red-400',
  ESCALATED: 'text-amber-600 dark:text-amber-400',
}

const ACTIVATION_BADGE: Record<
  string,
  { label: string; className: string }
> = {
  ACTIVATED: {
    label: 'Activated',
    className:
      'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  },
  CRITERIA_MET: {
    label: 'Criteria Met',
    className:
      'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  },
  DECLINED: {
    label: 'Declined',
    className:
      'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  },
  PENDING: {
    label: 'Pending',
    className:
      'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
  },
}

function StatusIndicator({ status }: { status: string }) {
  if (status === 'COMPLETE')
    return <CheckCircle className="h-4 w-4 text-green-500" />
  if (status === 'ESCALATED')
    return <AlertTriangle className="h-4 w-4 text-amber-500" />
  if (status === 'IN_PROGRESS')
    return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
  return <Package className="h-4 w-4 text-gray-400" />
}

interface ProductTrackCardProps {
  track: ProductTrack
  isFirstActivated: boolean
}

function ProductTrackCard({ track, isFirstActivated }: ProductTrackCardProps) {
  const label = (track.product_name ?? track.product_code).replace(/_/g, ' ')
  const statusColor = STATUS_COLORS[track.status] ?? 'text-gray-500'
  const activationState = track.activation_state ?? 'PENDING'
  const badge = ACTIVATION_BADGE[activationState] ?? ACTIVATION_BADGE.PENDING

  return (
    <div
      className={[
        'flex flex-col gap-2 border bg-white p-4 dark:bg-gray-800',
        isFirstActivated
          ? 'border-green-400 dark:border-green-600 ring-1 ring-green-400 dark:ring-green-600'
          : 'border-gray-200 dark:border-gray-700',
      ].join(' ')}
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <StatusIndicator status={track.status} />
          <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">
            {label}
          </span>
          {isFirstActivated && (
            <span className="flex items-center gap-0.5 rounded bg-green-500 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
              <Zap className="h-2.5 w-2.5" />
              First Live
            </span>
          )}
        </div>
        <span className={['text-xs font-medium', statusColor].join(' ')}>
          {track.status}
        </span>
      </div>

      {/* Progress bar */}
      <ProgressBar
        value={track.progress}
        size="md"
        color={
          track.status === 'COMPLETE'
            ? 'success'
            : track.status === 'ESCALATED'
            ? 'warning'
            : track.status === 'FAILED'
            ? 'danger'
            : 'default'
        }
      />

      {/* Steps / progress */}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>
          {track.steps_completed}/{track.steps_total} steps
        </span>
        <span className="tabular-nums font-semibold text-gray-700 dark:text-gray-200">
          {track.progress}%
        </span>
      </div>

      {/* Activation badge row */}
      <div className="flex items-center justify-between gap-2 pt-0.5">
        <span
          className={[
            'inline-block rounded px-2 py-0.5 text-[11px] font-semibold',
            badge.className,
          ].join(' ')}
        >
          {badge.label}
        </span>
        {track.account_number && activationState === 'ACTIVATED' && (
          <span className="font-mono text-[11px] text-gray-500 dark:text-gray-400 truncate max-w-[140px]">
            {track.account_number}
          </span>
        )}
      </div>
    </div>
  )
}

// ── SSE activation state overlay ──────────────────────────────────────────────

interface ActivationEntry {
  state: string
  account_number: string | null
}

function useProductActivationSSE(caseId: string | undefined) {
  const [overrides, setOverrides] = useState<Record<string, ActivationEntry>>({})
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!caseId) return
    const es = new EventSource(`/api/cases/${caseId}/events`, { withCredentials: true })
    esRef.current = es

    es.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as {
          type: string
          activations: Record<string, ActivationEntry>
        }
        if (msg.type === 'activation_update') {
          setOverrides(msg.activations)
        }
      } catch {
        // malformed SSE payload — ignore
      }
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [caseId])

  return overrides
}

// ── Component ─────────────────────────────────────────────────────────────────

interface ParallelProductTracksProps {
  tracks: ProductTrack[]
  isLoading?: boolean
  caseId?: string
}

export default function ParallelProductTracks({ tracks, isLoading, caseId }: ParallelProductTracksProps) {
  const sseActivations = useProductActivationSSE(caseId)

  // Merge SSE overrides into tracks: SSE is authoritative for activation_state
  // and account_number; other track fields come from the polled REST response.
  const mergedTracks = tracks.map((t) => {
    const sse = sseActivations[t.product_code]
    if (!sse) return t
    return {
      ...t,
      activation_state: sse.state as ProductTrack['activation_state'],
      account_number:   sse.account_number,
    }
  })
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {[1, 2].map((i) => (
          <div key={i} className="h-32 animate-pulse bg-gray-200 dark:bg-gray-700" />
        ))}
      </div>
    )
  }

  if (!mergedTracks || mergedTracks.length === 0) {
    return (
      <div className="border border-dashed border-gray-200 py-6 text-center dark:border-gray-700">
        <Package className="mx-auto h-6 w-6 text-gray-300 dark:text-gray-600" />
        <p className="mt-2 text-xs text-gray-400">No products selected</p>
      </div>
    )
  }

  // The first product that reached ACTIVATED is highlighted
  const firstActivatedCode = mergedTracks.find(
    (t) => t.activation_state === 'ACTIVATED'
  )?.product_code

  return (
    <div
      className={[
        'grid gap-4',
        mergedTracks.length >= 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1',
      ].join(' ')}
    >
      {mergedTracks.map((track) => (
        <ProductTrackCard
          key={track.product_code}
          track={track}
          isFirstActivated={track.product_code === firstActivatedCode}
        />
      ))}
    </div>
  )
}
