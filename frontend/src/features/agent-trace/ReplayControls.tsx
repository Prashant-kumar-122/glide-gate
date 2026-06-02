import { RotateCcw, Square } from 'lucide-react'
import { useTraceStore } from '@/store/traceStore'
import type { AgentTaskOut } from '@/lib/api'

const SPEED_OPTIONS = [
  { label: '0.25×', ms: 2400 },
  { label: '0.5×',  ms: 1200 },
  { label: '1×',    ms: 600  },
  { label: '2×',    ms: 300  },
] as const

interface ReplayControlsProps {
  activeCaseId: string | null
  tasks: AgentTaskOut[]
}

export function ReplayControls({ activeCaseId, tasks }: ReplayControlsProps) {
  const replayState    = useTraceStore((s) => s.replayState)
  const replayProgress = useTraceStore((s) => s.replayProgress)
  const replaySpeed    = useTraceStore((s) => s.replaySpeed)
  const startReplay    = useTraceStore((s) => s.startReplay)
  const stopReplay     = useTraceStore((s) => s.stopReplay)
  const setReplaySpeed = useTraceStore((s) => s.setReplaySpeed)

  const isPlaying = replayState === 'playing'
  const canReplay = !!activeCaseId && tasks.length > 0 && !isPlaying

  return (
    <div className="flex shrink-0 items-center gap-2 border-b border-gray-200 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-800">
      {/* Speed chips */}
      <div className="flex items-center gap-1">
        {SPEED_OPTIONS.map((opt) => (
          <button
            key={opt.label}
            onClick={() => setReplaySpeed(opt.ms)}
            disabled={isPlaying}
            className={[
              'rounded px-2 py-0.5 text-[11px] font-medium transition-colors',
              replaySpeed === opt.ms
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                : 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700',
              isPlaying ? 'cursor-not-allowed opacity-50' : '',
            ].join(' ')}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="h-4 w-px bg-gray-200 dark:bg-gray-600" />

      {/* Replay / Stop button */}
      {isPlaying ? (
        <button
          onClick={stopReplay}
          className="flex items-center gap-1.5 rounded-lg bg-red-100 px-3 py-1.5 text-[11px] font-medium text-red-700 transition-colors hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50"
        >
          <Square className="h-3 w-3 fill-current" />
          Stop
        </button>
      ) : (
        <button
          onClick={() => startReplay(tasks)}
          disabled={!canReplay}
          title={!activeCaseId ? 'Select a case to replay' : tasks.length === 0 ? 'No task history to replay' : undefined}
          className={[
            'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11px] font-medium transition-colors',
            canReplay
              ? 'bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-300 dark:hover:bg-blue-900/40'
              : 'cursor-not-allowed bg-gray-100 text-gray-400 dark:bg-gray-700 dark:text-gray-500',
          ].join(' ')}
        >
          <RotateCcw className="h-3 w-3" />
          Replay
        </button>
      )}

      {/* Slim progress bar — only visible while playing */}
      {isPlaying && (
        <div className="flex-1">
          <div className="h-1 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
            <div
              className="h-full rounded-full bg-blue-500 transition-all duration-100"
              style={{ width: `${replayProgress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
