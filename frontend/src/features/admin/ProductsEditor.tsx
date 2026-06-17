import { useState } from 'react'
import { Plus, Trash2, Loader2, ChevronDown, ChevronRight, GripVertical } from 'lucide-react'
import {
  useProducts,
  useCreateProduct,
  useUpdateProduct,
  useDeleteProduct,
  usePipeline,
  useAddPipelineStep,
  useDeletePipelineStep,
  type ProductOut,
} from '@/hooks/useDomainAdmin'

interface Props {
  domainId: string
}

function JsonEditor({
  label,
  value,
  onChange,
}: {
  label: string
  value: Record<string, unknown>
  onChange: (v: Record<string, unknown>) => void
}) {
  const [raw, setRaw] = useState(JSON.stringify(value, null, 2))
  const [err, setErr] = useState<string | null>(null)

  function handleBlur() {
    try {
      const parsed = JSON.parse(raw)
      onChange(parsed)
      setErr(null)
    } catch {
      setErr('Invalid JSON')
    }
  }

  return (
    <div className="space-y-1">
      <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">{label}</label>
      <textarea
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        onBlur={handleBlur}
        rows={5}
        spellCheck={false}
        className="w-full border border-gray-200 bg-white px-2.5 py-2 font-mono text-[11px] text-gray-700 outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
      />
      {err && <p className="text-[10px] text-red-500">{err}</p>}
    </div>
  )
}

