import { useState } from 'react'
import { Plus, Trash2, Loader2, ArrowRight, Pencil, Check, X } from 'lucide-react'
import {
  useStages,
  useCreateStage,
  useUpdateStage,
  useDeleteStage,
  useTransitions,
  useCreateTransition,
  useDeleteTransition,
  useTaskRouting,
  type StageOut,
} from '@/hooks/useDomainAdmin'

interface Props {
  domainId: string
}

function StageRow({
  s,
  routing,
  updateStage,
  deleteStage,
}: {
  s: StageOut
  routing?: { target_agent: string; task_type: string }
  updateStage: ReturnType<typeof useUpdateStage>
  deleteStage: ReturnType<typeof useDeleteStage>
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(s.display_name)

  function save() {
    if (!draft.trim() || draft === s.display_name) { setEditing(false); return }
    updateStage.mutate({ id: s.id, display_name: draft.trim() }, {
      onSuccess: () => setEditing(false),
    })
  }

  return (
    <tr className="hover:bg-gray-50 dark:hover:bg-gray-700">
      <td className="px-4 py-2.5 font-mono font-medium text-gray-800 dark:text-gray-100">
        {s.stage_code}
      </td>
      <td className="px-4 py-2.5 text-gray-700 dark:text-gray-300">
        {editing ? (
          <div className="flex items-center gap-1.5">
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(false) }}
              className="w-full border border-primary bg-white px-2 py-0.5 text-xs outline-none dark:bg-gray-800 dark:text-gray-200"
            />
            <button onClick={save} disabled={updateStage.isPending} className="text-emerald-600 hover:text-emerald-700 disabled:opacity-40">
              <Check className="h-3.5 w-3.5" />
            </button>
            <button onClick={() => { setDraft(s.display_name); setEditing(false) }} className="text-gray-400 hover:text-gray-600">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 group">
            <span>{s.display_name}</span>
            <button
              onClick={() => { setDraft(s.display_name); setEditing(true) }}
              className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-gray-500 transition-opacity"
              aria-label="Edit display name"
            >
              <Pencil className="h-3 w-3" />
            </button>
          </div>
        )}
      </td>
      <td className="px-4 py-2.5">
        <input
          type="checkbox"
          checked={s.is_terminal}
          onChange={(e) => updateStage.mutate({ id: s.id, is_terminal: e.target.checked })}
          className="h-3.5 w-3.5 accent-blue-600"
        />
      </td>
      <td className="px-4 py-2.5">
        <input
          type="checkbox"
          checked={s.is_human_pending}
          onChange={(e) => updateStage.mutate({ id: s.id, is_human_pending: e.target.checked })}
          className="h-3.5 w-3.5 accent-blue-600"
        />
      </td>
      <td className="px-4 py-2.5 text-[10px] text-gray-400">
        {routing ? (
          <span>{routing.target_agent} / {routing.task_type}</span>
        ) : (
          <span className="text-amber-500">No routing</span>
        )}
      </td>
      <td className="px-4 py-2.5">
        <button
          onClick={() => deleteStage.mutate(s.id)}
          disabled={deleteStage.isPending}
          className="rounded p-1 text-gray-300 hover:bg-red-50 hover:text-red-500 disabled:opacity-30 dark:hover:bg-red-950"
          aria-label="Delete stage"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </td>
    </tr>
  )
}

