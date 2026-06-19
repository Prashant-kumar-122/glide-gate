import { useState } from 'react'
import { ArrowLeft, AlertCircle, FileText, ClipboardList, Check, ChevronDown, Package } from 'lucide-react'
import { useCaseProgress, useQuestionnaireSchema, useCollectedFields } from '@/hooks/useDocuments'
import ClientDocumentHub from '@/features/client/ClientDocumentHub'
import OnboardingFormView from '@/features/client/OnboardingFormView'
import ParallelProductTracks from '@/features/advisor/ParallelProductTracks'

// Retail:        Application → Documents → KYC Review → Account Setup → Complete
// Institutional: Application → Documents → Sales Review → KYC Review → Account Setup → Complete
const STAGES_RETAIL        = ['INTAKE', 'REVIEW', 'KYC', 'PARALLEL_PRODUCTS', 'COMPLETE'] as const
const STAGES_INSTITUTIONAL = ['INTAKE', 'REVIEW', 'SALES_REVIEW', 'KYC', 'PARALLEL_PRODUCTS', 'COMPLETE'] as const

const STAGE_LABELS: Record<string, string> = {
  INTAKE:            'Application',
  REVIEW:            'Documents',
  SALES_REVIEW:      'Sales Review',
  KYC:               'KYC Review',
  PARALLEL_PRODUCTS: 'Account Setup',
  COMPLETE:          'Complete',
  ESCALATED:         'Escalated',
}

function formatProductNames(products: string[]): string {
  return products
    .map((p) => p.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()))
    .join(' · ')
}

type Tab = 'products' | 'application' | 'documents'

interface Props {
  caseId: string
  onBack: () => void
}

