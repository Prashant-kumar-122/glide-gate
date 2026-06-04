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
import { useThemeStore } from '@/store/themeStore'

ModuleRegistry.registerModules([AllCommunityModule])

// ── Themes ────────────────────────────────────────────────────────────────────

const darkGridTheme = themeQuartz.withPart(colorSchemeDarkBlue).withParams({
  backgroundColor:             'rgb(22 27 36)',    // gray-900 dark (#161B24)
  headerBackgroundColor:       'rgb(30 37 51)',    // gray-800 dark (#1E2533)
  borderColor:                 'rgba(42 49 64 / 0.5)', // gray-700 dark
  rowBorder:                   true,
  foregroundColor:             'rgb(192 198 212)', // gray-300 dark (#C0C6D4)
  headerTextColor:             'rgb(160 170 185)', // gray-400 dark (#A0AAB9)
  fontFamily:                  'inherit',
  fontSize:                    13,
  rowHoverColor:               'rgba(42 49 64 / 0.4)',
  selectedRowBackgroundColor:  'rgba(59 123 245 / 0.15)',
  accentColor:                 'rgb(59 123 245)',  // primary (#3B7BF5)
  oddRowBackgroundColor:       'rgb(22 27 36)',
})

const lightGridTheme = themeQuartz.withParams({
  backgroundColor:             'rgb(255 255 255)',
  headerBackgroundColor:       'rgb(249 250 251)', // gray-50
  borderColor:                 'rgba(229 231 235 / 0.8)', // gray-200
  rowBorder:                   true,
  foregroundColor:             'rgb(31 41 55)',    // gray-800
  headerTextColor:             'rgb(107 114 128)', // gray-500
  fontFamily:                  'inherit',
  fontSize:                    13,
  rowHoverColor:               'rgba(243 244 246 / 0.9)', // gray-100
  selectedRowBackgroundColor:  'rgba(59 130 246 / 0.1)',
  accentColor:                 'rgb(59 130 246)',  // blue-500
  oddRowBackgroundColor:       'rgb(255 255 255)',
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
  /** Called when a row is clicked. Enables pointer cursor on rows. */
  onRowClicked?: (data: TData) => void
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
  onRowClicked,
}: BaseGridProps<TData>) {
  const isDark = useThemeStore((s) => s.theme === 'dark')
  const mergedDefaultColDef = useMemo<ColDef>(
    () => ({ ...baseDefaultColDef, ...defaultColDef }),
    [defaultColDef],
  )

  return (
    <AgGridReact<TData>
      ref={gridRef as never}
      theme={isDark ? darkGridTheme : lightGridTheme}
      rowData={rowData}
      columnDefs={columnDefs}
      defaultColDef={mergedDefaultColDef}
      context={context}
      quickFilterText={quickFilterText}
      onRowClicked={onRowClicked ? (e) => { if (e.data) onRowClicked(e.data) } : undefined}
      rowStyle={onRowClicked ? { cursor: 'pointer' } : undefined}
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
