import { Bot, RefreshCw } from 'lucide-react'
import type { CallSummary } from '@/lib/api'

interface Props {
  summary?: CallSummary
  isLoading?: boolean
  isError?: boolean
  onRefresh?: () => void
}

export default function CallSummaryCard({ summary, isLoading, isError, onRefresh }: Props) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-3 flex items-center gap-2">
          <div className="h-4 w-4 animate-pulse rounded-full bg-gray-200 dark:bg-gray-700" />
          <div className="h-3 w-24 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
        </div>
        <div className="space-y-2">
          {[90, 75, 60].map((w) => (
            <div key={w} className="h-2 animate-pulse rounded bg-gray-100 dark:bg-gray-700" style={{ width: `${w}%` }} />
          ))}
        </div>
      </div>
    )
  }

  if (isError || !summary) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 p-4 text-center dark:border-gray-700 dark:bg-gray-800">
        <Bot className="mx-auto h-6 w-6 text-gray-300 dark:text-gray-600" />
        <p className="mt-2 text-xs text-gray-400">AI call summary not yet available</p>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="mx-auto mt-2 flex items-center gap-1 text-xs text-blue-500 hover:text-blue-600"
          >
            <RefreshCw className="h-3 w-3" />
            Generate summary
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-purple-500" />
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-200">AI Call Summary</span>
        </div>
        {onRefresh && (
          <button onClick={onRefresh} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <p className="text-xs leading-relaxed text-gray-600 dark:text-gray-300">{summary.summary}</p>

      {summary.key_points.length > 0 && (
        <div className="mt-3">
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
            Key Points
          </p>
          <ul className="space-y-1">
            {summary.key_points.map((pt, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-gray-600 dark:text-gray-300">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-purple-400" />
                {pt}
              </li>
            ))}
          </ul>
        </div>
      )}

      {summary.recommended_actions.length > 0 && (
        <div className="mt-3">
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
            Recommended Actions
          </p>
          <ul className="space-y-1">
            {summary.recommended_actions.map((action, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs font-medium text-gray-700 dark:text-gray-200">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-3 text-[10px] text-gray-300 dark:text-gray-600">
        Generated {new Date(summary.generated_at).toLocaleString()}
      </p>
    </div>
  )
}