export default function CaseDetailView({ caseId, onBack }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('products')
  const [mobileExpanded, setMobileExpanded] = useState(false)

  const { data: summary, isLoading } = useCaseProgress(caseId)
  const { data: schemaData, isLoading: schemaLoading } = useQuestionnaireSchema(caseId)
  const { data: collectedData, isLoading: collectedLoading } = useCollectedFields(caseId)


  const isInstitutional = summary?.is_institutional ?? false
  const isEscalated     = summary?.escalated ?? false
  const STAGES: readonly string[] = isInstitutional ? STAGES_INSTITUTIONAL : STAGES_RETAIL

  const activeStageIndex = STAGES.indexOf(summary?.current_stage ?? 'INTAKE')
  const currentStepLabel = STAGE_LABELS[summary?.current_stage ?? 'INTAKE'] ?? (summary?.current_stage ?? 'Application')

  const tabs: { id: Tab; label: string; icon: typeof ClipboardList }[] = [
    { id: 'products',    label: 'Product Tracks', icon: Package },
    { id: 'application', label: 'Application',    icon: ClipboardList },
    { id: 'documents',   label: 'Documents',      icon: FileText },
  ]

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="shrink-0 z-10 bg-white border-b border-gray-200 px-6 py-4 dark:bg-gray-800 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 transition-colors dark:text-gray-400 dark:hover:text-gray-100"
            >
              <ArrowLeft className="w-4 h-4" />
              My Cases
            </button>
            {!isLoading && summary && (
              <>
                <div className="h-4 w-px bg-gray-200 dark:bg-gray-600" />
                <div>
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {formatProductNames(summary.products?.map((p) => p.product_code) ?? [])}
                  </p>
                  <p className="text-xs text-gray-400">{summary.client_name}</p>
                </div>
              </>
            )}
          </div>

          {summary && (
            <span
              className={[
                'text-xs font-semibold px-2.5 py-1 rounded-full',
                summary.current_stage === 'COMPLETE'
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'
                  : summary.current_stage === 'ESCALATED'
                  ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                  : 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
              ].join(' ')}
            >
              {STAGE_LABELS[summary.current_stage] ?? summary.current_stage}
            </span>
          )}
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 flex-col overflow-hidden md:flex-row">
        {/* Left sidebar — vertical stage tracker */}
        <aside className="flex w-full shrink-0 flex-col border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950 md:w-56 md:border-b-0 md:border-r">
          {/* Mobile toggle — visible only below md */}
          <button
            onClick={() => setMobileExpanded((v) => !v)}
            className="flex items-center justify-between px-4 py-2.5 text-xs text-gray-600 dark:text-gray-400 md:hidden"
          >
            <span className="flex items-center gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400">Progress</span>
              <span className={[
                'px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                isEscalated
                  ? 'border border-amber-300 bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400 dark:border-amber-700/30'
                  : 'border border-gray-200 bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700',
              ].join(' ')}>
                {isEscalated ? 'Escalated' : currentStepLabel}
              </span>
            </span>
            <ChevronDown className={['h-3.5 w-3.5 text-gray-400 transition-transform', mobileExpanded ? 'rotate-180' : ''].join(' ')} />
          </button>

          {/* Collapsible body */}
          <div className={['flex-col flex-1 overflow-y-auto', mobileExpanded ? 'flex' : 'hidden md:flex'].join(' ')}>
            <div className="flex-1 py-4">
              <p className="mb-3 px-4 text-[10px] font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400">
                Application Progress
              </p>

              {isLoading ? (
                <div className="space-y-5 px-4">
                  {STAGES.map((_, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="h-6 w-6 animate-pulse bg-gray-200 dark:bg-gray-800" />
                      <div className="h-2 w-20 animate-pulse bg-gray-200 dark:bg-gray-800" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="px-4">
                  {STAGES.map((stage, idx) => {
                    const isCompleted = idx < activeStageIndex
                    const isActive    = idx === activeStageIndex
                    const isLast      = idx === STAGES.length - 1

                    return (
                      <div key={stage} className="flex gap-2.5">
                        {/* Square step indicator */}
                        <div className="flex flex-col items-center">
                          <div
                            className={[
                              'flex h-6 w-6 shrink-0 items-center justify-center text-[10px] font-bold',
                              isCompleted
                                ? 'bg-primary text-white'
                                : isActive
                                ? isEscalated
                                  ? 'bg-amber-500 text-white ring-2 ring-amber-500/30'
                                  : 'bg-primary text-white ring-2 ring-primary/30'
                                : 'border border-gray-300 text-gray-400 bg-white dark:border-gray-700 dark:text-gray-600 dark:bg-transparent',
                            ].join(' ')}
                          >
                            {isCompleted ? <Check className="h-3 w-3" /> : <span>{idx + 1}</span>}
                          </div>

                          {!isLast && (
                            <div
                              className={[
                                'my-0.5 min-h-[24px] w-px flex-1',
                                isCompleted ? 'bg-primary/60' : 'bg-gray-200 dark:bg-gray-800',
                              ].join(' ')}
                            />
                          )}
                        </div>

                        {/* Step label */}
                        <div className={isLast ? 'pb-0' : 'pb-4'}>
                          <p
                            className={[
                              'pt-0.5 text-xs font-medium',
                              isActive
                                ? 'text-gray-900 dark:text-white'
                                : isCompleted
                                ? 'text-gray-500 dark:text-gray-500'
                                : 'text-gray-400 dark:text-gray-700',
                            ].join(' ')}
                          >
                            {STAGE_LABELS[stage]}
                          </p>
                          {isActive && (
                            <span
                              className={[
                                'mt-1 inline-block px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide',
                                isEscalated
                                  ? 'border border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-700/30 dark:bg-amber-950/60 dark:text-amber-400'
                                  : 'border border-blue-200 bg-blue-50 text-blue-700 dark:border-primary/20 dark:bg-primary-subtle dark:text-primary',
                              ].join(' ')}
                            >
                              {isEscalated ? 'Escalated' : 'Active'}
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Overall progress bar at the bottom of sidebar */}
            {summary && (
              <div className="border-t border-gray-100 px-4 py-4 dark:border-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-400">Overall</span>
                  <span className="text-xs font-semibold text-gray-700 dark:text-gray-200">
                    {summary.overall_progress ?? 0}%
                  </span>
                </div>
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden dark:bg-gray-700">
                  <div
                    className="h-full bg-blue-600 rounded-full transition-all"
                    style={{ width: `${summary.overall_progress ?? 0}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto px-6 py-6 space-y-6 bg-gray-50 dark:bg-gray-900">
          {/* Escalation banner */}
          {summary?.escalated && (
            <div className="flex items-start gap-3 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 dark:bg-amber-950 dark:border-amber-800">
              <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <p className="text-sm text-amber-800 dark:text-amber-300">
                Your case has been escalated for enhanced review. Our compliance team will be in touch.
              </p>
            </div>
          )}

          {/* Tabs */}
          <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden dark:border-gray-700 dark:bg-gray-800">
            {/* Tab bar */}
            <div className="flex border-b border-gray-200 dark:border-gray-700">
              {tabs.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id)}
                  className={[
                    'flex flex-1 items-center justify-center gap-2 py-3.5 text-sm font-medium border-b-2 transition-colors',
                    activeTab === id
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200',
                  ].join(' ')}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="p-5">
              {activeTab === 'products' && (
                <ParallelProductTracks
                  tracks={summary?.products ?? []}
                  isLoading={isLoading}
                  caseId={caseId}
                />
              )}

              {activeTab === 'application' && (
                <OnboardingFormView
                  caseId={caseId}
                  clientData={collectedData?.client_data ?? {}}
                  schema={schemaData?.fields ?? []}
                  isLoading={schemaLoading || collectedLoading}
                  readOnly={summary?.current_stage !== 'REVIEW'}
                />
              )}

              {activeTab === 'documents' && (
                <ClientDocumentHub caseId={caseId} readOnly={summary?.current_stage !== 'REVIEW'} />
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
