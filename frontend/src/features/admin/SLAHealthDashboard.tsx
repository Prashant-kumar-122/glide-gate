import { Loader2, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import { useSLAHealth } from '@/hooks/useDomainAdmin'

interface Props {
  domainCode?: string
}

function ElapsedBar({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-[10px] text-gray-400">—</span>
  const clamped = Math.min(pct, 100)
  const color =
    pct >= 100 ? 'bg-red-500' :
    pct >= 80  ? 'bg-amber-400' :
                 'bg-emerald-400'

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-700">
        <div className={`h-full ${color}`} style={{ width: `${clamped}%` }} />
      </div>
      <span className={[
        'text-[10px] font-medium',
        pct >= 100 ? 'text-red-600 dark:text-red-400' :
        pct >= 80  ? 'text-amber-600 dark:text-amber-400' :
                     'text-gray-600 dark:text-gray-400',
      ].join(' ')}>
        {pct.toFixed(1)}%
      </span>
    </div>
  )
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

export default function SLAHealthDashboard({ domainCode = 'wealth_management' }: Props) {
  const { data: entries, isLoading, refetch } = useSLAHealth(domainCode)

  const active = entries ?? []
  const breached = active.filter((e) => e.pct_elapsed !== null && e.pct_elapsed >= (e.escalation_pct ?? 100))
  const warned = active.filter((e) => !e.breach_triggered && e.pct_elapsed !== null && e.pct_elapsed >= (e.warning_pct ?? 80))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">SLA Health Dashboard</h3>
          <p className="mt-0.5 text-xs text-gray-500">
            Active cases with SLA tracking. Refreshes every 30 seconds.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="border border-gray-200 px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          Refresh
        </button>
      </div>

      {/* Summary chips */}
      <div className="flex flex-wrap gap-3">
        <div className="flex items-center gap-1.5 border border-gray-200 px-3 py-2 dark:border-gray-700">
          <Clock className="h-4 w-4 text-gray-400" />
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{active.length} active</span>
        </div>
        <div className="flex items-center gap-1.5 border border-amber-200 bg-amber-50 px-3 py-2 dark:border-amber-800 dark:bg-amber-950">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <span className="text-xs font-medium text-amber-700 dark:text-amber-300">{warned.length} in warning</span>
        </div>
        <div className="flex items-center gap-1.5 border border-red-200 bg-red-50 px-3 py-2 dark:border-red-800 dark:bg-red-950">
          <AlertTriangle className="h-4 w-4 text-red-500" />
          <span className="text-xs font-medium text-red-700 dark:text-red-300">{breached.length} breached</span>
        </div>
      </div>

      <div className="overflow-hidden border border-gray-200 dark:border-gray-700">
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-xs text-gray-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : active.length === 0 ? (
          <div className="flex items-center justify-center gap-2 py-8 text-xs text-gray-400">
            <CheckCircle className="h-4 w-4 text-emerald-400" />
            No active SLA tracking rows.
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[640px] text-xs">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    {['Case ID', 'Stage', 'Elapsed', 'Window', '% Elapsed', 'Warning Sent', 'Breached'].map((h) => (
                      <th key={h} className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {active.map((e) => (
                    <tr
                      key={`${e.case_id}-${e.stage_code}`}
                      className={[
                        'hover:bg-gray-50 dark:hover:bg-gray-700',
                        e.breach_triggered ? 'bg-red-50 dark:bg-red-950/30' :
                        e.warning_sent ? 'bg-amber-50 dark:bg-amber-950/30' : '',
                      ].join(' ')}
                    >
                      <td className="px-4 py-2.5 font-mono text-[11px] text-gray-600 dark:text-gray-400">
                        {e.case_id.slice(0, 8)}…
                      </td>
                      <td className="px-4 py-2.5 font-mono font-medium text-gray-800 dark:text-gray-100">
                        {e.stage_code}
                      </td>
                      <td className="px-4 py-2.5 text-gray-600 dark:text-gray-400">
                        {formatElapsed(e.net_elapsed_seconds)}
                      </td>
                      <td className="px-4 py-2.5 text-gray-600 dark:text-gray-400">
                        {e.window_hours !== null ? `${e.window_hours}h` : '—'}
                      </td>
                      <td className="px-4 py-2.5">
                        <ElapsedBar pct={e.pct_elapsed} />
                      </td>
                      <td className="px-4 py-2.5">
                        {e.warning_sent ? (
                          <span className="text-[10px] text-amber-600 dark:text-amber-400">⚠ Sent</span>
                        ) : (
                          <span className="text-[10px] text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5">
                        {e.breach_triggered ? (
                          <span className="text-[10px] font-semibold text-red-600 dark:text-red-400">✕ Breached</span>
                        ) : (
                          <span className="text-[10px] text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="divide-y divide-gray-100 md:hidden dark:divide-gray-700">
              {active.map((e) => (
                <div key={`${e.case_id}-${e.stage_code}`} className="p-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-mono text-xs font-medium text-gray-800 dark:text-gray-100">{e.stage_code}</p>
                      <p className="text-[10px] text-gray-400">{e.case_id.slice(0, 8)}… · {formatElapsed(e.net_elapsed_seconds)}</p>
                    </div>
                    <div>
                      {e.breach_triggered && <span className="text-[10px] font-semibold text-red-600">Breached</span>}
                      {!e.breach_triggered && e.warning_sent && <span className="text-[10px] text-amber-600">Warning</span>}
                    </div>
                  </div>
                  <div className="mt-2">
                    <ElapsedBar pct={e.pct_elapsed} />
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
