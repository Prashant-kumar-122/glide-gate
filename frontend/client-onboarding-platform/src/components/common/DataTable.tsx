import type { ReactNode } from 'react';
import { IconInbox } from '@tabler/icons-react';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  width?: string;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyMessage?: string;
}

// ─── Skeleton row ─────────────────────────────────────────────────────────────

function SkeletonRow({ colCount }: { colCount: number }) {
  return (
    <tr className="border-t border-border-subtle">
      {Array.from({ length: colCount }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 rounded bg-bg-elevated animate-pulse" style={{ width: `${60 + (i * 17) % 30}%` }} />
        </td>
      ))}
    </tr>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function DataTable<T extends object>({
  columns,
  data,
  onRowClick,
  loading = false,
  emptyMessage = 'No records found.',
}: DataTableProps<T>) {
  const hasData   = data.length > 0;
  const clickable = typeof onRowClick === 'function';

  return (
    <div className="bg-bg-surface border border-border-default rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          {/* ── Header ── */}
          <thead>
            <tr className="bg-bg-elevated">
              {columns.map(col => (
                <th
                  key={col.key}
                  style={col.width ? { width: col.width } : undefined}
                  className="px-4 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider whitespace-nowrap"
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>

          {/* ── Body ── */}
          <tbody>
            {/* Loading state: 3 skeleton rows */}
            {loading && (
              <>
                <SkeletonRow colCount={columns.length} />
                <SkeletonRow colCount={columns.length} />
                <SkeletonRow colCount={columns.length} />
              </>
            )}

            {/* Empty state */}
            {!loading && !hasData && (
              <tr>
                <td colSpan={columns.length}>
                  <div className="flex flex-col items-center justify-center gap-3 py-14 text-text-muted">
                    <IconInbox size={36} strokeWidth={1.25} />
                    <p className="text-sm">{emptyMessage}</p>
                  </div>
                </td>
              </tr>
            )}

            {/* Data rows */}
            {!loading && hasData && data.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                onClick={clickable ? () => onRowClick(row) : undefined}
                className={[
                  'border-t border-border-subtle transition-colors',
                  clickable ? 'cursor-pointer hover:bg-bg-hover' : '',
                ].join(' ')}
              >
                {columns.map(col => {
                  const rawValue = (row as Record<string, unknown>)[col.key];
                  return (
                    <td key={col.key} className="px-4 py-3 text-text-primary">
                      {col.render
                        ? col.render(row)
                        : rawValue !== undefined && rawValue !== null
                        ? String(rawValue)
                        : <span className="text-text-muted">—</span>
                      }
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default DataTable;
