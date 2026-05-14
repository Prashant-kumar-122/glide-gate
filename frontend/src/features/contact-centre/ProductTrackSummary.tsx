import { CheckCircle, AlertTriangle, Loader2, Package } from 'lucide-react'
import ProgressBar from '@/components/ProgressBar'
import type { ProductTrack } from '@/lib/api'

const PRODUCT_LABELS: Record<string, string> = {
  cash_account: 'Cash Account',
  retirement_account: 'Retirement Account',
}

function StatusDot({ status }: { status: string }) {
  if (status === 'COMPLETE') return <CheckCircle className="h-3.5 w-3.5 text-green-500" />
  if (status === 'ESCALATED') return <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
  if (status === 'IN_PROGRESS') return <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" />
  return <Package className="h-3.5 w-3.5 text-gray-400" />
}

export default function ProductTrackSummary({ tracks }: { tracks: ProductTrack[] }) {
  if (!tracks || tracks.length === 0) {
    return <p className="text-xs text-gray-400">No products selected</p>
  }

  return (
    <div className="space-y-2.5">
      {tracks.map((t) => (
        <div key={t.product_code} className="flex items-center gap-3">
          <StatusDot status={t.status} />
          <span className="w-36 shrink-0 truncate text-xs font-medium text-gray-700">
            {PRODUCT_LABELS[t.product_code] ?? t.product_name ?? t.product_code}
          </span>
          <div className="flex-1">
            <ProgressBar
              value={t.progress}
              size="sm"
              color={
                t.status === 'COMPLETE'
                  ? 'success'
                  : t.status === 'ESCALATED'
                  ? 'warning'
                  : t.status === 'FAILED'
                  ? 'danger'
                  : 'default'
              }
            />
          </div>
          <span className="w-8 shrink-0 text-right text-xs tabular-nums text-gray-500">
            {t.progress}%
          </span>
        </div>
      ))}
    </div>
  )
}
