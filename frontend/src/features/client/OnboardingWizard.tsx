import { useEffect, useMemo, useState } from 'react'
import {
  ArrowLeft, ArrowRight, CheckCircle, Upload, Star, Users, Building2,
  Globe, Zap, FileText, Loader, Sparkles, X,
} from 'lucide-react'
import {
  useProducts, useQuestionnaireSchema, useCollectedFields,
  useUpdateCollectedField, useInitiateCase, useCases,
} from '@/hooks/useDocuments'
import { api } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import DocumentUploadStep from '@/features/client/DocumentUploadStep'
import type { ProductOut } from '@/lib/api'
import type { QuestionSchemaItem } from '@/hooks/useDocuments'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatSectionTitle(section: string): string {
  const overrides: Record<string, string> = {
    personal: 'Personal Information',
    financial: 'Financial Information',
    tax: 'Tax Information',
    risk: 'Risk Profile',
    employment: 'Employment Details',
    identity: 'Identity Verification',
  }
  return overrides[section] ?? section.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

function sectionIcon(section: string) {
  const map: Record<string, typeof Users> = {
    personal: Users,
    financial: Building2,
    tax: Globe,
    risk: Zap,
    employment: FileText,
    identity: CheckCircle,
  }
  return map[section] ?? FileText
}

// ── Step definitions ──────────────────────────────────────────────────────────

interface WizardStep {
  id: string
  title: string
  icon: typeof Star
}

function buildSteps(sections: string[]): WizardStep[] {
  return [
    { id: 'products',  title: 'Select Products',  icon: Star },
    { id: 'documents', title: 'Upload Documents',  icon: Upload },
    ...sections.map((s) => ({ id: s, title: formatSectionTitle(s), icon: sectionIcon(s) })),
    { id: 'review',    title: 'Review & Submit',   icon: CheckCircle },
  ]
}

// ── Field renderer ────────────────────────────────────────────────────────────

function SchemaField({
  field,
  value,
  onChange,
}: {
  field: QuestionSchemaItem
  value: unknown
  onChange: (v: unknown) => void
}) {
  const base = 'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
  const strVal = value !== undefined && value !== null ? String(value) : ''

  if (field.field_type === 'choice' && field.options?.length) {
    return (
      <select value={strVal} onChange={(e) => onChange(e.target.value)} className={base}>
        <option value="">Select…</option>
        {field.options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    )
  }

  if (field.field_type === 'multi_choice' && field.options?.length) {
    const selected: string[] = Array.isArray(value) ? (value as string[]) : strVal ? [strVal] : []
    return (
      <div className="space-y-2">
        {field.options.map((o) => (
          <label key={o} className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={selected.includes(o)}
              onChange={(e) => {
                const next = e.target.checked
                  ? [...selected, o]
                  : selected.filter((x) => x !== o)
                onChange(next)
              }}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">{o}</span>
          </label>
        ))}
      </div>
    )
  }

  const inputType = field.field_type === 'number' ? 'number' : field.field_type === 'date' ? 'date' : 'text'
  return (
    <input
      type={inputType}
      value={strVal}
      onChange={(e) => onChange(e.target.value)}
      placeholder={`Enter ${field.label.toLowerCase()}`}
      className={base}
    />
  )
}

// ── Product card ──────────────────────────────────────────────────────────────

function ProductCard({
  product,
  selected,
  onToggle,
}: {
  product: ProductOut
  selected: boolean
  onToggle: () => void
}) {
  return (
    <button
      onClick={onToggle}
      className={[
        'w-full text-left rounded-xl border-2 p-4 transition-all',
        selected
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 bg-white hover:border-blue-300',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-gray-900 truncate">{product.name}</p>
          {product.description && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{product.description}</p>
          )}
        </div>
        <div
          className={[
            'w-5 h-5 rounded-full border-2 shrink-0 mt-0.5 flex items-center justify-center transition-all',
            selected ? 'border-blue-500 bg-blue-500' : 'border-gray-300',
          ].join(' ')}
        >
          {selected && (
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </div>
      </div>
    </button>
  )
}

// ── Review step ───────────────────────────────────────────────────────────────

function ReviewStep({
  caseId,
  schemaFields,
  localData,
  onSubmit,
  isSubmitting,
}: {
  caseId: string
  schemaFields: QuestionSchemaItem[]
  localData: Record<string, unknown>
  onSubmit: () => void
  isSubmitting: boolean
}) {
  const sections = [...new Set(schemaFields.map((f) => f.section))]
  const filledCount = schemaFields.filter((f) => localData[f.question_key] !== undefined && localData[f.question_key] !== '').length

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-bold text-gray-900">Review &amp; Submit</h3>
        <p className="text-sm text-gray-500 mt-1">
          {filledCount} of {schemaFields.length} fields completed. Please review before submitting.
        </p>
      </div>

      {sections.map((section) => {
        const fields = schemaFields.filter((f) => f.section === section && localData[f.question_key])
        if (fields.length === 0) return null
        return (
          <div key={section} className="rounded-xl border border-gray-200 bg-white p-5">
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
              {formatSectionTitle(section)}
            </h4>
            <div className="grid grid-cols-2 gap-x-6 gap-y-3">
              {fields.map((f) => (
                <div key={f.question_key}>
                  <p className="text-xs text-gray-400">{f.label}</p>
                  <p className="text-sm font-medium text-gray-800 mt-0.5">
                    {Array.isArray(localData[f.question_key])
                      ? (localData[f.question_key] as string[]).join(', ')
                      : String(localData[f.question_key])}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )
      })}

      {/* Declaration */}
      <div className="rounded-xl bg-gray-50 border border-gray-200 p-4">
        <p className="text-xs text-gray-500 leading-relaxed">
          By submitting this application, I confirm that all information provided is accurate and
          complete to the best of my knowledge. I understand that providing false information may
          result in rejection of my application.
        </p>
      </div>

      <button
        onClick={onSubmit}
        disabled={isSubmitting}
        className="w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isSubmitting ? (
          <><Loader className="w-4 h-4 animate-spin" />Submitting…</>
        ) : (
          <><CheckCircle className="w-4 h-4" />Submit Application</>
        )}
      </button>
    </div>
  )
}

// ── Main wizard ───────────────────────────────────────────────────────────────

interface Props {
  onComplete: () => void
  onCancel: () => void
}

export default function OnboardingWizard({ onComplete, onCancel }: Props) {
  const [step, setStep] = useState(0)
  const [selectedProducts, setSelectedProducts] = useState<string[]>([])
  const [caseId, setCaseId] = useState<string | null>(null)
  const [prefillCount, setPrefillCount] = useState(0)
  const [showPrefillBanner, setShowPrefillBanner] = useState(false)
  const [localData, setLocalData] = useState<Record<string, unknown>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [creatingCase, setCreatingCase] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  const { user } = useAuthStore()
  const { data: existingCases = [] } = useCases()
  const { data: products = [], isLoading: productsLoading } = useProducts()
  const { data: schemaData, isLoading: schemaLoading } = useQuestionnaireSchema(caseId)
  const { data: collectedData } = useCollectedFields(caseId)
  const updateField = useUpdateCollectedField(caseId)
  const initiateCase = useInitiateCase()

  // Initialise local form data from collected-fields when they load
  useEffect(() => {
    if (collectedData?.client_data) {
      setLocalData((prev) => ({ ...collectedData.client_data, ...prev }))
    }
  }, [collectedData])

  const schemaSections = useMemo(
    () => [...new Set(schemaData?.fields.map((f) => f.section) ?? [])],
    [schemaData],
  )

  const steps = useMemo(() => buildSteps(schemaSections), [schemaSections])
  const totalSteps = steps.length
  const progressPct = Math.round((step / Math.max(totalSteps - 1, 1)) * 100)

  const currentStep = steps[step]

  async function handleProductsContinue() {
    if (selectedProducts.length === 0) return
    setCreatingCase(true)
    setCreateError(null)
    try {
      const paddedId = String(existingCases.length).padStart(2, '0')
      const caseName = `${user?.firstName ?? ''} ${user?.lastName ?? ''} ${paddedId}`.trim()
      const newCase = await initiateCase.mutateAsync({
        case_name: caseName,
        selected_products: selectedProducts,
        assigned_advisor_id: null,
      })
      setCaseId(newCase.id)
      setStep(1)
    } catch {
      setCreateError('Failed to create case. Please try again.')
    } finally {
      setCreatingCase(false)
    }
  }

  async function handleSectionContinue() {
    if (!caseId) return
    const section = currentStep.id
    const sectionFields = schemaData?.fields.filter((f) => f.section === section) ?? []
    const initial = collectedData?.client_data ?? {}
    const dirty = sectionFields
      .map((f) => f.question_key)
      .filter((k) => {
        const cur = localData[k]
        const orig = initial[k]
        return cur !== undefined && cur !== orig
      })

    if (dirty.length > 0) {
      await Promise.allSettled(
        dirty.map((k) => updateField.mutateAsync({ questionKey: k, value: localData[k] })),
      )
    }
    setStep((s) => s + 1)
  }

  async function handleSubmit() {
    if (!caseId) return
    setIsSubmitting(true)
    try {
      await api.post(`/cases/${caseId}/resume`)
    } catch {
      // Submission failed gracefully — case data is saved regardless
    } finally {
      setIsSubmitting(false)
      onComplete()
    }
  }

  function handleBack() {
    if (step === 0) {
      onCancel()
    } else {
      setStep((s) => s - 1)
    }
  }

  function handleDocumentAnalysed(count: number) {
    setPrefillCount(count)
    if (count > 0) setShowPrefillBanner(true)
  }

  function canProceed(): boolean {
    if (step === 0) return selectedProducts.length > 0
    if (step === 1) return true // documents step — always optional
    return true
  }

  function renderContent() {
    if (!currentStep) return null

    // Step 0: product selection
    if (currentStep.id === 'products') {
      return (
        <div className="space-y-5">
          <div>
            <h3 className="text-lg font-bold text-gray-900">Select Products</h3>
            <p className="text-sm text-gray-500 mt-1">
              Choose the accounts you'd like to open. You can select multiple products.
            </p>
          </div>

          {createError && (
            <div className="rounded-xl bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-700">
              {createError}
            </div>
          )}

          {productsLoading ? (
            <div className="flex justify-center py-12">
              <div className="h-7 w-7 rounded-full border-2 border-gray-200 border-t-blue-500 animate-spin" />
            </div>
          ) : products.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No products available.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {products.map((p) => (
                <ProductCard
                  key={p.id}
                  product={p}
                  selected={selectedProducts.includes(p.product_code)}
                  onToggle={() => {
                    setSelectedProducts((prev) =>
                      prev.includes(p.product_code)
                        ? prev.filter((x) => x !== p.product_code)
                        : [...prev, p.product_code],
                    )
                  }}
                />
              ))}
            </div>
          )}

          {selectedProducts.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-1">
              {selectedProducts.map((code) => {
                const p = products.find((x) => x.product_code === code)
                return (
                  <span
                    key={code}
                    className="inline-flex items-center gap-1.5 text-xs font-medium bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full"
                  >
                    {p?.name ?? code}
                    <button
                      onClick={() => setSelectedProducts((prev) => prev.filter((x) => x !== code))}
                      className="hover:text-blue-900"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )
              })}
            </div>
          )}
        </div>
      )
    }

    // Step 1: document upload
    if (currentStep.id === 'documents' && caseId) {
      return (
        <DocumentUploadStep
          caseId={caseId}
          onAnalysed={handleDocumentAnalysed}
          onSkip={() => setStep((s) => s + 1)}
        />
      )
    }

    // Review step
    if (currentStep.id === 'review' && caseId && schemaData) {
      return (
        <ReviewStep
          caseId={caseId}
          schemaFields={schemaData.fields}
          localData={localData}
          onSubmit={handleSubmit}
          isSubmitting={isSubmitting}
        />
      )
    }

    // Schema section steps
    if (caseId) {
      if (schemaLoading) {
        return (
          <div className="flex justify-center py-12">
            <div className="h-7 w-7 rounded-full border-2 border-gray-200 border-t-blue-500 animate-spin" />
          </div>
        )
      }

      const sectionFields = schemaData?.fields.filter((f) => f.section === currentStep.id) ?? []

      return (
        <div className="space-y-5">
          {/* Pre-fill banner */}
          {showPrefillBanner && prefillCount > 0 && (
            <div className="flex items-start gap-3 rounded-xl bg-violet-50 border border-violet-200 px-4 py-3">
              <Sparkles className="w-4 h-4 text-violet-500 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="text-xs text-violet-800">
                  <strong>{prefillCount} fields pre-filled</strong> from your documents.
                  Please review all values before continuing.
                </span>
              </div>
              <button
                onClick={() => setShowPrefillBanner(false)}
                className="text-violet-400 hover:text-violet-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {sectionFields.length === 0 ? (
            <p className="text-sm text-gray-400 py-4">No fields for this section.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
              {sectionFields.map((field) => (
                <div
                  key={field.question_key}
                  className={field.field_type === 'multi_choice' ? 'sm:col-span-2' : ''}
                >
                  <label className="block text-xs font-medium text-gray-700 mb-1.5">
                    {field.label}
                  </label>
                  <SchemaField
                    field={field}
                    value={localData[field.question_key]}
                    onChange={(v) =>
                      setLocalData((prev) => ({ ...prev, [field.question_key]: v }))
                    }
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )
    }

    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-gray-50">
      {/* Top progress bar */}
      <div className="h-1 bg-gray-200 shrink-0">
        <div
          className="h-full bg-blue-600 transition-all duration-500"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Header */}
      <header className="shrink-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Building2 className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="font-bold text-sm text-gray-900">GlideGate</div>
            <div className="text-gray-400 text-xs">New Account Application</div>
          </div>
        </div>
        <button
          onClick={onCancel}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-700 border border-gray-200 hover:border-gray-300 px-3 py-1.5 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Cancel
        </button>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — stepper */}
        <aside className="w-60 shrink-0 bg-gray-900 flex flex-col overflow-y-auto hidden lg:flex">
          <nav className="flex-1 px-4 py-8">
            <div className="space-y-1">
              {steps.map((s, idx) => {
                const isCompleted = idx < step
                const isActive = idx === step
                const isPending = idx > step
                const Icon = s.icon
                return (
                  <button
                    key={s.id}
                    onClick={() => isCompleted && setStep(idx)}
                    disabled={isPending}
                    className={[
                      'w-full flex items-center gap-3 px-3 py-3 rounded-xl text-left transition-all',
                      isActive && 'bg-white/10',
                      isCompleted && 'hover:bg-white/5 cursor-pointer',
                      isPending && 'cursor-default opacity-40',
                    ].filter(Boolean).join(' ')}
                  >
                    <div
                      className={[
                        'w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold transition-all',
                        isCompleted ? 'bg-emerald-500 text-white' :
                        isActive ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/40' :
                        'bg-white/10 text-gray-400',
                      ].join(' ')}
                    >
                      {isCompleted ? <CheckCircle className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                    </div>
                    <div className="min-w-0">
                      <div
                        className={[
                          'text-xs font-medium leading-tight truncate',
                          isActive ? 'text-white' : isCompleted ? 'text-gray-300' : 'text-gray-500',
                        ].join(' ')}
                      >
                        {s.title}
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </nav>

          {/* Progress footer */}
          <div className="px-5 py-5 border-t border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-gray-400">Overall progress</span>
              <span className="text-xs font-bold text-white">{progressPct}%</span>
            </div>
            <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <div className="mt-2 text-xs text-gray-500">
              Step {step + 1} of {totalSteps}
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Step header */}
          <div className="shrink-0 bg-white border-b border-gray-100 px-8 py-5">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-gray-100 rounded-xl flex items-center justify-center">
                {currentStep && <currentStep.icon className="w-5 h-5 text-gray-600" />}
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">{currentStep?.title}</h1>
              </div>
              <div className="ml-auto flex items-center gap-2 text-xs text-gray-400">
                <span className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center font-bold text-gray-500">
                  {step + 1}
                </span>
                <span>of {totalSteps}</span>
              </div>
            </div>
          </div>

          {/* Scrollable form */}
          <div className="flex-1 overflow-y-auto px-8 py-8">
            <div className="max-w-2xl">{renderContent()}</div>
          </div>

          {/* Footer navigation */}
          <div className="shrink-0 bg-white border-t border-gray-100 px-8 py-5 flex items-center justify-between">
            <button
              onClick={handleBack}
              className="flex items-center gap-2 rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              {step === 0 ? 'Cancel' : 'Back'}
            </button>

            <div className="flex items-center gap-3">
              {step > 0 && step < totalSteps - 1 && (
                <span className="text-xs text-gray-400">Auto-saved</span>
              )}

              {/* Don't show Continue on review step — it has its own Submit button */}
              {currentStep?.id !== 'review' && (
                step === 0 ? (
                  <button
                    onClick={handleProductsContinue}
                    disabled={!canProceed() || creatingCase}
                    className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {creatingCase ? (
                      <><Loader className="w-4 h-4 animate-spin" />Creating…</>
                    ) : (
                      <>Continue <ArrowRight className="w-4 h-4" /></>
                    )}
                  </button>
                ) : (
                  <button
                    onClick={
                      currentStep?.id === 'documents'
                        ? () => setStep((s) => s + 1)
                        : handleSectionContinue
                    }
                    disabled={!canProceed()}
                    className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Continue <ArrowRight className="w-4 h-4" />
                  </button>
                )
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
