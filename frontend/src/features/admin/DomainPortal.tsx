import { useState } from 'react'
import { Loader2, Plus, CheckCircle, XCircle, AlertTriangle, Power, PowerOff } from 'lucide-react'
import {
  useDomains,
  useCreateDomain,
  useValidateDomain,
  useActivateDomain,
  useDeactivateDomain,
  type DomainOut,
  type DomainValidationResult,
} from '@/hooks/useDomainAdmin'
import StagesEditor from './StagesEditor'
import AgentsEditor from './AgentsEditor'
import ProductsEditor from './ProductsEditor'
import SLAEditor from './SLAEditor'
import SLAHealthDashboard from './SLAHealthDashboard'
import PersonasEditor from './PersonasEditor'

const DOMAIN_TABS = [
  { id: 'stages', label: 'Stages' },
  { id: 'agents', label: 'Agents' },
  { id: 'products', label: 'Products' },
  { id: 'sla', label: 'SLA' },
  { id: 'sla-health', label: 'SLA Health' },
  { id: 'personas', label: 'Personas' },
] as const

type DomainTabId = (typeof DOMAIN_TABS)[number]['id']

function DomainBadge({ domain }: { domain: DomainOut }) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold ring-1',
        domain.is_active
          ? 'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:ring-emerald-800'
          : 'bg-gray-50 text-gray-500 ring-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:ring-gray-700',
      ].join(' ')}
    >
      {domain.is_active ? <CheckCircle className="h-2.5 w-2.5" /> : <XCircle className="h-2.5 w-2.5" />}
      {domain.is_active ? 'Active' : 'Inactive'}
    </span>
  )
}

function ValidationBanner({ result }: { result: DomainValidationResult }) {
  if (result.valid) {
    return (
      <div className="flex items-center gap-2 border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
        <CheckCircle className="h-3.5 w-3.5 shrink-0" />
        Domain definition is valid.
      </div>
    )
  }
  return (
    <div className="border border-red-200 bg-red-50 px-3 py-2 dark:border-red-800 dark:bg-red-950">
      <div className="mb-1 flex items-center gap-2 text-xs font-semibold text-red-700 dark:text-red-300">
        <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
        Validation failed ({result.errors.length} error{result.errors.length !== 1 ? 's' : ''})
      </div>
      <ul className="ml-5 list-disc space-y-0.5">
        {result.errors.map((e, i) => (
          <li key={i} className="text-[11px] text-red-600 dark:text-red-400">{e}</li>
        ))}
      </ul>
    </div>
  )
}

