import { useState } from 'react'
import { Plus, Trash2, RotateCcw, Shield, Loader2 } from 'lucide-react'
import {
  useCheckpointRules,
  useCreateCheckpointRule,
  useDeleteCheckpointRule,
  useResetCheckpointRules,
} from '@/hooks/useCheckpointRules'
import type { CreateCheckpointRuleRequest } from '@/lib/api'

const ACTION_COLORS: Record<string, string> = {
  ESCALATE: 'bg-red-50 text-red-700 ring-red-200 dark:bg-red-950 dark:text-red-300 dark:ring-red-800',
  ENHANCED_DD: 'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:ring-amber-800',
  REQUIRE_DOCUMENTS: 'bg-blue-50 text-blue-700 ring-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:ring-blue-800',
}

const ACTION_LABEL: Record<string, string> = {
  ESCALATE: 'Escalate',
  ENHANCED_DD: 'Enhanced DD',
  REQUIRE_DOCUMENTS: 'Require Docs',
}

const RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
const ACCOUNT_BANDS = ['NORMAL', 'LARGE']
const ACTIONS = ['ESCALATE', 'ENHANCED_DD', 'REQUIRE_DOCUMENTS'] as const

const EMPTY_FORM: CreateCheckpointRuleRequest = {
  description: '',
  product_type: null,
  risk_level: null,
  account_value_band: null,
  jurisdiction: null,
  action: 'ESCALATE',
  required_documents: [],
  reason_template: '',
}

function DimChip({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <span className={['rounded px-1.5 py-0.5 text-[10px] font-medium', color].join(' ')}>
      {label}: {value}
    </span>
  )
}

