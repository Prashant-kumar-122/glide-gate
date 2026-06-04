import { Briefcase, Wifi, WifiOff, X, BadgeCheck, Search } from 'lucide-react'
import { useState } from 'react'
import { useWorkspaceStore } from '@/store/workspaceStore'
import ProgressBar from '@/components/ProgressBar'
import { useCases, useAccount } from '@/hooks/useDocuments'
import type { CaseOut } from '@/lib/api'

const STAGE_LABELS: Record<string, string> = {
  INTAKE:            'Intake',
  KYC:               'KYC',
  PARALLEL_PRODUCTS: 'Products',
  REVIEW:            'Review',
  COMPLETE:          'Complete',
  ESCALATED:         'Escalated',
}

interface CaseItemProps {
  c: CaseOut
  isSelected: boolean
  badgeCount: number
  onSelect: () => void
}

function caseDisplayName(c: CaseOut): string {
  if (c.case_name) return c.case_name
  if (c.selected_products.length > 0)
    return c.selected_products
      .map((p) => p.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()))
      .join(' & ')
  return c.client_name ?? 'Case'
}

function CaseItem({ c, isSelected, badgeCount, onSelect }: CaseItemProps) {
  const progress   = Math.round(c.percentage ?? 0)
  const stageLabel = STAGE_LABELS[c.current_stage] ?? c.current_stage
  const { data: account } = useAccount(c.id, c.current_stage === 'COMPLETE')

  return (
    <button
      onClick={onSelect}
      className={[
        'w-full px-3 py-2.5 text-left transition-colors border-l-2',
        isSelected
          ? 'border-primary bg-blue-50 dark:bg-primary-subtle'
          : 'border-transparent bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800/60',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className={[
            'truncate text-xs font-semibold',
            isSelected
              ? 'text-primary dark:text-white'
              : 'text-gray-800 dark:text-gray-100',
          ].join(' ')}>
            {caseDisplayName(c)}
          </p>
          <p className={[
            'mt-0.5 text-[10px] font-medium uppercase tracking-wide',
            isSelected
              ? 'text-primary/70 dark:text-blue-200'
              : 'text-gray-500 dark:text-gray-400',
          ].join(' ')}>
            {stageLabel}
          </p>
          {account && account.map((acc) => (
            <p key={acc.account_number} className="mt-0.5 flex items-center gap-1 font-mono text-[10px] font-medium truncate text-emerald-600 dark:text-emerald-400">
              <BadgeCheck className="w-2.5 h-2.5 shrink-0" />
              {acc.account_number}
            </p>
          ))}
        </div>

        {badgeCount > 0 && (
          <span className="flex h-4 min-w-4 items-center justify-center bg-red-500 px-1 text-[9px] font-bold text-white shrink-0">
            {badgeCount}
          </span>
        )}
      </div>

      <div className="mt-2">
        <ProgressBar
          value={progress}
          size="sm"
          color={
            c.current_stage === 'COMPLETE'  ? 'success' :
            c.current_stage === 'ESCALATED' ? 'warning' : 'default'
          }
        />
      </div>

      <p className={[
        'mt-1 text-right font-mono text-[9px] tabular-nums',
        isSelected ? 'text-primary/70 dark:text-blue-200' : 'text-gray-400 dark:text-gray-500',
      ].join(' ')}>
        {progress}%
      </p>
    </button>
  )
}

interface ClientRailNavProps {
  isMobileOpen?: boolean
  onMobileClose?: () => void
}

export default function ClientRailNav({ isMobileOpen = false, onMobileClose }: ClientRailNavProps) {
  const { selectedCaseId, socketConnected, setSelectedClient, uploadBadgeCounts } = useWorkspaceStore()
  const { data: cases, isLoading, isError } = useCases()
  const [search, setSearch] = useState('')

  const filtered = (cases ?? []).filter((c) => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      caseDisplayName(c).toLowerCase().includes(q) ||
      (c.client_name ?? '').toLowerCase().includes(q) ||
      c.current_stage.toLowerCase().includes(q) ||
      c.selected_products.some((p) => p.toLowerCase().includes(q))
    )
  })

  function handleSelect(clientId: string, caseId: string) {
    setSelectedClient(clientId, caseId)
    onMobileClose?.()
  }

  return (
    <aside
      className={[
        // max-w prevents overflow on very small screens (320px)
        'fixed inset-y-0 left-0 z-40 flex w-[260px] max-w-[calc(100vw-3rem)] shrink-0 flex-col',
        'border-r border-gray-200 bg-gray-50 shadow-lg dark:border-gray-800 dark:bg-gray-950',
        'transition-transform duration-200 ease-in-out',
        isMobileOpen ? 'translate-x-0' : '-translate-x-full',
        'lg:relative lg:inset-auto lg:z-auto lg:w-56 lg:max-w-none lg:translate-x-0 lg:shadow-none lg:transition-none',
      ].join(' ')}
      aria-label="Cases sidebar"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-3 py-2.5 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <Briefcase className="h-3.5 w-3.5 text-gray-500 dark:text-gray-500" />
          <span className="text-[10px] font-semibold uppercase tracking-widest text-gray-600 dark:text-gray-500">Cases</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span title={socketConnected ? 'Live data' : 'Disconnected'}>
            {socketConnected
              ? <Wifi className="h-3.5 w-3.5 text-green-500" />
              : <WifiOff className="h-3.5 w-3.5 text-gray-400" />
            }
          </span>
          {onMobileClose && (
            <button
              onClick={onMobileClose}
              className="p-0.5 text-gray-500 transition-colors hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 lg:hidden"
              aria-label="Close cases panel"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="border-b border-gray-200 px-3 py-2 dark:border-gray-800">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3 w-3 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search cases…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full border border-gray-200 bg-white py-1.5 pl-7 pr-3 text-xs text-gray-900 placeholder-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:placeholder-gray-600"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              aria-label="Clear search"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
        {search && (
          <p className="mt-1 text-[10px] text-gray-500 dark:text-gray-400">
            {filtered.length} of {cases?.length ?? 0} cases
          </p>
        )}
      </div>

      {/* Case list */}
      <div className="flex-1 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-800/50">
        {isLoading && (
          <div className="p-3 space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 animate-pulse bg-gray-200 dark:bg-gray-800" />
            ))}
          </div>
        )}

        {isError && (
          <p className="m-3 border border-red-200 bg-red-50 p-2.5 text-[10px] text-red-700 dark:border-red-700/30 dark:bg-red-950/40 dark:text-red-400">
            Failed to load cases. Is the backend running?
          </p>
        )}

        {!isLoading && !isError && filtered.length === 0 && (
          <div className="flex flex-col items-center py-12 text-center px-4">
            <Search className="h-6 w-6 text-gray-300 dark:text-gray-700" />
            <p className="mt-2 text-[10px] text-gray-500 dark:text-gray-400">
              {search ? 'No cases match your search' : 'No active cases'}
            </p>
          </div>
        )}

        {filtered.map((c) => (
          <CaseItem
            key={c.id}
            c={c}
            isSelected={selectedCaseId === c.id}
            badgeCount={uploadBadgeCounts[c.id] ?? 0}
            onSelect={() => handleSelect(c.client_id, c.id)}
          />
        ))}
      </div>

      {/* Footer */}
      {cases && cases.length > 0 && (
        <div className="border-t border-gray-200 px-3 py-2 dark:border-gray-800">
          <p className="font-mono text-[10px] text-gray-500 dark:text-gray-400">
            {cases.length} active case{cases.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}
    </aside>
  )
}
