import type { ReactNode } from 'react';

interface MetaItem {
  label: string;
  value: ReactNode;
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  chips?: ReactNode;
  meta?: MetaItem[];
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, chips, meta, actions }: PageHeaderProps) {
  return (
    <div className="pb-1 border-b border-border-default">
      {/* Row 1: title + actions */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          {/* Client name */}
          {subtitle && (
            <h2 className="mt-1 text-base font-semibold text-text-secondary leading-snug">
              {subtitle}
            </h2>
          )}

          {/* Chips row */}
          {chips && (
            <div className="flex items-center gap-2 flex-wrap mt-2">
              {chips}
            </div>
          )}

          {/* Meta info bar */}
          {meta && meta.length > 0 && (
            <div className="flex items-center flex-wrap gap-x-0 mt-3">
              {meta.map(({ label, value }, i) => (
                <div key={label} className="flex items-center">
                  {i > 0 && (
                    <span className="mx-3 text-border-default select-none text-text-muted">·</span>
                  )}
                  <span className="text-xs text-text-muted">{label}:</span>
                  <span className="ml-1.5 text-xs text-text-secondary font-medium">{value}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right-side actions (kept for other pages) */}
        {actions && (
          <div className="flex items-center gap-3 flex-shrink-0 mt-0.5">
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}

export default PageHeader;
