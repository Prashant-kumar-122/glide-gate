import { useState, useMemo, useRef, useEffect, useCallback } from 'react'
import { Search, Eye, X, ChevronDown, Check } from 'lucide-react'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef, ICellRendererParams, GridReadyEvent, ModelUpdatedEvent, CellStyle } from 'ag-grid-community'
import { BaseGrid, TruncatedCell } from '@/components/grid/BaseGrid'
import { useCases } from '@/hooks/useDocuments'
import type { CaseOut } from '@/lib/api'
import { useWorkspaceStore } from '@/store/workspaceStore'

// ── Stage config ──────────────────────────────────────────────────────────────

const STAGE_LABELS: Record<string, string> = {
  INTAKE: 'Intake',
  KYC: 'KYC',
  PARALLEL_PRODUCTS: 'Products',
  REVIEW: 'Sales Review',
  COMPLETE: 'Live',
  ESCALATED: 'Escalated',
}

const STAGE_STYLES: Record<string, { badge: string; dot: string; optionDot: string }> = {
  INTAKE:            { badge: 'border border-gray-500/60 text-gray-400',     dot: 'bg-gray-400',    optionDot: 'bg-gray-400' },
  KYC:               { badge: 'border border-blue-500/60 text-blue-400',     dot: 'bg-blue-400',    optionDot: 'bg-blue-400' },
  PARALLEL_PRODUCTS: { badge: 'border border-purple-500/60 text-purple-400', dot: 'bg-purple-400',  optionDot: 'bg-purple-400' },
  REVIEW:            { badge: 'border border-cyan-500/60 text-cyan-400',     dot: 'bg-cyan-400',    optionDot: 'bg-cyan-400' },
  COMPLETE:          { badge: 'border border-teal-500/60 text-teal-400',     dot: 'bg-teal-400',    optionDot: 'bg-teal-400' },
  ESCALATED:         { badge: 'border border-red-500/60 text-red-400',       dot: 'bg-red-400',     optionDot: 'bg-red-400' },
}

const ALL_STAGES = ['INTAKE', 'KYC', 'PARALLEL_PRODUCTS', 'REVIEW', 'COMPLETE', 'ESCALATED']

// ── Helpers ───────────────────────────────────────────────────────────────────

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
  return `${Math.floor(diffMs / 60_000)}m ago`
}

// ── Cell renderers — stateless, no hooks, safe for virtualized scroll ─────────

function ProductsCell({ value }: ICellRendererParams<CaseOut, string[]>) {
  const label = value?.length ? value.map((p) => p.replace(/_/g, ' ').toUpperCase()).join(', ') : ''
  if (!label) return <span style={{ color: 'rgb(107 114 128)' }}>—</span>
  return (
    <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'rgb(147 197 253)' }}>
      {label}
    </span>
  )
}

function StageCell({ value }: ICellRendererParams<CaseOut, string>) {
  if (!value) return null
  const style = STAGE_STYLES[value] ?? { badge: 'border border-gray-600 text-gray-400', dot: 'bg-gray-400', optionDot: 'bg-gray-400' }
  return (
    <span className={['inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium', style.badge].join(' ')}>
      <span className={['h-1.5 w-1.5 rounded-full', style.dot].join(' ')} />
      {STAGE_LABELS[value] ?? value}
    </span>
  )
}

function ViewCell({ data, context }: ICellRendererParams<CaseOut>) {
  if (!data) return null
  return (
    <button
      onClick={() => context.openCaseTab(data.id, data.client_id, data.case_name ?? data.id)}
      className="flex items-center gap-1.5 rounded-md border border-gray-600 px-3 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:border-blue-500 hover:bg-blue-500/10 hover:text-blue-300"
    >
      <Eye className="h-3.5 w-3.5" />
      View
    </button>
  )
}

// ── No-rows overlay — module-level so BaseGrid never receives a new reference ──

function NoCasesOverlay() {
  return <span className="text-sm text-gray-500">No cases found</span>
}

// ── Stage dropdown ────────────────────────────────────────────────────────────

interface StageDropdownProps {
  value: string
  onChange: (v: string) => void
}

function StageDropdown({ value, onChange }: StageDropdownProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onOutside)
    return () => document.removeEventListener('mousedown', onOutside)
  }, [])

  const selectedLabel = value ? STAGE_LABELS[value] : 'All Stages'
  const selectedDot = value ? STAGE_STYLES[value]?.dot : null

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={[
          'flex min-w-[140px] items-center justify-between gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors',
          open ? 'border-blue-500 bg-gray-800 text-white' : 'border-gray-600 bg-gray-800 text-gray-300 hover:border-gray-500',
        ].join(' ')}
      >
        <span className="flex items-center gap-2">
          {selectedDot && <span className={['h-2 w-2 rounded-full', selectedDot].join(' ')} />}
          {selectedLabel}
        </span>
        <ChevronDown className={['h-3.5 w-3.5 text-gray-400 transition-transform', open ? 'rotate-180' : ''].join(' ')} />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 min-w-[160px] overflow-hidden rounded-md border border-gray-600 bg-gray-800 shadow-xl">
          <button
            onClick={() => { onChange(''); setOpen(false) }}
            className={['flex w-full items-center justify-between px-3 py-2 text-sm transition-colors', !value ? 'bg-blue-600/30 text-white' : 'text-gray-300 hover:bg-gray-700'].join(' ')}
          >
            <span className="flex items-center gap-2.5">
              <span className="h-2 w-2 rounded-full opacity-0" />
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
                className={['flex w-full items-center justify-between px-3 py-2 text-sm transition-colors', active ? 'bg-blue-600/30 text-white' : 'text-gray-300 hover:bg-gray-700'].join(' ')}
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

