import { useState } from 'react'
import { Plus, Trash2, Loader2, ChevronDown, ChevronRight, Shield } from 'lucide-react'
import {
  usePersonas,
  useCreatePersona,
  useDeletePersona,
  usePermissions,
  useAddPermission,
  useRemovePermission,
  type PersonaOut,
} from '@/hooks/useDomainAdmin'

interface Props {
  domainId: string
}

const ALL_SCOPES = [
  'case:read', 'case:create', 'case:approve',
  'review:read', 'review:approve', 'review:escalate',
  'sales:review', 'sales:decide',
  'compliance:read', 'compliance:decide',
  'audit:read', 'audit:export',
  'document:upload', 'document:validate',
  'admin:config',
]

function PermissionsPanel({ domainId, personaCode }: { domainId: string; personaCode: string }) {
  const { data: permissions, isLoading } = usePermissions(domainId, personaCode)
  const addPerm = useAddPermission(domainId, personaCode)
  const removePerm = useRemovePermission(domainId, personaCode)

  const grantedScopes = new Set((permissions ?? []).map((p) => p.permission_scope))

  if (isLoading) return <div className="py-3 text-center"><Loader2 className="mx-auto h-4 w-4 animate-spin text-gray-400" /></div>

  return (
    <div className="border-t border-gray-100 px-4 py-4 dark:border-gray-700">
      <h5 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-gray-500">Permission Scopes</h5>
      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
        {ALL_SCOPES.map((scope) => {
          const granted = grantedScopes.has(scope)
          return (
            <label
              key={scope}
              className={[
                'flex cursor-pointer items-center gap-2 border px-2.5 py-1.5 text-[11px] transition-colors',
                granted
                  ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300'
                  : 'border-gray-200 text-gray-500 hover:border-gray-300 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-700',
              ].join(' ')}
            >
              <input
                type="checkbox"
                checked={granted}
                onChange={() => {
                  if (granted) {
                    removePerm.mutate(scope)
                  } else {
                    addPerm.mutate(scope)
                  }
                }}
                className="h-3 w-3 accent-blue-600"
              />
              <span className="font-mono">{scope}</span>
            </label>
          )
        })}
      </div>
    </div>
  )
}

export default function PersonasEditor({ domainId }: Props) {
  const { data: personas, isLoading } = usePersonas(domainId)
  const createPersona = useCreatePersona(domainId)
  const deletePersona = useDeletePersona(domainId)

  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({
    persona_code: '',
    display_label: '',
    color: '#6366f1',
    default_route: '/',
    nav_links: [] as unknown[],
  })
  const [expanded, setExpanded] = useState<string | null>(null)

  function handleAdd() {
    if (!form.persona_code.trim() || !form.display_label.trim()) return
    createPersona.mutate(form, {
      onSuccess: () => {
        setForm({ persona_code: '', display_label: '', color: '#6366f1', default_route: '/', nav_links: [] })
        setShowAdd(false)
      },
    })
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Personas &amp; Permissions</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Define role personas and assign permission scopes. Changes invalidate the server-side permission cache immediately.
        </p>
      </div>

      <div className="overflow-hidden border border-gray-200 dark:border-gray-700">
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-xs text-gray-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {(personas ?? []).length === 0 && (
              <p className="py-8 text-center text-xs text-gray-400">No personas defined.</p>
            )}
            {(personas ?? []).map((p) => (
              <div key={p.id}>
                <div className="flex items-center justify-between px-4 py-3">
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <button
                      onClick={() => setExpanded((e) => (e === p.persona_code ? null : p.persona_code))}
                      className="shrink-0 text-gray-400 hover:text-gray-600"
                    >
                      {expanded === p.persona_code
                        ? <ChevronDown className="h-4 w-4" />
                        : <ChevronRight className="h-4 w-4" />
                      }
                    </button>
                    <div
                      className="h-4 w-4 shrink-0 rounded-full"
                      style={{ backgroundColor: p.color }}
                      aria-hidden="true"
                    />
                    <div className="min-w-0">
                      <p className="font-mono text-xs font-medium text-gray-800 dark:text-gray-100">{p.persona_code}</p>
                      <p className="text-[11px] text-gray-500">{p.display_label} · <span className="text-gray-400">{p.default_route}</span></p>
                    </div>
                  </div>
                  <div className="ml-3 flex items-center gap-2">
                    <Shield className="h-4 w-4 text-gray-300" />
                    <button
                      onClick={() => deletePersona.mutate(p.id)}
                      disabled={deletePersona.isPending}
                      className="rounded p-1 text-gray-300 hover:bg-red-50 hover:text-red-500 disabled:opacity-30 dark:hover:bg-red-950"
                      aria-label="Delete persona"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                {expanded === p.persona_code && (
                  <PermissionsPanel domainId={domainId} personaCode={p.persona_code} />
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {showAdd ? (
        <div className="border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
          <p className="mb-3 text-xs font-semibold text-blue-700 dark:text-blue-300">New Persona</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Persona Code <span className="text-red-400">*</span></label>
              <input
                type="text"
                value={form.persona_code}
                onChange={(e) => setForm((p) => ({ ...p, persona_code: e.target.value.toLowerCase() }))}
                placeholder="e.g. compliance_officer"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 font-mono text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Display Label <span className="text-red-400">*</span></label>
              <input
                type="text"
                value={form.display_label}
                onChange={(e) => setForm((p) => ({ ...p, display_label: e.target.value }))}
                placeholder="e.g. Compliance Officer"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Color</label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={form.color}
                  onChange={(e) => setForm((p) => ({ ...p, color: e.target.value }))}
                  className="h-8 w-12 cursor-pointer border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
                />
                <span className="font-mono text-xs text-gray-500">{form.color}</span>
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Default Route</label>
              <input
                type="text"
                value={form.default_route}
                onChange={(e) => setForm((p) => ({ ...p, default_route: e.target.value }))}
                placeholder="/dashboard"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
          </div>
          {createPersona.isError && (
            <p className="mt-2 text-[11px] text-red-600 dark:text-red-400">Failed to create persona.</p>
          )}
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleAdd}
              disabled={!form.persona_code.trim() || !form.display_label.trim() || createPersona.isPending}
              className="flex items-center gap-1.5 bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-50"
            >
              {createPersona.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              Create Persona
            </button>
            <button
              onClick={() => setShowAdd(false)}
              className="bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 border border-dashed border-gray-300 px-4 py-2.5 text-xs font-medium text-gray-500 hover:border-primary hover:text-primary dark:border-gray-600 dark:text-gray-400"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Persona
        </button>
      )}
    </div>
  )
}
