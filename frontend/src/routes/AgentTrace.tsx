import { useState, useEffect, useRef, useMemo } from 'react'
import { ChevronDown } from 'lucide-react'
import AgentTraceCanvas from '@/features/agent-trace/AgentTraceCanvas'
import { useCases } from '@/hooks/useDocuments'

interface TraceSelectProps {
  options: { id: string; label: string }[]
  value: string | null
  onChange: (id: string | null) => void
}

function TraceSelect({ options, value, onChange }: TraceSelectProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const active = options.find((o) => o.id === value)

  useEffect(() => {
    function onOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onOutside)
    return () => document.removeEventListener('mousedown', onOutside)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex max-w-[180px] items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 transition-colors hover:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400 sm:max-w-xs dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
      >
        <span className="truncate">{active?.label ?? 'Select a case…'}</span>
        <ChevronDown
          className={[
            'h-4 w-4 shrink-0 text-gray-400 transition-transform duration-200',
            open ? 'rotate-180' : '',
          ].join(' ')}
        />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 max-h-64 w-72 overflow-y-auto rounded-xl border border-gray-200 bg-white py-1 shadow-xl dark:border-gray-700 dark:bg-gray-800">
          {options.map((o) => (
            <button
              key={o.id}
              onClick={() => { onChange(o.id); setOpen(false) }}
              className={[
                'w-full px-4 py-2.5 text-left text-sm transition-colors',
                o.id === value
                  ? 'bg-blue-50 font-semibold text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                  : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700',
              ].join(' ')}
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function AgentTrace() {
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null)
  const { data: cases } = useCases()

  useEffect(() => {
    if (cases && cases.length > 0 && !activeCaseId) {
      setActiveCaseId(cases[0].id)
    }
  }, [cases, activeCaseId])

  const caseOptions = useMemo(
    () =>
      (cases ?? []).map((c) => {
        let label: string
        if (c.case_name) {
          label = c.case_name
        } else if (c.selected_products.length > 0) {
          label = c.selected_products
            .map((p) => p.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()))
            .join(' & ')
        } else {
          label = c.client_name ?? c.id.slice(0, 8)
        }
        return { id: c.id, label: `${label} — ${c.current_stage}` }
      }),
    [cases],
  )

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4 py-3 sm:px-6 dark:border-gray-700 dark:bg-gray-800">
        <div>
          <h1 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Agent Trace Canvas</h1>
          <p className="hidden text-[11px] text-gray-400 sm:block">
            Live A2A message flow · 8 agent nodes · Real-time state machine
          </p>
        </div>

        {caseOptions.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="hidden text-xs text-gray-400 sm:block">Trace case:</span>
            <TraceSelect
              options={caseOptions}
              value={activeCaseId}
              onChange={setActiveCaseId}
            />
          </div>
        )}
      </div>

      {/* Canvas */}
      <div className="flex-1 overflow-hidden">
        <AgentTraceCanvas activeCaseId={activeCaseId} />
      </div>
    </div>
  )
}
