import { CheckCircle, AlertTriangle, XCircle, Loader2, RefreshCw } from 'lucide-react'
import type { ValidationResult, FindingResult } from '@/lib/api'

interface VerdictIconProps {
  verdict: FindingResult['severity']
  size?: 'sm' | 'md'
}

function VerdictIcon({ verdict, size = 'sm' }: VerdictIconProps) {
  const cls = size === 'sm' ? 'h-4 w-4' : 'h-5 w-5'
  if (verdict === 'pass') return <CheckCircle className={`${cls} text-green-500`} />
  if (verdict === 'warn') return <AlertTriangle className={`${cls} text-amber-500`} />
  return <XCircle className={`${cls} text-red-500`} />
}

const VERDICT_BG: Record<FindingResult['severity'], string> = {
  pass: 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800',
  warn: 'bg-amber-50 border-amber-200 dark:bg-amber-950 dark:border-amber-800',
  fail: 'bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800',
}

const VERDICT_TEXT: Record<FindingResult['severity'], string> = {
  pass: 'text-green-700 dark:text-green-300',
  warn: 'text-amber-700 dark:text-amber-300',
  fail: 'text-red-700 dark:text-red-300',
}

const OVERALL_BADGE: Record<FindingResult['severity'], string> = {
  pass: 'bg-green-100 text-green-800 ring-green-300 dark:bg-green-900 dark:text-green-200 dark:ring-green-700',
  warn: 'bg-amber-100 text-amber-800 ring-amber-300 dark:bg-amber-900 dark:text-amber-200 dark:ring-amber-700',
  fail: 'bg-red-100 text-red-800 ring-red-300 dark:bg-red-900 dark:text-red-200 dark:ring-red-700',
}

interface AIValidationPanelProps {
  result: ValidationResult | null | undefined
  isLoading?: boolean
  onRunValidation?: () => void
  isRunning?: boolean
}

export default function AIValidationPanel({
  result,
  isLoading,
  onRunValidation,
  isRunning,
}: AIValidationPanelProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-100">Document Validation</h4>
        {onRunValidation && (
          <button
            onClick={onRunValidation}
            disabled={isRunning}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            {isRunning ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <RefreshCw className="h-3 w-3" />
            )}
            {isRunning ? 'Running…' : 'Run AI Check'}
          </button>
        )}
      </div>

      {!result && !isRunning && (
        <div className="rounded-lg border border-dashed border-gray-200 py-8 text-center dark:border-gray-700">
          <p className="text-xs text-gray-400">No validation result yet.</p>
          {onRunValidation && (
            <p className="mt-1 text-xs text-gray-400">Click "Run AI Check" to start.</p>
          )}
        </div>
      )}

      {isRunning && !result && (
        <div className="flex flex-col items-center gap-2 py-8">
          <Loader2 className="h-6 w-6 animate-spin text-indigo-500" />
          <p className="text-xs text-gray-500 dark:text-gray-400">AI is reviewing the document…</p>
        </div>
      )}

      {result && Object.keys(result).length > 0 && (
        <>
          {/* Overall verdict */}
          <div className="flex items-center gap-2">
            <span
              className={[
                'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset',
                OVERALL_BADGE[result.overall_status],
              ].join(' ')}
            >
              <VerdictIcon verdict={result.overall_status} />
              {result.overall_status === 'pass'
                ? 'All checks passed'
                : result.overall_status === 'warn'
                ? 'Warnings found'
                : 'Issues found'}
            </span>
            <span className="ml-auto text-[10px] text-gray-400">
              {new Date(result.validated_at).toLocaleString()}
            </span>
          </div>

          {/* Findings list */}
          <div className="flex flex-col gap-2">
            {result.findings.map((f, i) => (
              <div
                key={i}
                className={[
                  'flex items-start gap-2.5 rounded-lg border px-3 py-2',
                  VERDICT_BG[f.severity],
                ].join(' ')}
              >
                <VerdictIcon verdict={f.severity} />
                <div className="min-w-0 flex-1">
                  <p className={['text-xs font-semibold', VERDICT_TEXT[f.severity]].join(' ')}>
                    {f.field}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-600 dark:text-gray-300">{f.message}</p>
                  {f.confidence !== undefined && (
                    <p className="mt-0.5 text-[10px] text-gray-400">
                      Confidence: {Math.round(f.confidence * 100)}%
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {result.prompt_version && (
            <p className="text-[10px] text-gray-400">Prompt version: {result.prompt_version}</p>
          )}
        </>
      )}
    </div>
  )
}
