import { useState, useMemo, useRef, useEffect, useCallback } from 'react'
import { Search, Eye, X, ChevronDown, Check, Plus } from 'lucide-react'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef, ICellRendererParams, GridReadyEvent, ModelUpdatedEvent, CellStyle } from 'ag-grid-community'
import { BaseGrid, TruncatedCell } from '@/components/grid/BaseGrid'
import { useCases } from '@/hooks/useDocuments'
import type { CaseOut } from '@/lib/api'
import { useWorkspaceStore } from '@/store/workspaceStore'
import { useAuthStore } from '@/store/authStore'
import InstitutionalCaseModal from './InstitutionalCaseModal'

// ── Stage config ──────────────────────────────────────────────────────────────

const STAGE_LABELS: Record<string, string> = {
  INTAKE:            'Intake',
  KYC:               'KYC',
  PARALLEL_PRODUCTS: 'Products',
  REVIEW:            'Advisor Review',
  SALES_REVIEW:      'Sales Review',
  COMPLETE:          'Live',
  ESCALATED:         'Escalated',
}

const STAGE_STYLES: Record<string, { badge: string; dot: string; optionDot: string }> = {
  INTAKE:            { badge: 'border border-gray-600/50 text-gray-400',    dot: 'bg-gray-500',   optionDot: 'bg-gray-400' },
  KYC:               { badge: 'border border-blue-600/50 text-blue-400',    dot: 'bg-blue-500',   optionDot: 'bg-blue-400' },
  PARALLEL_PRODUCTS: { badge: 'border border-violet-600/50 text-violet-400',dot: 'bg-violet-500', optionDot: 'bg-violet-400' },
  REVIEW:            { badge: 'border border-amber-600/50 text-amber-400',  dot: 'bg-amber-500',  optionDot: 'bg-amber-400' },
  SALES_REVIEW:      { badge: 'border border-amber-600/50 text-amber-400',  dot: 'bg-amber-500',  optionDot: 'bg-amber-400' },
  COMPLETE:          { badge: 'border border-green-600/50 text-green-400',  dot: 'bg-green-500',  optionDot: 'bg-green-400' },
  ESCALATED:         { badge: 'border border-red-600/50 text-red-400',      dot: 'bg-red-500',    optionDot: 'bg-red-400' },
}

const ALL_STAGES = ['INTAKE', 'REVIEW', 'SALES_REVIEW', 'KYC', 'PARALLEL_PRODUCTS', 'COMPLETE', 'ESCALATED']

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
  const days   = Math.floor(diffMs / 86_400_000)
  if (days > 0)  return `${days}d ago`
  const hours  = Math.floor(diffMs / 3_600_000)
  if (hours > 0) return `${hours}h ago`
  return `${Math.floor(diffMs / 60_000)}m ago`
}

// ── Cell renderers ────────────────────────────────────────────────────────────

function ProductsCell({ value }: ICellRendererParams<CaseOut, string[]>) {
  const label = value?.length ? value.map((p) => p.replace(/_/g, ' ').toUpperCase()).join(', ') : ''
  if (!label) return <span style={{ color: 'rgb(var(--gray-500))' }}>—</span>
  return (
    <span style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'rgb(var(--blue-400))' }}>
      {label}
    </span>
  )
}

function StageCell({ value }: ICellRendererParams<CaseOut, string>) {
  if (!value) return null
  const style = STAGE_STYLES[value] ?? { badge: 'border border-gray-600/50 text-gray-400', dot: 'bg-gray-500', optionDot: 'bg-gray-400' }
  return (
    <span className={['inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide', style.badge].join(' ')}>
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
      className="flex items-center gap-1.5 border border-gray-600/50 px-3 py-1 text-[10px] font-medium uppercase tracking-wide text-gray-400 transition-colors hover:border-primary/60 hover:bg-primary-subtle hover:text-primary"
    >
      <Eye className="h-3 w-3" />
      View
    </button>
  )
}

