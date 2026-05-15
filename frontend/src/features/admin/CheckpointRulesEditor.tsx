import { useState } from 'react'
import { Plus, Trash2, Info } from 'lucide-react'

interface CheckpointRule {
  id: string
  dimension: 'product_type' | 'risk_level' | 'account_value_band' | 'jurisdiction'
  condition: string
  action: string
  description: string
}

const DEFAULT_RULES: CheckpointRule[] = [
  {
    id: 'r1',
    dimension: 'risk_level',
    condition: 'HIGH',
    action: 'MANUAL_REVIEW',
    description: 'High-risk clients require manual compliance review before onboarding proceeds.',
  },
  {
    id: 'r2',
    dimension: 'risk_level',
    condition: 'VERY_HIGH',
    action: 'MANUAL_REVIEW',
    description: 'Very high-risk clients require enhanced due diligence and senior approval.',
  },
  {
    id: 'r3',
    dimension: 'account_value_band',
    condition: '>= £1,000,000',
    action: 'ENHANCED_DUE_DILIGENCE',
    description: 'Accounts exceeding £1M require enhanced source-of-wealth documentation.',
  },
  {
    id: 'r4',
    dimension: 'jurisdiction',
    condition: 'US',
    action: 'FATCA_CHECK',
    description: 'US persons require FATCA self-certification and IRS W-9 / W-8BEN form.',
  },
  {
    id: 'r5',
    dimension: 'product_type',
    condition: 'retirement_account',
    action: 'PENSION_SUITABILITY_CHECK',
    description: 'Retirement accounts require age and pension transfer suitability assessment.',
  },
]

const DIMENSION_LABELS: Record<string, string> = {
  product_type: 'Product Type',
  risk_level: 'Risk Level',
  account_value_band: 'Account Value',
  jurisdiction: 'Jurisdiction',
}

const DIMENSION_COLORS: Record<string, string> = {
  product_type: 'bg-purple-50 text-purple-700 ring-purple-200',
  risk_level: 'bg-red-50 text-red-700 ring-red-200',
  account_value_band: 'bg-blue-50 text-blue-700 ring-blue-200',
  jurisdiction: 'bg-teal-50 text-teal-700 ring-teal-200',
}

export default function CheckpointRulesEditor() {
  const [rules, setRules] = useState<CheckpointRule[]>(DEFAULT_RULES)
  const [showAdd, setShowAdd] = useState(false)
  const [newRule, setNewRule] = useState<Omit<CheckpointRule, 'id'>>({
    dimension: 'risk_level',
    condition: '',
    action: '',
    description: '',
  })

  function removeRule(id: string) {
    setRules((prev) => prev.filter((r) => r.id !== id))
  }

  function addRule() {
    if (!newRule.condition.trim() || !newRule.action.trim()) return
    setRules((prev) => [
      ...prev,
      { ...newRule, id: `r${Date.now()}` },
    ])
    setNewRule({ dimension: 'risk_level', condition: '', action: '', description: '' })
    setShowAdd(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-gray-900">Checkpoint Rules</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Rules that trigger additional checks during KYC and product onboarding. Evaluated across 4 dimensions.
        </p>
      </div>

      {/* Persistence note */}
      <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
        <p className="text-[11px] text-amber-700">
          Changes here affect local state only. Persistent DB-backed rules are wired in Phase 6 (STEP-30).
        </p>
      </div>

      {/* Rules table */}
      <div className="overflow-hidden rounded-xl border border-gray-200">
        <table className="w-full text-xs">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                Dimension
              </th>
              <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                Condition
              </th>
              <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                Action
              </th>
              <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                Description
              </th>
              <th className="w-10 px-4 py-2.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rules.map((rule) => (
              <tr key={rule.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <span
                    className={[
                      'rounded-full px-2 py-0.5 text-[10px] font-medium ring-1',
                      DIMENSION_COLORS[rule.dimension] ?? 'bg-gray-50 text-gray-600 ring-gray-200',
                    ].join(' ')}
                  >
                    {DIMENSION_LABELS[rule.dimension] ?? rule.dimension}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <code className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-700">
                    {rule.condition}
                  </code>
                </td>
                <td className="px-4 py-3">
                  <code className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700">
                    {rule.action}
                  </code>
                </td>
                <td className="px-4 py-3 text-[11px] text-gray-500">{rule.description}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => removeRule(rule.id)}
                    className="rounded p-1 text-gray-300 hover:bg-red-50 hover:text-red-500"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add rule form */}
      {showAdd ? (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <p className="mb-3 text-xs font-semibold text-blue-700">New Checkpoint Rule</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600">Dimension</label>
              <select
                value={newRule.dimension}
                onChange={(e) =>
                  setNewRule((prev) => ({
                    ...prev,
                    dimension: e.target.value as CheckpointRule['dimension'],
                  }))
                }
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none"
              >
                {Object.entries(DIMENSION_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600">Condition</label>
              <input
                type="text"
                value={newRule.condition}
                onChange={(e) => setNewRule((prev) => ({ ...prev, condition: e.target.value }))}
                placeholder="e.g. HIGH or >= £500,000"
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none focus:border-blue-400"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600">Action</label>
              <input
                type="text"
                value={newRule.action}
                onChange={(e) => setNewRule((prev) => ({ ...prev, action: e.target.value }))}
                placeholder="e.g. MANUAL_REVIEW"
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none focus:border-blue-400"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600">Description</label>
              <input
                type="text"
                value={newRule.description}
                onChange={(e) => setNewRule((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Short explanation…"
                className="w-full rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none focus:border-blue-400"
              />
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={addRule}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
            >
              Add Rule
            </button>
            <button
              onClick={() => setShowAdd(false)}
              className="rounded-lg bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 rounded-lg border border-dashed border-gray-300 px-4 py-2.5 text-xs font-medium text-gray-500 hover:border-blue-400 hover:text-blue-600"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Checkpoint Rule
        </button>
      )}
    </div>
  )
}
