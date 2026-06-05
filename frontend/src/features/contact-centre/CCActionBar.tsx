import { Phone, Mail, ExternalLink, AlertTriangle, CheckCircle } from 'lucide-react'
import type { CaseSummary } from '@/lib/api'

interface Props {
  summary?: CaseSummary
  onEscalate?: () => void
  onResolve?: () => void
}

export default function CCActionBar({ summary, onEscalate, onResolve }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button className="flex items-center gap-1.5 border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700">
        <Phone className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
        Log Call
      </button>
      <button className="flex items-center gap-1.5 border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700">
        <Mail className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
        Send Email
      </button>
      <button className="flex items-center gap-1.5 border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700">
        <ExternalLink className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
        Open Case
      </button>
      {summary?.escalated ? (
        <button
          onClick={onResolve}
          className="flex items-center gap-1.5 border border-green-200 bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 transition-colors hover:bg-green-100 dark:border-green-800 dark:bg-green-950 dark:text-green-300 dark:hover:bg-green-900"
        >
          <CheckCircle className="h-3.5 w-3.5" />
          Mark Resolved
        </button>
      ) : (
        <button
          onClick={onEscalate}
          className="flex items-center gap-1.5 border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300 dark:hover:bg-amber-900"
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          Escalate
        </button>
      )}
    </div>
  )
}