function NoCasesOverlay() {
  return <span className="text-xs text-gray-500">No cases found</span>
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
  const selectedDot   = value ? STAGE_STYLES[value]?.dot : null

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={[
          'flex min-w-[130px] items-center justify-between gap-2 border px-3 py-1.5 text-xs transition-colors',
          open
            ? 'border-primary bg-blue-50 text-primary dark:bg-primary-subtle dark:text-white'
            : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300',
        ].join(' ')}
      >
        <span className="flex items-center gap-2">
          {selectedDot && <span className={['h-1.5 w-1.5 rounded-full', selectedDot].join(' ')} />}
          {selectedLabel}
        </span>
        <ChevronDown className={['h-3 w-3 text-gray-400 transition-transform', open ? 'rotate-180' : ''].join(' ')} />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-0.5 min-w-[150px] border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-900">
          <button
            onClick={() => { onChange(''); setOpen(false) }}
            className={[
              'flex w-full items-center justify-between px-3 py-2 text-xs transition-colors',
              !value ? 'bg-blue-50 text-primary dark:bg-primary-subtle dark:text-white' : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800',
            ].join(' ')}
          >
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full opacity-0" />
              All Stages
            </span>
            {!value && <Check className="h-3 w-3 text-primary" />}
          </button>
          <div className="mx-2 border-t border-gray-100 dark:border-gray-800" />
          {ALL_STAGES.map((s) => {
            const style  = STAGE_STYLES[s]
            const active = value === s
            return (
              <button
                key={s}
                onClick={() => { onChange(s); setOpen(false) }}
                className={[
                  'flex w-full items-center justify-between px-3 py-2 text-xs transition-colors',
                  active ? 'bg-blue-50 text-primary dark:bg-primary-subtle dark:text-white' : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800',
                ].join(' ')}
              >
                <span className="flex items-center gap-2">
                  <span className={['h-1.5 w-1.5 rounded-full', style.optionDot].join(' ')} />
                  {STAGE_LABELS[s]}
                </span>
                {active && <Check className="h-3 w-3 text-primary" />}
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
  const { data: cases, isLoading, isError } = useCases()
  const { openCaseTab } = useWorkspaceStore()
  const { user } = useAuthStore()

  const [search,        setSearch]        = useState('')
  const [stageFilter,   setStageFilter]   = useState('')
  const [filteredCount, setFilteredCount] = useState<number | null>(null)
  const [showInstModal, setShowInstModal] = useState(false)
  const gridRef = useRef<AgGridReact<CaseOut>>(null)

  const rowData = useMemo(() => cases ?? [], [cases])

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
      cellRendererParams: { style: { fontWeight: '600' } },
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
      cellRendererParams: { style: { color: 'rgb(var(--gray-500))' } },
      valueFormatter: (p) => p.value ?? '—',
    },
    {
      headerName: 'Updated',
      field: 'updated_at',
      flex: 0.8,
      minWidth: 110,
      filter: false,
      cellRenderer: TruncatedCell,
      cellRendererParams: { style: { color: 'rgb(var(--gray-400))', fontVariantNumeric: 'tabular-nums', fontFamily: 'IBM Plex Mono, monospace' } },
      valueFormatter: (p) => relativeTime(p.value),
    },
    {
      headerName: '',
      field: 'id',
      width: 100,
      sortable: false,
      filter: false,
      resizable: false,
      cellRenderer: ViewCell,
      cellStyle: { display: 'flex', alignItems: 'center', justifyContent: 'flex-end' } as CellStyle,
    },
  ], [])

  const context    = useMemo(() => ({ openCaseTab }), [openCaseTab])
  const totalCount = cases?.length ?? 0

  const onGridReady     = useCallback((e: GridReadyEvent) => { setFilteredCount(e.api.getDisplayedRowCount()) }, [])
  const onModelUpdated  = useCallback((e: ModelUpdatedEvent) => { setFilteredCount(e.api.getDisplayedRowCount()) }, [])
  const onQuickFilter   = useCallback((e: React.ChangeEvent<HTMLInputElement>) => { setSearch(e.target.value) }, [])

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-white p-4 dark:bg-gray-950 sm:p-6">
      {/* Toolbar */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          {/* Search input */}
          <div className="relative w-full sm:w-auto">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3 w-3 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search cases…"
              value={search}
              onChange={onQuickFilter}
              className="w-full border border-gray-200 bg-white py-1.5 pl-8 pr-8 text-xs text-gray-800 placeholder-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:placeholder-gray-600 sm:w-48"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>

          <StageDropdown value={stageFilter} onChange={setStageFilter} />

          {user?.role === 'sales_manager' && (
            <button
              onClick={() => setShowInstModal(true)}
              className="flex items-center gap-1.5 bg-primary px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-primary-hover"
            >
              <Plus className="h-3 w-3" />
              Open New Account
            </button>
          )}
        </div>

        {!isLoading && totalCount > 0 && (
          <p className="font-mono text-xs text-gray-500 dark:text-gray-400">
            {filteredCount !== null && filteredCount !== totalCount ? (
              <>
                <span className="font-semibold text-gray-800 dark:text-gray-100">{filteredCount}</span>
                <span> / </span>
                <span className="font-semibold text-gray-800 dark:text-gray-100">{totalCount}</span>
                <span> cases</span>
              </>
            ) : (
              <>
                <span className="font-semibold text-gray-800 dark:text-gray-100">{totalCount}</span>
                <span> cases</span>
              </>
            )}
          </p>
        )}
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-hidden border border-gray-200 dark:border-gray-800">
        {isError ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-xs text-red-400">Failed to load cases. Is the backend running?</p>
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

      {showInstModal && (
        <InstitutionalCaseModal
          onCreated={(caseId, clientId, label) => {
            setShowInstModal(false)
            openCaseTab(caseId, clientId, label)
          }}
          onClose={() => setShowInstModal(false)}
        />
      )}
    </div>
  )
}
