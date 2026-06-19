import { useState } from 'react'
import { Plus, Trash2, Loader2, AlertTriangle, Pencil, Check, X } from 'lucide-react'
import { useSLAs, useCreateSLA, useUpdateSLA, useDeleteSLA, type SLAOut } from '@/hooks/useDomainAdmin'

interface Props {
  domainId: string
}

const REGULATED_STAGES = new Set(['KYC', 'REVIEW', 'SALES_REVIEW', 'ESCALATED'])

const EMPTY_FORM: Omit<SLAOut, 'id' | 'domain_id'> = {
  stage_code: '',
  priority_tier: null,
  product_code: null,
  is_enabled: true,
  window_hours: 24,
  warning_pct: 80,
  escalation_pct: 100,
  warning_task_type: 'SEND_SLA_WARNING',
  escalation_task_type: 'SEND_ESCALATION_ALERT',
  escalation_target_agent: 'orchestrator',
  pause_on_human_review: false,
}

function SLAEditPanel({
  sla,
  domainId,
  onClose,
}: {
  sla: SLAOut
  domainId: string
  onClose: () => void
}) {
  const updateSLA = useUpdateSLA(domainId)
  const [draft, setDraft] = useState({
    window_hours: sla.window_hours,
    warning_pct: sla.warning_pct,
    escalation_pct: sla.escalation_pct,
    is_enabled: sla.is_enabled,
    pause_on_human_review: sla.pause_on_human_review,
    warning_task_type: sla.warning_task_type,
    escalation_task_type: sla.escalation_task_type,
    escalation_target_agent: sla.escalation_target_agent,
  })

  const invalid = draft.warning_pct >= draft.escalation_pct

  function save() {
    if (invalid) return
    updateSLA.mutate({ id: sla.id, ...draft }, { onSuccess: onClose })
  }

  return (
    <tr>
      <td colSpan={6} className="border-t border-blue-100 bg-blue-50 px-4 py-4 dark:border-blue-900 dark:bg-blue-950">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Window (hours)</label>
            <input
              type="number"
              value={draft.window_hours}
              onChange={(e) => setDraft((d) => ({ ...d, window_hours: parseFloat(e.target.value) || 0 }))}
              min="0.01" step="0.5"
              className="w-full border border-gray-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Warning %</label>
            <input
              type="number"
              value={draft.warning_pct}
              onChange={(e) => setDraft((d) => ({ ...d, warning_pct: parseInt(e.target.value, 10) || 80 }))}
              min="1" max="99"
              className="w-full border border-gray-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Escalation %</label>
            <input
              type="number"
              value={draft.escalation_pct}
              onChange={(e) => setDraft((d) => ({ ...d, escalation_pct: parseInt(e.target.value, 10) || 100 }))}
              min="2"
              className="w-full border border-gray-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Escalation Target Agent</label>
            <input
              type="text"
              value={draft.escalation_target_agent}
              onChange={(e) => setDraft((d) => ({ ...d, escalation_target_agent: e.target.value }))}
              placeholder="orchestrator"
              className="w-full border border-gray-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Warning Task Type</label>
            <input
              type="text"
              value={draft.warning_task_type}
              onChange={(e) => setDraft((d) => ({ ...d, warning_task_type: e.target.value }))}
              className="w-full border border-gray-200 bg-white px-2 py-1.5 font-mono text-[11px] outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Escalation Task Type</label>
            <input
              type="text"
              value={draft.escalation_task_type}
              onChange={(e) => setDraft((d) => ({ ...d, escalation_task_type: e.target.value }))}
              className="w-full border border-gray-200 bg-white px-2 py-1.5 font-mono text-[11px] outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            />
          </div>
          <div className="col-span-2 flex items-center gap-4">
            <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
              <input
                type="checkbox"
                checked={draft.is_enabled}
                onChange={(e) => setDraft((d) => ({ ...d, is_enabled: e.target.checked }))}
                className="h-3.5 w-3.5 accent-blue-600"
              />
              Enabled
            </label>
            <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
              <input
                type="checkbox"
                checked={draft.pause_on_human_review}
                onChange={(e) => setDraft((d) => ({ ...d, pause_on_human_review: e.target.checked }))}
                className="h-3.5 w-3.5 accent-blue-600"
              />
              Pause on human review
            </label>
          </div>
        </div>
        {invalid && (
          <p className="mt-2 text-[11px] text-red-600 dark:text-red-400">Warning % must be less than Escalation %.</p>
        )}
        <div className="mt-3 flex gap-2">
          <button
            onClick={save}
            disabled={invalid || updateSLA.isPending}
            className="flex items-center gap-1.5 bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-50"
          >
            {updateSLA.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
            Save
          </button>
          <button onClick={onClose} className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700">
            <X className="mr-1 inline h-3 w-3" />Cancel
          </button>
        </div>
      </td>
    </tr>
  )
}

function SLARow({
  sla,
  domainId,
  isEditing,
  onEditToggle,
}: {
  sla: SLAOut
  domainId: string
  isEditing: boolean
  onEditToggle: () => void
}) {
  const updateSLA = useUpdateSLA(domainId)
  const deleteSLA = useDeleteSLA(domainId)
  const isRegulated = REGULATED_STAGES.has(sla.stage_code)

  function handleToggle() {
    if (!sla.is_enabled && isRegulated) return
    if (sla.is_enabled && isRegulated) {
      if (!window.confirm(`Disabling SLA on regulated stage '${sla.stage_code}' is a compliance risk. Continue?`)) return
    }
    updateSLA.mutate({ id: sla.id, is_enabled: !sla.is_enabled })
  }

  return (
    <>
      <tr className={['hover:bg-gray-50 dark:hover:bg-gray-700', isEditing ? 'bg-blue-50/40 dark:bg-blue-950/30' : ''].join(' ')}>
        <td className="px-4 py-2.5">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-xs font-medium text-gray-800 dark:text-gray-100">{sla.stage_code}</span>
            {isRegulated && (
              <span className="text-[9px] text-amber-600 dark:text-amber-400" title="Regulated stage — disable with caution">●</span>
            )}
          </div>
          {sla.priority_tier && <span className="text-[10px] text-purple-600 dark:text-purple-400">tier:{sla.priority_tier}</span>}
          {sla.product_code && <span className="text-[10px] text-blue-600 dark:text-blue-400"> prod:{sla.product_code}</span>}
        </td>
        <td className="px-4 py-2.5">
          <button
            onClick={handleToggle}
            disabled={updateSLA.isPending}
            className={[
              'px-2 py-0.5 text-[10px] font-semibold ring-1 transition-colors',
              sla.is_enabled
                ? 'bg-emerald-50 text-emerald-700 ring-emerald-200 hover:bg-emerald-100 dark:bg-emerald-950 dark:text-emerald-300 dark:ring-emerald-800'
                : 'bg-gray-50 text-gray-400 ring-gray-200 hover:bg-gray-100 dark:bg-gray-800 dark:ring-gray-700',
            ].join(' ')}
          >
            {sla.is_enabled ? 'Enabled' : 'Disabled'}
          </button>
        </td>
        <td className="px-4 py-2.5 text-xs text-gray-700 dark:text-gray-300">{sla.window_hours}h</td>
        <td className="px-4 py-2.5">
          <span className="text-[11px] text-amber-600 dark:text-amber-400">{sla.warning_pct}%</span>
          {' / '}
          <span className="text-[11px] text-red-600 dark:text-red-400">{sla.escalation_pct}%</span>
        </td>
        <td className="px-4 py-2.5">
          <span className={['text-[10px]', sla.pause_on_human_review ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400'].join(' ')}>
            {sla.pause_on_human_review ? 'Pauses' : '—'}
          </span>
        </td>
        <td className="px-4 py-2.5">
          <div className="flex items-center gap-1">
            <button
              onClick={onEditToggle}
              className={[
                'rounded p-1 transition-colors',
                isEditing
                  ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400'
                  : 'text-gray-300 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700',
              ].join(' ')}
              aria-label="Edit SLA row"
            >
              <Pencil className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => deleteSLA.mutate(sla.id)}
              disabled={deleteSLA.isPending}
              className="rounded p-1 text-gray-300 hover:bg-red-50 hover:text-red-500 disabled:opacity-30 dark:hover:bg-red-950"
              aria-label="Delete SLA row"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </td>
      </tr>
      {isEditing && <SLAEditPanel sla={sla} domainId={domainId} onClose={onEditToggle} />}
    </>
  )
}

export default function SLAEditor({ domainId }: Props) {
  const { data: slas, isLoading } = useSLAs(domainId)
  const createSLA = useCreateSLA(domainId)

  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState<Omit<SLAOut, 'id' | 'domain_id'>>(EMPTY_FORM)
  const [editingId, setEditingId] = useState<string | null>(null)

  function handleAdd() {
    if (!form.stage_code.trim()) return
    if (form.warning_pct >= form.escalation_pct) {
      alert('Warning % must be less than Escalation %')
      return
    }
    createSLA.mutate(form, {
      onSuccess: () => {
        setForm(EMPTY_FORM)
        setShowAdd(false)
      },
    })
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">SLA Configuration</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Multi-axis SLA rules: domain default, priority-tier override, product-specific override. Each row is tried from most-specific to least.
        </p>
      </div>

      <div className="overflow-hidden border border-gray-200 dark:border-gray-700">
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-xs text-gray-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] text-xs">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  {['Stage / Tier / Product', 'Status', 'Window', 'Warn / Escalate', 'Clock Pause', ''].map((h) => (
                    <th key={h} className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {(slas ?? []).length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-xs text-gray-400">No SLA rows. Add the first below.</td>
                  </tr>
                )}
                {(slas ?? []).map((sla) => (
                  <SLARow
                    key={sla.id}
                    sla={sla}
                    domainId={domainId}
                    isEditing={editingId === sla.id}
                    onEditToggle={() => setEditingId((id) => id === sla.id ? null : sla.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showAdd ? (
        <div className="border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
          <p className="mb-3 text-xs font-semibold text-blue-700 dark:text-blue-300">New SLA Row</p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Stage Code <span className="text-red-400">*</span></label>
              <input
                type="text"
                value={form.stage_code}
                onChange={(e) => setForm((p) => ({ ...p, stage_code: e.target.value.toUpperCase() }))}
                placeholder="e.g. KYC"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 font-mono text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
              {REGULATED_STAGES.has(form.stage_code) && (
                <p className="flex items-center gap-1 text-[10px] text-amber-600"><AlertTriangle className="h-3 w-3" /> Regulated stage</p>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Priority Tier <span className="text-gray-400">(optional)</span></label>
              <input
                type="text"
                value={form.priority_tier ?? ''}
                onChange={(e) => setForm((p) => ({ ...p, priority_tier: e.target.value || null }))}
                placeholder="e.g. sme"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Product Code <span className="text-gray-400">(optional)</span></label>
              <input
                type="text"
                value={form.product_code ?? ''}
                onChange={(e) => setForm((p) => ({ ...p, product_code: e.target.value || null }))}
                placeholder="e.g. equity_fund"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Window (hours)</label>
              <input
                type="number"
                value={form.window_hours}
                onChange={(e) => setForm((p) => ({ ...p, window_hours: parseFloat(e.target.value) || 0 }))}
                min="0.01" step="0.5"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Warning %</label>
              <input
                type="number"
                value={form.warning_pct}
                onChange={(e) => setForm((p) => ({ ...p, warning_pct: parseInt(e.target.value, 10) || 80 }))}
                min="1" max="99"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Escalation %</label>
              <input
                type="number"
                value={form.escalation_pct}
                onChange={(e) => setForm((p) => ({ ...p, escalation_pct: parseInt(e.target.value, 10) || 100 }))}
                min="2"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="col-span-2 flex items-center gap-4 sm:col-span-3">
              <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                <input type="checkbox" checked={form.is_enabled} onChange={(e) => setForm((p) => ({ ...p, is_enabled: e.target.checked }))} className="h-3.5 w-3.5 accent-blue-600" />
                Enabled
              </label>
              <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                <input type="checkbox" checked={form.pause_on_human_review} onChange={(e) => setForm((p) => ({ ...p, pause_on_human_review: e.target.checked }))} className="h-3.5 w-3.5 accent-blue-600" />
                Pause on human review
              </label>
            </div>
          </div>
          {form.warning_pct >= form.escalation_pct && (
            <p className="mt-2 text-[11px] text-red-600 dark:text-red-400">Warning % must be less than Escalation %.</p>
          )}
          {createSLA.isError && (
            <p className="mt-2 text-[11px] text-red-600 dark:text-red-400">Failed to create SLA row.</p>
          )}
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleAdd}
              disabled={!form.stage_code.trim() || form.warning_pct >= form.escalation_pct || createSLA.isPending}
              className="flex items-center gap-1.5 bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-50"
            >
              {createSLA.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              Add SLA Row
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
          Add SLA Row
        </button>
      )}
    </div>
  )
}
