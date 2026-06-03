import { useMemo } from 'react'
import { AgGridReact } from 'ag-grid-react'
import {
  themeQuartz,
  colorSchemeDarkBlue,
  AllCommunityModule,
  ModuleRegistry,
} from 'ag-grid-community'
import type {
  ColDef,
  GridReadyEvent,
  ModelUpdatedEvent,
  ICellRendererParams,
} from 'ag-grid-community'

ModuleRegistry.registerModules([AllCommunityModule])

// ── Theme ─────────────────────────────────────────────────────────────────────

export const gridTheme = themeQuartz.withPart(colorSchemeDarkBlue).withParams({
  backgroundColor: 'rgb(17 24 39)',
  headerBackgroundColor: 'rgb(31 41 55)',
  borderColor: 'rgba(55 65 81 / 0.5)',
  rowBorder: true,
  foregroundColor: 'rgb(209 213 219)',
  headerTextColor: 'rgb(156 163 175)',
  fontFamily: 'inherit',
  fontSize: 13,
  rowHoverColor: 'rgba(31 41 55 / 0.7)',
  selectedRowBackgroundColor: 'rgba(59 130 246 / 0.15)',
  accentColor: 'rgb(59 130 246)',
  oddRowBackgroundColor: 'rgb(17 24 39)',
})

// ── Overlays — module-level so AG Grid never gets a new reference ──────────────

function DefaultLoadingOverlay() {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-400">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-600 border-t-blue-500" />
      Loading…
    </div>
  )
}

function DefaultNoRowsOverlay() {
  return <span className="text-sm text-gray-500">No rows found</span>
}

// ── Base column defaults ──────────────────────────────────────────────────────

export const baseDefaultColDef: ColDef = {
  sortable: true,
  resizable: true,
  filter: false,
  floatingFilter: false,
  suppressMovable: true,
  filterParams: { debounceMs: 200, maxNumConditions: 1 },
}

// ── Generic cell renderers ────────────────────────────────────────────────────

const TRUNCATE: React.CSSProperties = {
  display: 'block',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
}

// Stateless — no hooks. Safe to mount/unmount rapidly during virtualized scroll.
export function TruncatedCell({
  value,
  valueFormatted,
  style,
}: ICellRendererParams & { style?: React.CSSProperties }) {
  const display = valueFormatted ?? (typeof value === 'string' ? value : '') ?? ''
  return <span style={{ ...TRUNCATE, ...style }}>{display}</span>
}

// ── BaseGrid ──────────────────────────────────────────────────────────────────

export interface BaseGridProps<TData = unknown> {
  rowData: TData[] | undefined
  columnDefs: ColDef<TData>[]
  /** Merged on top of baseDefaultColDef. */
  defaultColDef?: ColDef<TData>
  context?: unknown
  quickFilterText?: string
  onGridReady?: (e: GridReadyEvent<TData>) => void
  onModelUpdated?: (e: ModelUpdatedEvent<TData>) => void
  rowHeight?: number
  headerHeight?: number
  /** Pass gridRef.current to get access to the AG Grid API (e.g. setFilterModel). */
  gridRef?: React.RefObject<AgGridReact<TData> | null>
  /** Override the default loading overlay. Must be a stable (module-level) reference. */
  loadingOverlayComponent?: () => React.ReactElement
  /** Override the default no-rows overlay. Must be a stable (module-level) reference. */
  noRowsOverlayComponent?: () => React.ReactElement
}

export function BaseGrid<TData = unknown>({
  rowData,
  columnDefs,
  defaultColDef,
  context,
  quickFilterText,
  onGridReady,
  onModelUpdated,
  rowHeight = 56,
  headerHeight = 44,
  gridRef,
  loadingOverlayComponent = DefaultLoadingOverlay,
  noRowsOverlayComponent = DefaultNoRowsOverlay,
}: BaseGridProps<TData>) {
  const mergedDefaultColDef = useMemo<ColDef>(
    () => ({ ...baseDefaultColDef, ...defaultColDef }),
    [defaultColDef],
  )

  return (
    <AgGridReact<TData>
      ref={gridRef}
      theme={gridTheme}
      rowData={rowData}
      columnDefs={columnDefs}
      defaultColDef={mergedDefaultColDef}
      context={context}
      quickFilterText={quickFilterText}
      onGridReady={onGridReady}
      onModelUpdated={onModelUpdated}
      rowHeight={rowHeight}
      headerHeight={headerHeight}
      animateRows
      suppressCellFocus
      suppressRowClickSelection
      suppressRowVirtualisation={false}
      suppressColumnVirtualisation={false}
      tooltipShowDelay={300}
      tooltipHideDelay={100}
      loadingOverlayComponent={loadingOverlayComponent}
      noRowsOverlayComponent={noRowsOverlayComponent}
    />
  )
}
