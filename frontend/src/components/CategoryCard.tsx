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
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
      >
        {icon && <span className="text-gray-500">{icon}</span>}

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-800">{title}</span>
            {badge}
          </div>
          <div className="mt-1.5">
            <ProgressBar value={pct} size="sm" />
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <span className="text-xs tabular-nums text-gray-500">
            {approvedDocs}/{totalDocs}
          </span>
          {open ? (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </button>

      {open && children && (
        <div className="border-t border-gray-100 px-2 py-2 space-y-1">
          {children}
        </div>
      )}
    </div>
  )
}