export default function StagesEditor({ domainId }: Props) {
  const { data: stages, isLoading: stagesLoading } = useStages(domainId)
  const { data: transitions, isLoading: transitionsLoading } = useTransitions(domainId)
  const { data: taskRouting } = useTaskRouting(domainId)
  const createStage = useCreateStage(domainId)
  const updateStage = useUpdateStage(domainId)
  const deleteStage = useDeleteStage(domainId)
  const createTransition = useCreateTransition(domainId)
  const deleteTransition = useDeleteTransition(domainId)

  const [showAddStage, setShowAddStage] = useState(false)
  const [stageForm, setStageForm] = useState({ stage_code: '', display_name: '', is_terminal: false, is_human_pending: false })
  const [showAddTransition, setShowAddTransition] = useState(false)
  const [transitionForm, setTransitionForm] = useState({ from_stage: '', to_stage: '' })

  const stageCodes = (stages ?? []).map((s) => s.stage_code)

  function handleAddStage() {
    if (!stageForm.stage_code.trim() || !stageForm.display_name.trim()) return
    createStage.mutate(stageForm, {
      onSuccess: () => {
        setStageForm({ stage_code: '', display_name: '', is_terminal: false, is_human_pending: false })
        setShowAddStage(false)
      },
    })
  }

  function handleAddTransition() {
    if (!transitionForm.from_stage || !transitionForm.to_stage) return
    createTransition.mutate(transitionForm, {
      onSuccess: () => {
        setTransitionForm({ from_stage: '', to_stage: '' })
        setShowAddTransition(false)
      },
    })
  }

  const isLoading = stagesLoading || transitionsLoading

  return (
    <div className="space-y-8">
      {/* ── Stages ──────────────────────────────────────────────────────────── */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Stages</h3>
            <p className="mt-0.5 text-xs text-gray-500">FSM nodes — define the onboarding lifecycle states. Hover a name to edit it.</p>
          </div>
        </div>

        <div className="overflow-hidden border border-gray-200 dark:border-gray-700">
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-xs text-gray-400">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…
            </div>
          ) : (
            <>
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full min-w-[500px] text-xs">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      {['Code', 'Display Name', 'Terminal', 'Human Pending', 'Routing', ''].map((h) => (
                        <th key={h} className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {(stages ?? []).map((s) => (
                      <StageRow
                        key={s.id}
                        s={s}
                        routing={(taskRouting ?? []).find((r) => r.stage_code === s.stage_code)}
                        updateStage={updateStage}
                        deleteStage={deleteStage}
                      />
                    ))}
                    {(stages ?? []).length === 0 && (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-xs text-gray-400">
                          No stages defined. Add the first stage below.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Mobile cards */}
              <div className="divide-y divide-gray-100 md:hidden dark:divide-gray-700">
                {(stages ?? []).map((s) => (
                  <div key={s.id} className="flex items-center justify-between p-3">
                    <div>
                      <p className="font-mono text-xs font-medium text-gray-800 dark:text-gray-100">{s.stage_code}</p>
                      <p className="text-[11px] text-gray-500">{s.display_name}</p>
                      <div className="mt-1 flex gap-2 text-[10px] text-gray-400">
                        {s.is_terminal && <span className="text-emerald-600">Terminal</span>}
                        {s.is_human_pending && <span className="text-amber-600">Human pending</span>}
                      </div>
                    </div>
                    <button
                      onClick={() => deleteStage.mutate(s.id)}
                      className="rounded p-1 text-gray-300 hover:text-red-500"
                      aria-label="Delete stage"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {showAddStage ? (
          <div className="mt-3 border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
            <p className="mb-3 text-xs font-semibold text-blue-700 dark:text-blue-300">New Stage</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Stage Code <span className="text-red-400">*</span></label>
                <input
                  type="text"
                  value={stageForm.stage_code}
                  onChange={(e) => setStageForm((p) => ({ ...p, stage_code: e.target.value.toUpperCase() }))}
                  placeholder="e.g. KYC"
                  className="w-full border border-gray-200 bg-white px-2.5 py-1.5 font-mono text-xs text-gray-700 outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Display Name <span className="text-red-400">*</span></label>
                <input
                  type="text"
                  value={stageForm.display_name}
                  onChange={(e) => setStageForm((p) => ({ ...p, display_name: e.target.value }))}
                  placeholder="e.g. KYC Verification"
                  className="w-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                />
              </div>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                  <input
                    type="checkbox"
                    checked={stageForm.is_terminal}
                    onChange={(e) => setStageForm((p) => ({ ...p, is_terminal: e.target.checked }))}
                    className="h-3.5 w-3.5 accent-blue-600"
                  />
                  Terminal stage
                </label>
                <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                  <input
                    type="checkbox"
                    checked={stageForm.is_human_pending}
                    onChange={(e) => setStageForm((p) => ({ ...p, is_human_pending: e.target.checked }))}
                    className="h-3.5 w-3.5 accent-blue-600"
                  />
                  Human pending
                </label>
              </div>
            </div>
            {createStage.isError && (
              <p className="mt-2 text-[11px] text-red-600 dark:text-red-400">Failed to create stage. Please try again.</p>
            )}
            <div className="mt-3 flex gap-2">
              <button
                onClick={handleAddStage}
                disabled={!stageForm.stage_code.trim() || !stageForm.display_name.trim() || createStage.isPending}
                className="flex items-center gap-1.5 bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-50"
              >
                {createStage.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                Add Stage
              </button>
              <button
                onClick={() => setShowAddStage(false)}
                className="bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowAddStage(true)}
            className="mt-3 flex items-center gap-2 border border-dashed border-gray-300 px-4 py-2.5 text-xs font-medium text-gray-500 hover:border-primary hover:text-primary dark:border-gray-600 dark:text-gray-400"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Stage
          </button>
        )}
      </section>

      {/* ── Transitions ─────────────────────────────────────────────────────── */}
      <section>
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Transitions</h3>
          <p className="mt-0.5 text-xs text-gray-500">Valid FSM edges — define which stage advances to which.</p>
        </div>

        <div className="overflow-hidden border border-gray-200 dark:border-gray-700">
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {(transitions ?? []).length === 0 && (
              <p className="py-6 text-center text-xs text-gray-400">No transitions defined.</p>
            )}
            {(transitions ?? []).map((t) => (
              <div key={t.id} className="flex items-center justify-between px-4 py-2.5">
                <div className="flex items-center gap-2 font-mono text-xs text-gray-700 dark:text-gray-300">
                  <span className="text-gray-800 dark:text-gray-100">{t.from_stage}</span>
                  <ArrowRight className="h-3 w-3 text-gray-400" />
                  <span className="text-gray-800 dark:text-gray-100">{t.to_stage}</span>
                </div>
                <button
                  onClick={() => deleteTransition.mutate(t.id)}
                  disabled={deleteTransition.isPending}
                  className="rounded p-1 text-gray-300 hover:bg-red-50 hover:text-red-500 disabled:opacity-30 dark:hover:bg-red-950"
                  aria-label="Delete transition"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {showAddTransition ? (
          <div className="mt-3 border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
            <p className="mb-3 text-xs font-semibold text-blue-700 dark:text-blue-300">New Transition</p>
            <div className="flex flex-wrap items-end gap-3">
              <div className="space-y-1">
                <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">From</label>
                <select
                  value={transitionForm.from_stage}
                  onChange={(e) => setTransitionForm((p) => ({ ...p, from_stage: e.target.value }))}
                  className="border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                >
                  <option value="">Select stage…</option>
                  {stageCodes.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <ArrowRight className="mb-1.5 h-4 w-4 text-gray-400" />
              <div className="space-y-1">
                <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">To</label>
                <select
                  value={transitionForm.to_stage}
                  onChange={(e) => setTransitionForm((p) => ({ ...p, to_stage: e.target.value }))}
                  className="border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                >
                  <option value="">Select stage…</option>
                  {stageCodes.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
            {createTransition.isError && (
              <p className="mt-2 text-[11px] text-red-600 dark:text-red-400">Failed to create transition.</p>
            )}
            <div className="mt-3 flex gap-2">
              <button
                onClick={handleAddTransition}
                disabled={!transitionForm.from_stage || !transitionForm.to_stage || createTransition.isPending}
                className="flex items-center gap-1.5 bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-50"
              >
                {createTransition.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                Add Transition
              </button>
              <button
                onClick={() => setShowAddTransition(false)}
                className="bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowAddTransition(true)}
            className="mt-3 flex items-center gap-2 border border-dashed border-gray-300 px-4 py-2.5 text-xs font-medium text-gray-500 hover:border-primary hover:text-primary dark:border-gray-600 dark:text-gray-400"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Transition
          </button>
        )}
      </section>
    </div>
  )
}
