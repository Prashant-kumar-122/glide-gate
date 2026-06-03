import { useState, useMemo, useRef, useEffect } from 'react'
import { Search, Eye, X, ChevronDown, Check } from 'lucide-react'
import { useCases } from '@/hooks/useDocuments'
import type { CaseOut } from '@/lib/api'
import { useWorkspaceStore } from '@/store/workspaceStore'

const STAGE_LABELS: Record<string, string> = {
  INTAKE: 'Intake',
  KYC: 'KYC',
  PARALLEL_PRODUCTS: 'Products',
  REVIEW: 'Sales Review',
  COMPLETE: 'Live',
  ESCALATED: 'Escalated',
}

const STAGE_STYLES: Record<string, { badge: string; dot: string; optionDot: string }> = {
  INTAKE:            { badge: 'border border-gray-500/60 text-gray-400',    dot: 'bg-gray-400',    optionDot: 'bg-gray-400' },
  KYC:               { badge: 'border border-blue-500/60 text-blue-400',    dot: 'bg-blue-400',    optionDot: 'bg-blue-400' },
  PARALLEL_PRODUCTS: { badge: 'border border-purple-500/60 text-purple-400', dot: 'bg-purple-400', optionDot: 'bg-purple-400' },
  REVIEW:            { badge: 'border border-cyan-500/60 text-cyan-400',    dot: 'bg-cyan-400',    optionDot: 'bg-cyan-400' },
  COMPLETE:          { badge: 'border border-teal-500/60 text-teal-400',    dot: 'bg-teal-400',    optionDot: 'bg-teal-400' },
  ESCALATED:         { badge: 'border border-red-500/60 text-red-400',      dot: 'bg-red-400',     optionDot: 'bg-red-400' },
}

const ALL_STAGES = ['INTAKE', 'KYC', 'PARALLEL_PRODUCTS', 'REVIEW', 'COMPLETE', 'ESCALATED']

interface StageDropdownProps {
  value: string
  onChange: (v: string) => void
}

