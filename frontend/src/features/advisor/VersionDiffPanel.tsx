import { GitCompare, Loader2 } from 'lucide-react'
import type { DiffResult, DiffSection } from '@/lib/api'

const CHANGE_STYLES: Record<DiffSection['change_type'], { bg: string; text: string; label: string }> = {
  added: { bg: 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800', text: 'text-green-700 dark:text-green-300', label: 'Added' },
  modified: { bg: 'bg-amber-50 border-amber-200 dark:bg-amber-950 dark:border-amber-800', text: 'text-amber-700 dark:text-amber-300', label: 'Modified' },
  removed: { bg: 'bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800', text: 'text-red-700 dark:text-red-300', label: 'Removed' },
  unchanged: { bg: 'bg-gray-50 border-gray-200 dark:bg-gray-800 dark:border-gray-700', text: 'text-gray-500 dark:text-gray-400', label: 'Unchanged' },
}

interface VersionDiffPanelProps {
  diff: DiffResult | null | undefined
  isLoading?: boolean
}

function SimilarityRing({ ratio }: { ratio: number }) {
  const pct = Math.round(ratio * 100)
  const color =
    pct >= 80 ? 'text-green-600' : pct >= 50 ? 'text-amber-600' : 'text-red-600'

  return (
    <div className="flex items-center gap-2">
      <div className={['text-2xl font-bold tabular-nums', color].join(' ')}>{pct}%</div>
      <div className="text-xs text-gray-500 dark:text-gray-400">similarity with previous version</div>
    </div>
  )
}

export default function VersionDiffPanel({ diff, isLoading }: VersionDiffPanelProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <h4 className="flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-gray-100">
        <GitCompare className="h-4 w-4 text-gray-500 dark:text-gray-400" />
        Version Diff
      </h4>

      {!diff && (
        <div className="rounded-lg border border-dashed border-gray-200 py-8 text-center dark:border-gray-700">
          <p className="text-xs text-gray-400">No diff available.</p>
          <p className="mt-1 text-xs text-gray-400">Upload a new version to see changes.</p>
        </div>
      )}

      {diff && Object.keys(diff).length > 0 && (
        <>
          <SimilarityRing ratio={diff.similarity_ratio} />

          <p className="rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-700 dark:bg-blue-950 dark:text-blue-300">
            {diff.summary}
          </p>

          <div className="flex flex-col gap-2">
            {diff.sections
              .filter((s) => s.change_type !== 'unchanged')
              .map((s, i) => {
                const style = CHANGE_STYLES[s.change_type]
                return (
                  <div
                    key={i}
                    className={[
                      'rounded-lg border px-3 py-2',
                      style.bg,
                    ].join(' ')}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={[
                          'rounded px-1.5 py-0.5 text-[10px] font-semibold',
                          style.text,
                        ].join(' ')}
                      >
                        {style.label.toUpperCase()}
                      </span>
                      <span className="text-xs font-medium text-gray-700 dark:text-gray-200">{s.section}</span>
                    </div>

                    {s.change_type === 'modified' && (
                      <div className="mt-2 grid grid-cols-2 gap-2 text-[11px]">
                        <div>
                          <p className="mb-0.5 font-semibold text-gray-400">Before</p>
                          <p className="rounded bg-red-100 px-2 py-1 font-mono text-red-700 dark:bg-red-900 dark:text-red-300">
                            {s.old_value ?? '—'}
                          </p>
                        </div>
                        <div>
                          <p className="mb-0.5 font-semibold text-gray-400">After</p>
                          <p className="rounded bg-green-100 px-2 py-1 font-mono text-green-700 dark:bg-green-900 dark:text-green-300">
                            {s.new_value ?? '—'}
                          </p>
                        </div>
                      </div>
                    )}

                    {s.change_type === 'added' && s.new_value && (
                      <p className="mt-1 rounded bg-green-100 px-2 py-1 font-mono text-[11px] text-green-700 dark:bg-green-900 dark:text-green-300">
                        {s.new_value}
                      </p>
                    )}

                    {s.change_type === 'removed' && s.old_value && (
                      <p className="mt-1 rounded bg-red-100 px-2 py-1 font-mono text-[11px] text-red-700 line-through dark:bg-red-900 dark:text-red-300">
                        {s.old_value}
                      </p>
                    )}
                  </div>
                )
              })}
          </div>

          <p className="text-[10px] text-gray-400">
            Compared to version {diff.parent_id.slice(0, 8)}… ·{' '}
            {new Date(diff.computed_at).toLocaleString()}
          </p>
        </>
      )}
    </div>
  )
}
