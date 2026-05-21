import { useState } from 'react'
import { X, Briefcase, Users, FileText } from 'lucide-react'
import { useProducts, useAdvisors, useInitiateCase } from '@/hooks/useDocuments'

interface Props {
  onCreated: (newCaseId: string) => void
  onClose: () => void
}

export default function CreateCaseModal({ onCreated, onClose }: Props) {
  const [caseName, setCaseName] = useState('')
  const [selectedProducts, setSelectedProducts] = useState<string[]>([])
  const [advisorId, setAdvisorId] = useState<string>('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const { data: products, isLoading: productsLoading } = useProducts()
  const { data: advisors, isLoading: advisorsLoading } = useAdvisors()
  const initiate = useInitiateCase()

  function toggleProduct(code: string) {
    setSelectedProducts((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
    )
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!caseName.trim() || selectedProducts.length === 0) return
    setErrorMessage(null)
    try {
      const newCase = await initiate.mutateAsync({
        case_name: caseName.trim(),
        selected_products: selectedProducts,
        assigned_advisor_id: advisorId || null,
      })
      onCreated(newCase.id)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorMessage(detail ?? 'Something went wrong. Please try again.')
    }
  }

  const ready = caseName.trim().length > 0 && selectedProducts.length > 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl dark:bg-gray-800">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-gray-100 px-6 py-5 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Start your onboarding</h2>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
              Let's get you set up — this takes under a minute.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 px-6 py-5">
          {/* Case name */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300">
              <FileText className="h-4 w-4 text-gray-400" />
              Case name
            </label>
            <input
              type="text"
              placeholder="e.g. Retirement Planning 2026"
              value={caseName}
              onChange={(e) => setCaseName(e.target.value)}
              className="w-full rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
              required
            />
          </div>

          {/* Product selection */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300">
              <Briefcase className="h-4 w-4 text-gray-400" />
              Product type
              <span className="ml-1 text-xs font-normal text-gray-400">(select one or more)</span>
            </label>
            {productsLoading ? (
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-200 border-t-blue-500 dark:border-gray-600" />
                Loading products…
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {(products ?? []).map((p) => {
                  const active = selectedProducts.includes(p.product_code)
                  return (
                    <button
                      key={p.product_code}
                      type="button"
                      onClick={() => toggleProduct(p.product_code)}
                      className={[
                        'rounded-xl border px-3 py-2.5 text-left text-sm transition-all',
                        active
                          ? 'border-blue-500 bg-blue-50 text-blue-700 ring-1 ring-blue-400 dark:bg-blue-950 dark:text-blue-300'
                          : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600',
                      ].join(' ')}
                    >
                      <span className="block font-medium">{p.name}</span>
                      {p.description && (
                        <span className="mt-0.5 block text-xs text-gray-400 line-clamp-1">
                          {p.description}
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Advisor selection */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300">
              <Users className="h-4 w-4 text-gray-400" />
              Advisor
              <span className="ml-1 text-xs font-normal text-gray-400">(optional)</span>
            </label>
            {advisorsLoading ? (
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-200 border-t-blue-500 dark:border-gray-600" />
                Loading advisors…
              </div>
            ) : (
              <select
                value={advisorId}
                onChange={(e) => setAdvisorId(e.target.value)}
                className="w-full rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-900 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              >
                <option value="">Assign me to any available advisor</option>
                {(advisors ?? []).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.first_name} {a.last_name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Error */}
          {errorMessage && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
              {errorMessage}
            </p>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={!ready || initiate.isPending}
            className="w-full rounded-xl bg-blue-600 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {initiate.isPending ? 'Creating case…' : 'Create case'}
          </button>
        </form>
      </div>
    </div>
  )
}