// ── Main component ────────────────────────────────────────────────────────────

export default function CaseListTable() {
  // TanStack Query — server state
  const { data: cases, isLoading, isError } = useCases()
  // Zustand — workspace UI state
  const { openCaseTab } = useWorkspaceStore()

  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState('')
  const [filteredCount, setFilteredCount] = useState<number | null>(null)
  const gridRef = useRef<AgGridReact<CaseOut>>(null)

  // Full dataset — row identity is stable; AG Grid filters in-place via filterModel.
  const rowData = useMemo(() => cases ?? [], [cases])

  // Drive stage filter through AG Grid's own filter engine instead of slicing rowData.
  // This preserves row identity so virtualization doesn't re-mount all rows on filter change.
  useEffect(() => {
    const api = gridRef.current?.api
    if (!api) return
    if (stageFilter) {
      api.setFilterModel({ current_stage: { filterType: 'text', type: 'equals', filter: stageFilter } })
    } else {
      api.setFilterModel(null)
    }
  }, [stageFilter])

  const colDefs = useMemo<ColDef<CaseOut>[]>(() => [
    {
      headerName: 'Case Name',
      valueGetter: (p) => caseName(p.data!),
      tooltipValueGetter: (p) => caseName(p.data!),
      flex: 1.5,
      minWidth: 160,
      filter: 'agTextColumnFilter',
      cellRenderer: TruncatedCell,
    },
    {
      headerName: 'Client',
      field: 'client_name',
      tooltipField: 'client_name',
      flex: 1.2,
      minWidth: 130,
      filter: 'agTextColumnFilter',
      cellRenderer: TruncatedCell,
      cellRendererParams: { style: { fontWeight: '600', color: 'white' } },
    },
    {
      headerName: 'Products',
      field: 'selected_products',
      tooltipValueGetter: (p) =>
        p.data?.selected_products?.map((pr) => pr.replace(/_/g, ' ').toUpperCase()).join(', ') ?? '',
      flex: 1.5,
      minWidth: 160,
      cellRenderer: ProductsCell,
      sortable: false,
      filter: false,
    },
    {
      headerName: 'Stage',
      field: 'current_stage',
      flex: 1,
      minWidth: 140,
      cellRenderer: StageCell,
      filter: 'agTextColumnFilter',
      filterValueGetter: (p) => STAGE_LABELS[p.data?.current_stage ?? ''] ?? p.data?.current_stage,
    },
    {
      headerName: 'Assigned To',
      field: 'assigned_advisor_name',
      tooltipField: 'assigned_advisor_name',
      flex: 1,
      minWidth: 130,
      filter: 'agTextColumnFilter',
      cellRenderer: TruncatedCell,
      cellRendererParams: { style: { color: 'rgb(209 213 219)' } },
      valueFormatter: (p) => p.value ?? '—',
    },
    {
      headerName: 'Updated',
      field: 'updated_at',
      flex: 0.8,
      minWidth: 110,
      filter: false,
      cellRenderer: TruncatedCell,
      cellRendererParams: { style: { color: 'rgb(156 163 175)', fontVariantNumeric: 'tabular-nums' } },
      valueFormatter: (p) => relativeTime(p.value),
    },
    {
      headerName: '',
      field: 'id',
      width: 110,
      sortable: false,
      filter: false,
      resizable: false,
      cellRenderer: ViewCell,
      cellStyle: { display: 'flex', alignItems: 'center', justifyContent: 'flex-end' } as CellStyle,
    },
  ], [])

  const context = useMemo(() => ({ openCaseTab }), [openCaseTab])
  const totalCount = cases?.length ?? 0

  const onGridReady = useCallback((e: GridReadyEvent) => {
    setFilteredCount(e.api.getDisplayedRowCount())
  }, [])

  const onModelUpdated = useCallback((e: ModelUpdatedEvent) => {
    setFilteredCount(e.api.getDisplayedRowCount())
  }, [])

  const onQuickFilter = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value)
  }, [])

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-gray-900 p-3 sm:p-6">
      {/* Filters + count */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative w-full sm:w-auto">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Search cases..."
              value={search}
              onChange={onQuickFilter}
              className="w-full rounded-md border border-gray-600 bg-gray-800 py-1.5 pl-9 pr-8 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 sm:w-52"
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

        {!isLoading && totalCount > 0 && (
          <p className="text-sm text-gray-400">
            {filteredCount !== null && filteredCount !== totalCount ? (
              <>
                <span className="font-semibold text-white">{filteredCount}</span>
                <span className="text-gray-500"> of </span>
                <span className="font-semibold text-white">{totalCount}</span>
                <span className="text-gray-500"> cases</span>
              </>
            ) : (
              <>
                <span className="font-semibold text-white">{totalCount}</span>
                <span className="text-gray-500"> cases</span>
              </>
            )}
          </p>
        )}
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-hidden rounded-lg border border-gray-700/60">
        {isError ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-red-400">Failed to load cases. Is the backend running?</p>
          </div>
        ) : (
          <BaseGrid<CaseOut>
            gridRef={gridRef}
            rowData={isLoading ? undefined : rowData}
            columnDefs={colDefs}
            context={context}
            quickFilterText={search}
            onGridReady={onGridReady}
            onModelUpdated={onModelUpdated}
            noRowsOverlayComponent={NoCasesOverlay}
          />
        )}
      </div>
    </div>
  )
}
