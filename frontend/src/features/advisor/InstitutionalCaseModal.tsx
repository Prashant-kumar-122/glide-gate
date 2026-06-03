import { useState, useEffect, useRef } from 'react'
import { X, Building2, Briefcase, UserSearch, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react'
import { useProducts, useInitiateCase, useLookupClient } from '@/hooks/useDocuments'
import type { UserOut } from '@/lib/api'

interface Props {
  onCreated: (newCaseId: string, clientId: string, label: string) => void
  onClose: () => void
}

export default function InstitutionalCaseModal({ onCreated, onClose }: Props) {
  const [legalEntityName, setLegalEntityName] = useState('')
  const [selectedProducts, setSelectedProducts] = useState<string[]>([])
  const [clientEmail, setClientEmail] = useState('')
  const [foundClient, setFoundClient] = useState<UserOut | null>(null)
  const [clientWarning, setClientWarning] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { data: products, isLoading: productsLoading } = useProducts()
  const initiate = useInitiateCase()
  const lookupClient = useLookupClient()

  // Debounced client lookup on email change
  useEffect(() => {
    setFoundClient(null)
    setClientWarning(null)

    const trimmed = clientEmail.trim()
    if (!trimmed) return

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        const user = await lookupClient.mutateAsync(trimmed)
        setFoundClient(user)
        setClientWarning(null)
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        if (detail === 'not_a_client') {
          setClientWarning('This user is not registered as a client.')
        } else {
          setClientWarning('No GlideGate account found for this email.')
        }
      }
    }, 400)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientEmail])

  function toggleProduct(code: string) {
    setSelectedProducts((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
    )
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!legalEntityName.trim() || selectedProducts.length === 0 || !foundClient) return
    setErrorMessage(null)
    try {
      const newCase = await initiate.mutateAsync({
        legal_entity_name: legalEntityName.trim(),
        selected_products: selectedProducts,
        client_id: foundClient.id,
        metadata: { legal_entity_name: legalEntityName.trim() },
      })
      onCreated(newCase.id, foundClient!.id, legalEntityName.trim())
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorMessage(detail ?? 'Something went wrong. Please try again.')
    }
  }

  const ready =
    legalEntityName.trim().length > 0 &&
    selectedProducts.length > 0 &&
    foundClient !== null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl dark:bg-gray-800 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-gray-100 px-6 py-5 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Open New Account</h2>
            <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
              Open an institutional account for a client entity.
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
          {/* Legal Entity Name */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300">
              <Building2 className="h-4 w-4 text-gray-400" />
              Legal Entity Name
            </label>
            <input
              type="text"
              placeholder="e.g. Acme Capital Partners LLC"
              value={legalEntityName}
              onChange={(e) => setLegalEntityName(e.target.value)}
              className="w-full rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
              required
            />
          </div>

          {/* Product Selection */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300">
              <Briefcase className="h-4 w-4 text-gray-400" />
              Products
              <span className="ml-1 text-xs font-normal text-gray-400">(select one or more)</span>
            </label>
            {productsLoading ? (
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Loader2 className="h-4 w-4 animate-spin" />
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

          {/* Invite Client */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300">
              <UserSearch className="h-4 w-4 text-gray-400" />
              Invite Client
            </label>
            <input
              type="email"
              placeholder="client@example.com"
              value={clientEmail}
              onChange={(e) => setClientEmail(e.target.value)}
              className="w-full rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
            />

            {/* Lookup loading */}
            {lookupClient.isPending && clientEmail.trim() && (
              <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
                <Loader2 className="h-3 w-3 animate-spin" />
                Looking up account…
              </div>
            )}

            {/* Client found */}
            {foundClient && (
              <div className="mt-3 grid grid-cols-2 gap-2">
                <div>
                  <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">First name</p>
                  <div className="flex items-center gap-1.5 rounded-xl border border-green-300 bg-green-50 px-3 py-2.5 text-sm text-green-800 dark:border-green-700 dark:bg-green-950 dark:text-green-300">
                    <CheckCircle className="h-3.5 w-3.5 shrink-0" />
                    {foundClient.first_name}
                  </div>
                </div>
                <div>
                  <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Last name</p>
                  <div className="flex items-center gap-1.5 rounded-xl border border-green-300 bg-green-50 px-3 py-2.5 text-sm text-green-800 dark:border-green-700 dark:bg-green-950 dark:text-green-300">
                    {foundClient.last_name}
                  </div>
                </div>
              </div>
            )}

            {/* Warning */}
            {clientWarning && !lookupClient.isPending && (
              <div className="mt-2 flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-400">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                {clientWarning}
              </div>
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
            {initiate.isPending ? 'Opening account…' : 'Open account'}
          </button>
        </form>
      </div>
    </div>
  )
}