function DomainEditor({ domain }: { domain: DomainOut }) {
  const [activeTab, setActiveTab] = useState<DomainTabId>('stages')
  const [validation, setValidation] = useState<DomainValidationResult | null>(null)
  const validateDomain = useValidateDomain()
  const activateDomain = useActivateDomain()
  const deactivateDomain = useDeactivateDomain()

  function handleValidate() {
    setValidation(null)
    validateDomain.mutate(domain.id, {
      onSuccess: (result) => setValidation(result),
    })
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Domain lifecycle toolbar */}
      <div className="shrink-0 border-b border-gray-100 bg-gray-50 px-4 py-2.5 dark:border-gray-700 dark:bg-gray-800/50">
        <div className="flex flex-wrap items-center gap-2">
          <DomainBadge domain={domain} />
          <span className="text-[11px] text-gray-400 font-mono">{domain.domain_code}</span>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={handleValidate}
              disabled={validateDomain.isPending}
              className="flex items-center gap-1.5 border border-gray-200 bg-white px-2.5 py-1.5 text-[11px] font-medium text-gray-600 hover:border-blue-300 hover:text-blue-600 disabled:opacity-40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
            >
              {validateDomain.isPending
                ? <Loader2 className="h-3 w-3 animate-spin" />
                : <CheckCircle className="h-3 w-3" />
              }
              Validate
            </button>
            {domain.is_active ? (
              <button
                onClick={() => deactivateDomain.mutate(domain.id)}
                disabled={deactivateDomain.isPending}
                className="flex items-center gap-1.5 border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-[11px] font-medium text-amber-700 hover:bg-amber-100 disabled:opacity-40 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300"
              >
                {deactivateDomain.isPending
                  ? <Loader2 className="h-3 w-3 animate-spin" />
                  : <PowerOff className="h-3 w-3" />
                }
                Deactivate
              </button>
            ) : (
              <button
                onClick={() => activateDomain.mutate(domain.id)}
                disabled={activateDomain.isPending}
                className="flex items-center gap-1.5 border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-[11px] font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-40 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
              >
                {activateDomain.isPending
                  ? <Loader2 className="h-3 w-3 animate-spin" />
                  : <Power className="h-3 w-3" />
                }
                Activate
              </button>
            )}
          </div>
        </div>
        {validation && (
          <div className="mt-2">
            <ValidationBanner result={validation} />
          </div>
        )}
      </div>

      {/* Tab bar */}
      <div
        className="flex shrink-0 overflow-x-auto border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
        role="tablist"
      >
        {DOMAIN_TABS.map(({ id, label }) => (
          <button
            key={id}
            role="tab"
            aria-selected={activeTab === id}
            onClick={() => setActiveTab(id)}
            className={[
              'shrink-0 px-4 py-2.5 text-xs font-medium transition-colors',
              activeTab === id
                ? 'border-b-2 border-blue-600 text-blue-700 dark:text-blue-400'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
            ].join(' ')}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        {activeTab === 'stages' && <StagesEditor domainId={domain.id} />}
        {activeTab === 'agents' && <AgentsEditor domainId={domain.id} />}
        {activeTab === 'products' && <ProductsEditor domainId={domain.id} />}
        {activeTab === 'sla' && <SLAEditor domainId={domain.id} />}
        {activeTab === 'sla-health' && <SLAHealthDashboard domainCode={domain.domain_code} />}
        {activeTab === 'personas' && <PersonasEditor domainId={domain.id} />}
      </div>
    </div>
  )
}

export default function DomainPortal() {
  const { data: domains, isLoading } = useDomains()
  const createDomain = useCreateDomain()

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ domain_code: '', display_name: '' })

  const selectedDomain = (domains ?? []).find((d) => d.id === selectedId) ?? null

  function handleCreate() {
    if (!createForm.domain_code.trim() || !createForm.display_name.trim()) return
    createDomain.mutate(createForm, {
      onSuccess: (created) => {
        setSelectedId(created.id)
        setCreateForm({ domain_code: '', display_name: '' })
        setShowCreate(false)
      },
    })
  }

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center text-xs text-gray-400">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading domains…
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Domain selector strip */}
      <div className="shrink-0 border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Domain</span>
          <div className="flex flex-wrap gap-1.5">
            {(domains ?? []).map((d) => (
              <button
                key={d.id}
                onClick={() => setSelectedId(d.id)}
                className={[
                  'flex items-center gap-1.5 border px-3 py-1 text-xs font-medium transition-colors',
                  selectedId === d.id
                    ? 'border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-700',
                ].join(' ')}
              >
                <span
                  className={[
                    'h-1.5 w-1.5 rounded-full',
                    d.is_active ? 'bg-emerald-500' : 'bg-gray-300',
                  ].join(' ')}
                />
                {d.display_name}
              </button>
            ))}
          </div>

          {showCreate ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={createForm.domain_code}
                onChange={(e) => setCreateForm((p) => ({ ...p, domain_code: e.target.value.toLowerCase() }))}
                placeholder="domain_code"
                className="w-28 border border-gray-200 bg-white px-2 py-1 font-mono text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
              <input
                type="text"
                value={createForm.display_name}
                onChange={(e) => setCreateForm((p) => ({ ...p, display_name: e.target.value }))}
                placeholder="Display Name"
                className="w-32 border border-gray-200 bg-white px-2 py-1 text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
              <button
                onClick={handleCreate}
                disabled={!createForm.domain_code.trim() || !createForm.display_name.trim() || createDomain.isPending}
                className="flex items-center gap-1 bg-primary px-2.5 py-1 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-50"
              >
                {createDomain.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                Create
              </button>
              <button
                onClick={() => { setShowCreate(false); setCreateForm({ domain_code: '', display_name: '' }) }}
                className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-1 border border-dashed border-gray-300 px-2.5 py-1 text-xs text-gray-400 hover:border-primary hover:text-primary"
            >
              <Plus className="h-3 w-3" />
              New
            </button>
          )}
        </div>
      </div>

      {/* Main content area */}
      {selectedDomain ? (
        <DomainEditor key={selectedDomain.id} domain={selectedDomain} />
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 text-gray-400">
          <Power className="h-8 w-8 text-gray-200 dark:text-gray-700" />
          <p className="text-xs">Select a domain above to configure it.</p>
          {(domains ?? []).length === 0 && (
            <p className="text-[11px] text-gray-400">No domains yet — create one with the &quot;+ New&quot; button.</p>
          )}
        </div>
      )}
    </div>
  )
}