function PipelineEditor({ domainId, productCode }: { domainId: string; productCode: string }) {
  const { data: steps, isLoading } = usePipeline(domainId, productCode)
  const addStep = useAddPipelineStep(domainId, productCode)
  const deleteStep = useDeletePipelineStep(domainId, productCode)

  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ step_id: '', step_label: '', step_order: 0, is_parallel: false, step_config: '{}' })

  function handleAdd() {
    if (!form.step_id.trim() || !form.step_label.trim()) return
    let config: Record<string, unknown> = {}
    try { config = JSON.parse(form.step_config) } catch { /* ignore */ }
    addStep.mutate(
      { step_id: form.step_id, step_label: form.step_label, step_order: form.step_order, is_parallel: form.is_parallel, step_config: config },
      { onSuccess: () => { setForm({ step_id: '', step_label: '', step_order: 0, is_parallel: false, step_config: '{}' }); setShowAdd(false) } },
    )
  }

  if (isLoading) return <div className="py-4 text-center text-xs text-gray-400"><Loader2 className="mx-auto h-4 w-4 animate-spin" /></div>

  return (
    <div className="mt-3 space-y-2">
      <h5 className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">Pipeline Steps</h5>
      <div className="overflow-hidden border border-gray-200 dark:border-gray-700">
        {(steps ?? []).length === 0 && (
          <p className="py-4 text-center text-[11px] text-gray-400">No steps. Add the first step below.</p>
        )}
        {(steps ?? []).map((s) => (
          <div key={s.id} className="flex items-center gap-3 border-b border-gray-100 px-3 py-2.5 last:border-0 dark:border-gray-700">
            <GripVertical className="h-3.5 w-3.5 text-gray-300" />
            <span className="w-6 text-center text-[11px] font-mono text-gray-400">{s.step_order}</span>
            <div className="flex-1">
              <p className="font-mono text-[11px] font-medium text-gray-800 dark:text-gray-100">{s.step_id}</p>
              <p className="text-[10px] text-gray-500">{s.step_label}{s.is_parallel && ' (parallel)'}</p>
            </div>
            <button
              onClick={() => deleteStep.mutate(s.step_id)}
              className="rounded p-0.5 text-gray-300 hover:text-red-500"
              aria-label="Delete step"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>

      {showAdd ? (
        <div className="border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-950">
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Step ID</label>
              <input
                type="text"
                value={form.step_id}
                onChange={(e) => setForm((p) => ({ ...p, step_id: e.target.value }))}
                placeholder="e.g. collect_documents"
                className="w-full border border-gray-200 bg-white px-2 py-1 font-mono text-[11px] outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Label</label>
              <input
                type="text"
                value={form.step_label}
                onChange={(e) => setForm((p) => ({ ...p, step_label: e.target.value }))}
                placeholder="Collect documents"
                className="w-full border border-gray-200 bg-white px-2 py-1 text-[11px] outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Order</label>
              <input
                type="number"
                value={form.step_order}
                onChange={(e) => setForm((p) => ({ ...p, step_order: parseInt(e.target.value, 10) || 0 }))}
                className="w-full border border-gray-200 bg-white px-2 py-1 text-[11px] outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="flex items-end pb-1.5">
              <label className="flex items-center gap-2 text-[11px] text-gray-600 dark:text-gray-400">
                <input type="checkbox" checked={form.is_parallel} onChange={(e) => setForm((p) => ({ ...p, is_parallel: e.target.checked }))} className="h-3.5 w-3.5 accent-blue-600" />
                Parallel
              </label>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleAdd}
              disabled={!form.step_id.trim() || !form.step_label.trim() || addStep.isPending}
              className="flex items-center gap-1 bg-primary px-2.5 py-1 text-[11px] font-medium text-white disabled:opacity-50"
            >
              {addStep.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              Add
            </button>
            <button onClick={() => setShowAdd(false)} className="px-2.5 py-1 text-[11px] text-gray-500">Cancel</button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 border border-dashed border-gray-300 px-3 py-2 text-[11px] text-gray-500 hover:border-primary hover:text-primary dark:border-gray-600"
        >
          <Plus className="h-3 w-3" />
          Add Step
        </button>
      )}
    </div>
  )
}

export default function ProductsEditor({ domainId }: Props) {
  const { data: products, isLoading } = useProducts(domainId)
  const createProduct = useCreateProduct(domainId)
  const updateProduct = useUpdateProduct(domainId)
  const deleteProduct = useDeleteProduct(domainId)

  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ product_code: '', display_name: '', product_type: 'retail' })
  const [expanded, setExpanded] = useState<string | null>(null)
  const [editingProduct, setEditingProduct] = useState<ProductOut | null>(null)

  function handleAdd() {
    if (!form.product_code.trim() || !form.display_name.trim()) return
    createProduct.mutate(form, {
      onSuccess: () => {
        setForm({ product_code: '', display_name: '', product_type: 'retail' })
        setShowAdd(false)
      },
    })
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Products</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Product catalog with suitability criteria, activation criteria, and per-product pipeline steps.
        </p>
      </div>

      <div className="overflow-hidden border border-gray-200 dark:border-gray-700">
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-xs text-gray-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {(products ?? []).length === 0 && (
              <p className="py-8 text-center text-xs text-gray-400">No products defined.</p>
            )}
            {(products ?? []).map((p) => (
              <div key={p.id}>
                <div className="flex items-center justify-between px-4 py-3">
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <button
                      onClick={() => setExpanded((e) => (e === p.product_code ? null : p.product_code))}
                      className="shrink-0 text-gray-400 hover:text-gray-600"
                    >
                      {expanded === p.product_code
                        ? <ChevronDown className="h-4 w-4" />
                        : <ChevronRight className="h-4 w-4" />
                      }
                    </button>
                    <div className="min-w-0">
                      <p className="font-mono text-xs font-medium text-gray-800 dark:text-gray-100">{p.product_code}</p>
                      <p className="text-[11px] text-gray-500">{p.display_name} · {p.product_type}</p>
                    </div>
                  </div>
                  <div className="ml-3 flex shrink-0 items-center gap-2">
                    <span className={[
                      'px-2 py-0.5 text-[10px] font-medium ring-1',
                      p.is_active
                        ? 'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:ring-emerald-800'
                        : 'bg-gray-50 text-gray-400 ring-gray-200 dark:bg-gray-800 dark:ring-gray-700',
                    ].join(' ')}>
                      {p.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <button
                      onClick={() => updateProduct.mutate({ id: p.id, is_active: !p.is_active })}
                      className="border border-gray-200 px-2 py-0.5 text-[11px] text-gray-500 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-400"
                    >
                      Toggle
                    </button>
                    <button
                      onClick={() => deleteProduct.mutate(p.id)}
                      className="rounded p-1 text-gray-300 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-950"
                      aria-label="Delete product"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>

                {expanded === p.product_code && (
                  <div className="border-t border-gray-100 px-4 py-4 dark:border-gray-700">
                    {editingProduct?.id === p.id ? (
                      <div className="space-y-4">
                        <JsonEditor
                          label="Suitability Criteria"
                          value={editingProduct.suitability_criteria}
                          onChange={(v) => setEditingProduct((ep) => ep ? { ...ep, suitability_criteria: v } : null)}
                        />
                        <JsonEditor
                          label="Activation Criteria"
                          value={editingProduct.activation_criteria}
                          onChange={(v) => setEditingProduct((ep) => ep ? { ...ep, activation_criteria: v } : null)}
                        />
                        <div className="space-y-1">
                          <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Required Documents (comma-separated)</label>
                          <input
                            type="text"
                            value={editingProduct.required_documents.join(', ')}
                            onChange={(e) => setEditingProduct((ep) => ep ? {
                              ...ep,
                              required_documents: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                            } : null)}
                            className="w-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                          />
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              updateProduct.mutate({
                                id: p.id,
                                suitability_criteria: editingProduct.suitability_criteria,
                                activation_criteria: editingProduct.activation_criteria,
                                required_documents: editingProduct.required_documents,
                              }, { onSuccess: () => setEditingProduct(null) })
                            }}
                            disabled={updateProduct.isPending}
                            className="bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-50"
                          >
                            Save
                          </button>
                          <button onClick={() => setEditingProduct(null)} className="px-3 py-1.5 text-xs text-gray-500">Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => setEditingProduct(p)}
                        className="text-xs text-blue-600 hover:underline dark:text-blue-400"
                      >
                        Edit criteria &amp; required documents
                      </button>
                    )}

                    <PipelineEditor domainId={domainId} productCode={p.product_code} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {showAdd ? (
        <div className="border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
          <p className="mb-3 text-xs font-semibold text-blue-700 dark:text-blue-300">New Product</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Product Code <span className="text-red-400">*</span></label>
              <input
                type="text"
                value={form.product_code}
                onChange={(e) => setForm((p) => ({ ...p, product_code: e.target.value.toLowerCase() }))}
                placeholder="e.g. equity_fund"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 font-mono text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Display Name <span className="text-red-400">*</span></label>
              <input
                type="text"
                value={form.display_name}
                onChange={(e) => setForm((p) => ({ ...p, display_name: e.target.value }))}
                placeholder="e.g. Equity Fund"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Type</label>
              <input
                type="text"
                value={form.product_type}
                onChange={(e) => setForm((p) => ({ ...p, product_type: e.target.value }))}
                placeholder="retail / institutional"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
          </div>
          {createProduct.isError && (
            <p className="mt-2 text-[11px] text-red-600 dark:text-red-400">Failed to create product.</p>
          )}
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleAdd}
              disabled={!form.product_code.trim() || !form.display_name.trim() || createProduct.isPending}
              className="flex items-center gap-1.5 bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-50"
            >
              {createProduct.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              Create Product
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
          Add Product
        </button>
      )}
    </div>
  )
}
