import { useMemo, useState } from 'react'
import { ExternalLink, Loader2 } from 'lucide-react'
import type { ColDef, ICellRendererParams, CellStyle } from 'ag-grid-community'
import { BaseGrid, TruncatedCell } from '@/components/grid/BaseGrid'
import { api } from '@/lib/api'
import type { DocumentOut } from '@/lib/api'
import { DOC_STATUS_LABEL } from '@/design-system/tokens'
import type { DocumentStatus } from '@/design-system/tokens'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface PendingDoc extends DocumentOut {
  caseName: string
  clientName: string
}

// ── Cell renderers — stateless except PreviewCell ─────────────────────────────

const STATUS_BADGE: Record<string, { badge: string; dot: string }> = {
  REQUESTED:      { badge: 'border border-blue-500/60 text-blue-400',    dot: 'bg-blue-400' },
  RECEIVED:       { badge: 'border border-violet-500/60 text-violet-400', dot: 'bg-violet-400' },
  UNDER_REVIEW:   { badge: 'border border-amber-500/60 text-amber-400',  dot: 'bg-amber-400' },
  NEEDS_REVISION: { badge: 'border border-red-500/60 text-red-400',      dot: 'bg-red-400' },
  APPROVED:       { badge: 'border border-green-500/60 text-green-400',  dot: 'bg-green-400' },
  NOT_REQUESTED:  { badge: 'border border-gray-500/60 text-gray-400',    dot: 'bg-gray-400' },
}

function StatusCell({ value }: ICellRendererParams<PendingDoc, string>) {
  if (!value) return null
  const s = STATUS_BADGE[value] ?? STATUS_BADGE.NOT_REQUESTED
  const label = DOC_STATUS_LABEL[value as DocumentStatus] ?? value
  return (
    <span className={['inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium', s.badge].join(' ')}>
      <span className={['h-1.5 w-1.5 rounded-full', s.dot].join(' ')} />
      {label}
    </span>
  )
}

function PreviewCell({ data }: ICellRendererParams<PendingDoc>) {
  const [loading, setLoading] = useState(false)

  if (!data) return null

  // REQUESTED = no file uploaded yet; all other statuses have an uploaded file
  if (data.status === 'REQUESTED') {
    return <span style={{ fontSize: 11, color: 'rgb(var(--gray-500))' }}>Not uploaded</span>
  }

  async function handlePreview(e: React.MouseEvent) {
    e.stopPropagation()
    if (loading) return
    setLoading(true)
    try {
      const res = await api.get(`/documents/${data!.id}/download`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      window.open(url, '_blank')
    } catch {
      // silent — file may be missing from storage
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handlePreview}
      disabled={loading}
      className="flex items-center gap-1 text-xs font-medium text-blue-600 transition-colors hover:text-blue-800 disabled:opacity-50 dark:text-blue-400 dark:hover:text-blue-300"
    >
      {loading
        ? <Loader2 className="h-3 w-3 animate-spin" />
        : <ExternalLink className="h-3 w-3" />}
      Preview
    </button>
  )
}

function NoPendingOverlay() {
  return <span className="text-sm text-gray-500">All documents are up to date</span>
}

// ── Grid ──────────────────────────────────────────────────────────────────────

interface Props {
  docs: PendingDoc[]
  isLoading: boolean
  onDocClick: (doc: PendingDoc) => void
}

export default function PendingDocumentsGrid({ docs, isLoading, onDocClick }: Props) {
  const colDefs = useMemo<ColDef<PendingDoc>[]>(() => [
    {
      headerName: 'Document Name',
      field: 'name',
      flex: 2,
      minWidth: 180,
      filter: 'agTextColumnFilter',
      tooltipField: 'name',
      cellRenderer: TruncatedCell,
      cellRendererParams: { style: { fontWeight: '700' } },
    },
    {
      headerName: 'Case Name',
      field: 'caseName',
      flex: 1.5,
      minWidth: 150,
      filter: 'agTextColumnFilter',
      tooltipField: 'caseName',
      cellRenderer: TruncatedCell,
    },
    {
      headerName: 'Category',
      field: 'category',
      flex: 1,
      minWidth: 120,
      filter: 'agTextColumnFilter',
      tooltipValueGetter: (p) =>
        p.data?.category
          ? p.data.category.charAt(0).toUpperCase() + p.data.category.slice(1)
          : '',
      cellRenderer: TruncatedCell,
      valueFormatter: (p) =>
        p.value ? p.value.charAt(0).toUpperCase() + p.value.slice(1) : '—',
    },
    {
      headerName: 'Uploaded By',
      field: 'clientName',
      flex: 1.2,
      minWidth: 130,
      filter: 'agTextColumnFilter',
      tooltipField: 'clientName',
      cellRenderer: TruncatedCell,
    },
    {
      headerName: 'Status',
      field: 'status',
      flex: 1.2,
      minWidth: 140,
      filter: 'agTextColumnFilter',
      tooltipValueGetter: (p) =>
        p.data?.status ? DOC_STATUS_LABEL[p.data.status as DocumentStatus] : '',
      cellRenderer: StatusCell,
      filterValueGetter: (p) =>
        p.data?.status ? DOC_STATUS_LABEL[p.data.status as DocumentStatus] : '',
    },
    {
      headerName: 'Preview',
      field: 'id',
      width: 100,
      sortable: false,
      filter: false,
      resizable: false,
      cellRenderer: PreviewCell,
      cellStyle: { display: 'flex', alignItems: 'center' } as CellStyle,
    },
  ], [])

  return (
    <BaseGrid<PendingDoc>
      rowData={isLoading ? undefined : docs}
      columnDefs={colDefs}
      onRowClicked={onDocClick}
      noRowsOverlayComponent={NoPendingOverlay}
      rowHeight={44}
      headerHeight={40}
    />
  )
}