function StageDropdown({ value, onChange }: StageDropdownProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const selectedLabel = value ? STAGE_LABELS[value] : 'All Stages'
  const selectedDot = value ? STAGE_STYLES[value]?.dot : null

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={[
          'flex min-w-[140px] items-center justify-between gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors',
          open
            ? 'border-blue-500 bg-gray-800 text-white'
            : 'border-gray-600 bg-gray-800 text-gray-300 hover:border-gray-500',
        ].join(' ')}
      >
        <span className="flex items-center gap-2">
          {selectedDot && (
            <span className={['h-2 w-2 rounded-full', selectedDot].join(' ')} />
          )}
          {selectedLabel}
        </span>
        <ChevronDown
          className={['h-3.5 w-3.5 text-gray-400 transition-transform', open ? 'rotate-180' : ''].join(' ')}
        />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 min-w-[160px] overflow-hidden rounded-md border border-gray-600 bg-gray-800 shadow-xl">
          {/* All Stages option */}
          <button
            onClick={() => { onChange(''); setOpen(false) }}
            className={[
              'flex w-full items-center justify-between px-3 py-2 text-sm transition-colors',
              !value
                ? 'bg-blue-600/30 text-white'
                : 'text-gray-300 hover:bg-gray-700',
            ].join(' ')}
          >
            <span className="flex items-center gap-2.5">
              <span className="h-2 w-2 rounded-full bg-gray-500/0" />
              All Stages
            </span>
            {!value && <Check className="h-3.5 w-3.5 text-blue-400" />}
          </button>

          <div className="mx-2 border-t border-gray-700/60" />

          {ALL_STAGES.map((s) => {
            const style = STAGE_STYLES[s]
            const active = value === s
            return (
              <button
                key={s}
                onClick={() => { onChange(s); setOpen(false) }}
                className={[
                  'flex w-full items-center justify-between px-3 py-2 text-sm transition-colors',
                  active ? 'bg-blue-600/30 text-white' : 'text-gray-300 hover:bg-gray-700',
                ].join(' ')}
              >
                <span className="flex items-center gap-2.5">
                  <span className={['h-2 w-2 rounded-full', style.optionDot].join(' ')} />
                  {STAGE_LABELS[s]}
                </span>
                {active && <Check className="h-3.5 w-3.5 text-blue-400" />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

function productLabel(p: string): string {
  return p.replace(/_/g, ' ').toUpperCase()
}

function caseName(c: CaseOut): string {
  if (c.case_name) return c.case_name
  if (c.selected_products.length > 0)
    return c.selected_products
      .map((p) => p.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()))
      .join(' & ')
  return c.id
}

function relativeTime(dateStr: string): string {
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const days = Math.floor(diffMs / 86_400_000)
  if (days > 0) return `${days}d ago`
  const hours = Math.floor(diffMs / 3_600_000)
  if (hours > 0) return `${hours}h ago`
  const mins = Math.floor(diffMs / 60_000)
  return `${mins}m ago`
}

export default function CaseListTable() {
  const { data: cases, isLoading, isError } = useCases()
  const { openCaseTab } = useWorkspaceStore()
  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState('')

  const allCases = cases ?? []

  const filtered = useMemo(() => {
    let list = allCases
    if (search) {
      const q = search.toLowerCase()
      list = list.filter(
        (c) =>
          caseName(c).toLowerCase().includes(q) ||
          (c.client_name ?? '').toLowerCase().includes(q) ||
          c.current_stage.toLowerCase().includes(q) ||
          c.id.toLowerCase().includes(q),
      )
    }
    if (stageFilter) list = list.filter((c) => c.current_stage === stageFilter)
    return list
  }, [cases, search, stageFilter])

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-gray-900 p-6">
      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search cases..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-52 rounded-md border border-gray-600 bg-gray-800 py-1.5 pl-9 pr-8 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-gray-500 hover:text-gray-300"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>

        <StageDropdown value={stageFilter} onChange={setStageFilter} />
      </div>

      {/* Table card */}
      <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-gray-700/60">
        {isLoading && (
          <div className="space-y-px">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-14 animate-pulse bg-gray-800/40" />
            ))}
          </div>
        )}

        {isError && (
          <div className="flex flex-1 items-center justify-center p-12">
            <p className="text-sm text-red-400">Failed to load cases. Is the backend running?</p>
          </div>
        )}

        {!isLoading && !isError && (
          <div className="flex-1 overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 border-b border-gray-700 bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Case Name</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Client</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Products</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Stage</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Assigned To</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Updated</th>
                  <th className="px-6 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700/50 bg-gray-900">
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-16 text-center text-sm text-gray-500">
                      No cases found
                    </td>
                  </tr>
                )}
                {filtered.map((c) => {
                  const stage = STAGE_STYLES[c.current_stage] ?? { badge: 'border border-gray-600 text-gray-400', dot: 'bg-gray-400', optionDot: 'bg-gray-400' }
                  return (
                    <tr key={c.id} className="transition-colors hover:bg-gray-800/60">
                      <td className="px-6 py-4 font-medium text-gray-300">{caseName(c)}</td>
                      <td className="px-6 py-4 font-semibold text-white">{c.client_name ?? '—'}</td>
                      <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1">
                          {c.selected_products.map((p) => (
                            <span
                              key={p}
                              className="rounded-md border border-blue-500/50 bg-blue-500/10 px-2 py-0.5 text-[11px] font-semibold text-blue-400"
                            >
                              {productLabel(p)}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={['inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium', stage.badge].join(' ')}>
                          <span className={['h-1.5 w-1.5 rounded-full', stage.dot].join(' ')} />
                          {STAGE_LABELS[c.current_stage] ?? c.current_stage}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-300">{c.assigned_advisor_name ?? <span className="text-gray-600">—</span>}</td>
                      <td className="px-6 py-4 tabular-nums text-gray-400">{relativeTime(c.updated_at)}</td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => openCaseTab(c.id, c.client_id, c.case_name ?? c.id)}
                          className="flex items-center gap-1.5 rounded-md border border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:border-blue-500 hover:bg-blue-500/10 hover:text-blue-300"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          View
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
