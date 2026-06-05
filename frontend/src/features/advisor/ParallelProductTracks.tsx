import { Package, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react'
import ProgressBar from '@/components/ProgressBar'
import type { ProductTrack } from '@/lib/api'

const PRODUCT_LABELS: Record<string, string> = {
  cash_account: 'Cash Account',
  retirement_account: 'Retirement Account',
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: 'text-gray-400',
  IN_PROGRESS: 'text-blue-600 dark:text-blue-400',
  COMPLETE: 'text-green-600 dark:text-green-400',
  FAILED: 'text-red-600 dark:text-red-400',
  ESCALATED: 'text-amber-600 dark:text-amber-400',
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
}

function ProductTrackCard({ track }: ProductTrackCardProps) {
  const label = PRODUCT_LABELS[track.product_code] ?? track.product_name ?? track.product_code
  const statusColor = STATUS_COLORS[track.status] ?? 'text-gray-500'

  return (
    <div className="flex flex-col gap-2 border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <StatusIndicator status={track.status} />
          <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">{label}</span>
        </div>
        <span className={['text-xs font-medium', statusColor].join(' ')}>{track.status}</span>
      </div>

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

      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>
          {track.steps_completed}/{track.steps_total} steps
        </span>
        <span className="tabular-nums font-semibold text-gray-700 dark:text-gray-200">{track.progress}%</span>
      </div>
    </div>
  )
}

interface ParallelProductTracksProps {
  tracks: ProductTrack[]
  isLoading?: boolean
}

export default function ParallelProductTracks({ tracks, isLoading }: ParallelProductTracksProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {[1, 2].map((i) => (
          <div key={i} className="h-28 animate-pulse bg-gray-200 dark:bg-gray-700" />
        ))}
      </div>
    )
  }

  if (!tracks || tracks.length === 0) {
    return (
      <div className="border border-dashed border-gray-200 py-6 text-center dark:border-gray-700">
        <Package className="mx-auto h-6 w-6 text-gray-300 dark:text-gray-600" />
        <p className="mt-2 text-xs text-gray-400">No products selected</p>
      </div>
    )
  }

  return (
    <div
      className={[
        'grid gap-4',
        tracks.length >= 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1',
      ].join(' ')}
    >
      {tracks.map((track) => (
        <ProductTrackCard key={track.product_code} track={track} />
      ))}
    </div>
  )
}
