import { ArrowRight } from 'lucide-react'
import { useTraceStore } from '@/store/traceStore'

const STATUS_COLORS: Record<string, string> = {
  SUCCESS: 'text-green-600 bg-green-50 dark:bg-green-950 dark:text-green-400',
  FAILED: 'text-red-600 bg-red-50 dark:bg-red-950 dark:text-red-400',
  ESCALATED: 'text-amber-600 bg-amber-50 dark:bg-amber-950 dark:text-amber-400',
  PARTIAL: 'text-amber-500 bg-amber-50 dark:bg-amber-950 dark:text-amber-400',
  IN_FLIGHT: 'text-blue-600 bg-blue-50 dark:bg-blue-950 dark:text-blue-400',
}

function fmtTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return ts
  }
}

export function MessageLog() {
  const messages = useTraceStore((s) => s.messageLog)
  const reversed = [...messages].reverse()

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-gray-100 px-4 py-2.5 dark:border-gray-700">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">
          A2A Message Log{messages.length > 0 ? ` (${messages.length})` : ''}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {reversed.length === 0 ? (
          <div className="flex h-full items-center justify-center px-6">
            <p className="text-center text-xs text-gray-300 dark:text-gray-600">
              No messages yet.
              <br />
              Select a case and start onboarding to see agent communication.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-50 dark:divide-gray-700">
            {reversed.map((msg) => (
              <li key={msg.id} className="px-4 py-2.5">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-semibold text-gray-700 dark:text-gray-200">{msg.fromAgent}</span>
                  <ArrowRight className="h-2.5 w-2.5 shrink-0 text-gray-400" />
                  <span className="text-[10px] font-semibold text-gray-700 dark:text-gray-200">{msg.toAgent}</span>
                  <span
                    className={[
                      'ml-auto shrink-0 rounded px-1 py-0.5 text-[9px] font-bold',
                      STATUS_COLORS[msg.status] ?? 'text-gray-500 bg-gray-100 dark:bg-gray-700 dark:text-gray-400',
                    ].join(' ')}
                  >
                    {msg.status}
                  </span>
                </div>
                <p className="mt-0.5 text-[10px] text-gray-500 dark:text-gray-400">{msg.taskType}</p>
                <p className="mt-0.5 text-[9px] text-gray-300 dark:text-gray-600">{fmtTime(msg.timestamp)}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
