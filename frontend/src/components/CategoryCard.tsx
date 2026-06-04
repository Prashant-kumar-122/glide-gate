import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import ProgressBar from './ProgressBar'
import type { ReactNode } from 'react'

export interface CategoryCardProps {
  title: string
  icon?: ReactNode
  totalDocs: number
  approvedDocs: number
  children?: ReactNode
  defaultOpen?: boolean
  badge?: ReactNode
}

export default function CategoryCard({
  title,
  icon,
  totalDocs,
  approvedDocs,
  children,
  defaultOpen = false,
  badge,
}: CategoryCardProps) {
  const [open, setOpen] = useState(defaultOpen)
  const pct = totalDocs === 0 ? 0 : Math.round((approvedDocs / totalDocs) * 100)

  return (
    <div className="border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
      >
        {icon && (
          <span className="text-gray-400 dark:text-gray-500 shrink-0">{icon}</span>
        )}

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-gray-800 dark:text-gray-200">{title}</span>
            {badge}
          </div>
          <div className="mt-1.5">
            <ProgressBar value={pct} size="sm" />
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <span className="font-mono text-[10px] tabular-nums text-gray-400 dark:text-gray-500">
            {approvedDocs}/{totalDocs}
          </span>
          {open
            ? <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
            : <ChevronRight className="h-3.5 w-3.5 text-gray-400" />
          }
        </div>
      </button>

      {open && children && (
        <div className="border-t border-gray-100 px-2 py-2 space-y-px dark:border-gray-800">
          {children}
        </div>
      )}
    </div>
  )
}