export default function CheckpointRulesEditor() {
  const { data: rules, isLoading } = useCheckpointRules()
  const createRule = useCreateCheckpointRule()
  const deleteRule = useDeleteCheckpointRule()
  const resetRules = useResetCheckpointRules()

  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState<CreateCheckpointRuleRequest>(EMPTY_FORM)
  const [docsInput, setDocsInput] = useState('')

  function handleAdd() {
    if (!form.description.trim()) return
    const docs = docsInput.split(',').map((s) => s.trim()).filter(Boolean)
    createRule.mutate(
      { ...form, required_documents: docs },
      {
        onSuccess: () => {
          setForm(EMPTY_FORM)
          setDocsInput('')
          setShowAdd(false)
        },
      },
    )
  }

  function handleDelete(ruleId: string) {
    deleteRule.mutate(ruleId)
  }

  function handleReset() {
    if (!window.confirm('Reset all rules to built-in defaults?')) return
    resetRules.mutate()
  }

  const ruleList = rules ?? []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Checkpoint Rules</h3>
          <p className="mt-0.5 text-xs text-gray-500">
            Rules evaluated across 4 dimensions during KYC. Built-in rules cannot be deleted.
          </p>
        </div>
        <button
          onClick={handleReset}
          disabled={resetRules.isPending}
          className="flex shrink-0 items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          {resetRules.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RotateCcw className="h-3.5 w-3.5" />
          )}
          Reset to defaults
        </button>
      </div>

      {/* Rules list */}
      <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700">
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-xs text-gray-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading rules…
          </div>
        ) : (
          <>
            {/* ── Mobile: card per rule (< md) ─────────────────────────────── */}
            <div className="divide-y divide-gray-100 md:hidden dark:divide-gray-700">
              {ruleList.length === 0 && (
                <p className="py-8 text-center text-xs text-gray-400">No rules defined.</p>
              )}
              {ruleList.map((rule) => (
                <div key={rule.rule_id} className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium leading-snug text-gray-800 dark:text-gray-100">
                        {rule.description}
                      </p>
                      {rule.required_documents.length > 0 && (
                        <p className="mt-1 text-[10px] text-gray-400">
                          Docs: {rule.required_documents.join(', ')}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => handleDelete(rule.rule_id)}
                      disabled={rule.is_builtin || deleteRule.isPending}
                      className="shrink-0 rounded p-1 text-gray-300 hover:bg-red-50 hover:text-red-500 disabled:cursor-not-allowed disabled:opacity-30 dark:hover:bg-red-950"
                      aria-label="Delete rule"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  <div className="mt-2.5 flex flex-wrap items-center gap-2">
                    <span
                      className={[
                        'rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1',
                        ACTION_COLORS[rule.action] ?? 'bg-gray-50 text-gray-600 ring-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:ring-gray-700',
                      ].join(' ')}
                    >
                      {ACTION_LABEL[rule.action] ?? rule.action}
                    </span>
                    {rule.is_builtin ? (
                      <span className="flex items-center gap-1 text-[10px] text-gray-400">
                        <Shield className="h-3 w-3" /> Built-in
                      </span>
                    ) : (
                      <span className="text-[10px] text-indigo-600 dark:text-indigo-400">Custom</span>
                    )}
                  </div>

                  {(rule.risk_level || rule.product_type || rule.account_value_band || rule.jurisdiction) ? (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {rule.risk_level && (
                        <DimChip label="Risk" value={rule.risk_level} color="text-red-600 bg-red-50 dark:bg-red-950 dark:text-red-400" />
                      )}
                      {rule.product_type && (
                        <DimChip label="Product" value={rule.product_type} color="text-purple-600 bg-purple-50 dark:bg-purple-950 dark:text-purple-400" />
                      )}
                      {rule.account_value_band && (
                        <DimChip label="Band" value={rule.account_value_band} color="text-blue-600 bg-blue-50 dark:bg-blue-950 dark:text-blue-400" />
                      )}
                      {rule.jurisdiction && (
                        <DimChip label="Juris." value={rule.jurisdiction} color="text-teal-600 bg-teal-50 dark:bg-teal-950 dark:text-teal-400" />
                      )}
                    </div>
                  ) : (
                    <p className="mt-1.5 text-[10px] text-gray-400">All dimensions: Any</p>
                  )}
                </div>
              ))}
            </div>

            {/* ── Desktop: scrollable table (md+) ──────────────────────────── */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[600px] text-xs">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      Description
                    </th>
                    <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      Action
                    </th>
                    <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      Dimensions
                    </th>
                    <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      Source
                    </th>
                    <th className="w-10 px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {ruleList.map((rule) => (
                    <tr key={rule.rule_id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                      <td className="max-w-xs px-4 py-3">
                        <p className="font-medium text-gray-800 dark:text-gray-100">{rule.description}</p>
                        {rule.required_documents.length > 0 && (
                          <p className="mt-0.5 text-[10px] text-gray-400">
                            Docs: {rule.required_documents.join(', ')}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={[
                            'rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1',
                            ACTION_COLORS[rule.action] ?? 'bg-gray-50 text-gray-600 ring-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:ring-gray-700',
                          ].join(' ')}
                        >
                          {ACTION_LABEL[rule.action] ?? rule.action}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {rule.risk_level && (
                            <DimChip label="Risk" value={rule.risk_level} color="text-red-600 bg-red-50 dark:bg-red-950 dark:text-red-400" />
                          )}
                          {rule.product_type && (
                            <DimChip label="Product" value={rule.product_type} color="text-purple-600 bg-purple-50 dark:bg-purple-950 dark:text-purple-400" />
                          )}
                          {rule.account_value_band && (
                            <DimChip label="Band" value={rule.account_value_band} color="text-blue-600 bg-blue-50 dark:bg-blue-950 dark:text-blue-400" />
                          )}
                          {rule.jurisdiction && (
                            <DimChip label="Juris." value={rule.jurisdiction} color="text-teal-600 bg-teal-50 dark:bg-teal-950 dark:text-teal-400" />
                          )}
                          {!rule.risk_level && !rule.product_type && !rule.account_value_band && !rule.jurisdiction && (
                            <span className="text-[10px] text-gray-400">Any</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {rule.is_builtin ? (
                          <span className="flex items-center gap-1 text-[10px] text-gray-400">
                            <Shield className="h-3 w-3" /> Built-in
                          </span>
                        ) : (
                          <span className="text-[10px] text-indigo-600 dark:text-indigo-400">Custom</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleDelete(rule.rule_id)}
                          disabled={rule.is_builtin || deleteRule.isPending}
                          className="rounded p-1 text-gray-300 hover:bg-red-50 hover:text-red-500 disabled:cursor-not-allowed disabled:opacity-30 dark:hover:bg-red-950"
                          aria-label="Delete rule"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Add rule form */}
      {showAdd ? (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
          <p className="mb-3 text-xs font-semibold text-blue-700 dark:text-blue-300">New Checkpoint Rule</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="col-span-1 space-y-1 sm:col-span-2">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">
                Description <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={form.description}
                onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                placeholder="Short explanation of when this rule triggers"
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none focus:border-blue-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Action</label>
              <select
                value={form.action}
                onChange={(e) =>
                  setForm((p) => ({
                    ...p,
                    action: e.target.value as CreateCheckpointRuleRequest['action'],
                  }))
                }
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              >
                {ACTIONS.map((a) => (
                  <option key={a} value={a}>{ACTION_LABEL[a]}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Risk Level</label>
              <select
                value={form.risk_level ?? ''}
                onChange={(e) => setForm((p) => ({ ...p, risk_level: e.target.value || null }))}
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              >
                <option value="">Any</option>
                {RISK_LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Product Type</label>
              <input
                type="text"
                value={form.product_type ?? ''}
                onChange={(e) => setForm((p) => ({ ...p, product_type: e.target.value || null }))}
                placeholder="e.g. cash_account"
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none focus:border-blue-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Account Value Band</label>
              <select
                value={form.account_value_band ?? ''}
                onChange={(e) =>
                  setForm((p) => ({ ...p, account_value_band: e.target.value || null }))
                }
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              >
                <option value="">Any</option>
                {ACCOUNT_BANDS.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Jurisdiction</label>
              <input
                type="text"
                value={form.jurisdiction ?? ''}
                onChange={(e) =>
                  setForm((p) => ({ ...p, jurisdiction: e.target.value || null }))
                }
                placeholder="e.g. iran"
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none focus:border-blue-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>

            <div className="col-span-1 space-y-1 sm:col-span-2">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">
                Required Documents{' '}
                <span className="text-gray-400">(comma-separated)</span>
              </label>
              <input
                type="text"
                value={docsInput}
                onChange={(e) => setDocsInput(e.target.value)}
                placeholder="e.g. source_of_wealth_declaration, bank_statement"
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none focus:border-blue-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
          </div>

          {createRule.isError && (
            <p className="mt-2 text-[11px] text-red-600 dark:text-red-400">
              Failed to create rule. Please try again.
            </p>
          )}

          <div className="mt-3 flex gap-2">
            <button
              onClick={handleAdd}
              disabled={!form.description.trim() || createRule.isPending}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {createRule.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              Add Rule
            </button>
            <button
              onClick={() => { setShowAdd(false); setForm(EMPTY_FORM); setDocsInput('') }}
              className="rounded-lg bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 rounded-lg border border-dashed border-gray-300 px-4 py-2.5 text-xs font-medium text-gray-500 hover:border-blue-400 hover:text-blue-600 dark:border-gray-600 dark:text-gray-400 dark:hover:border-blue-500 dark:hover:text-blue-400"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Checkpoint Rule
        </button>
      )}
    </div>
  )
}
