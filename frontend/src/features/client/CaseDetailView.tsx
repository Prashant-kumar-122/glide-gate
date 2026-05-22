import { useState } from 'react'
import { ArrowLeft, CheckCircle, Clock, AlertCircle, FileText, ClipboardList, BadgeCheck } from 'lucide-react'
import { useCaseProgress, useQuestionnaireSchema, useCollectedFields, useAccount } from '@/hooks/useDocuments'
import ClientDocumentHub from '@/features/client/ClientDocumentHub'
import OnboardingFormView from '@/features/client/OnboardingFormView'

const STAGES = ['INTAKE', 'PARALLEL_PRODUCTS', 'KYC', 'REVIEW', 'COMPLETE'] as const

const STAGE_LABELS: Record<string, string> = {
  INTAKE: 'Application',
  KYC: 'KYC Review',
  PARALLEL_PRODUCTS: 'Documents',
  REVIEW: 'Final Review',
  COMPLETE: 'Complete',
  ESCALATED: 'Escalated',
}

function formatProductNames(products: string[]): string {
  return products
    .map((p) => p.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()))
    .join(' · ')
}

type Tab = 'application' | 'documents'

interface Props {
  caseId: string
  onBack: () => void
}

export default function CaseDetailView({ caseId, onBack }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('application')

  const { data: summary, isLoading } = useCaseProgress(caseId)
  const { data: schemaData, isLoading: schemaLoading } = useQuestionnaireSchema(caseId)
  const { data: collectedData, isLoading: collectedLoading } = useCollectedFields(caseId)
  const { data: account } = useAccount(caseId, summary?.current_stage === 'COMPLETE')

  const activeStageIndex = STAGES.indexOf(
    (summary?.current_stage ?? 'INTAKE') as (typeof STAGES)[number],
  )

  const tabs: { id: Tab; label: string; icon: typeof ClipboardList }[] = [
    { id: 'application', label: 'Application', icon: ClipboardList },
    { id: 'documents',   label: 'Documents',   icon: FileText },
  ]

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4 dark:bg-gray-800 dark:border-gray-700">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
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

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Stage timeline */}
        <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
            Application Progress
          </h2>
          <div className="flex items-center gap-0">
            {STAGES.map((stage, idx) => {
              const isCompleted = idx < activeStageIndex
              const isActive = idx === activeStageIndex
              const isLast = idx === STAGES.length - 1
              return (
                <div key={stage} className="flex items-center flex-1 min-w-0">
                  <div className="flex flex-col items-center gap-1.5 shrink-0">
                    <div
                      className={[
                        'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold',
                        isCompleted
                          ? 'bg-emerald-500 text-white'
                          : isActive
                          ? 'bg-blue-600 text-white ring-4 ring-blue-100 dark:ring-blue-900'
                          : 'bg-gray-100 text-gray-400 dark:bg-gray-700 dark:text-gray-500',
                      ].join(' ')}
                    >
                      {isCompleted ? (
                        <CheckCircle className="w-3.5 h-3.5" />
                      ) : isActive ? (
                        <Clock className="w-3.5 h-3.5" />
                      ) : (
                        <span>{idx + 1}</span>
                      )}
                    </div>
                    <span
                      className={[
                        'text-xs font-medium text-center leading-tight',
                        isActive ? 'text-blue-600 dark:text-blue-400' : isCompleted ? 'text-gray-600 dark:text-gray-300' : 'text-gray-300 dark:text-gray-600',
                      ].join(' ')}
                    >
                      {STAGE_LABELS[stage]}
                    </span>
                  </div>
                  {!isLast && (
                    <div
                      className={[
                        'flex-1 h-0.5 mx-1',
                        isCompleted ? 'bg-emerald-300 dark:bg-emerald-700' : 'bg-gray-100 dark:bg-gray-700',
                      ].join(' ')}
                    />
                  )}
                </div>
              )
            })}
          </div>

          {/* Progress bar */}
          {summary && (
            <div className="mt-5 pt-4 border-t border-gray-100 dark:border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400">Overall progress</span>
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

        {/* Escalation banner */}
        {summary?.escalated && (
          <div className="flex items-start gap-3 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 dark:bg-amber-950 dark:border-amber-800">
            <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800 dark:text-amber-300">
              Your case has been escalated for enhanced review. Our compliance team will be in touch.
            </p>
          </div>
        )}

        {/* Account number banner */}
        {account && (
          <div className="flex items-center justify-between gap-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 dark:border-emerald-800 dark:bg-emerald-950">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-100 dark:bg-emerald-900 flex items-center justify-center shrink-0">
                <BadgeCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="text-xs font-medium text-emerald-700 dark:text-emerald-400 uppercase tracking-wide">Account Number</p>
                <p className="text-lg font-bold text-emerald-900 dark:text-emerald-100 tracking-wider font-mono">
                  {account.account_number}
                </p>
              </div>
            </div>
            <div className="text-right hidden sm:block">
              <p className="text-xs text-emerald-600 dark:text-emerald-400">Onboarding complete</p>
              <p className="text-xs text-emerald-500 dark:text-emerald-500 mt-0.5">
                {new Date(account.created_at).toLocaleDateString()}
              </p>
            </div>
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
            {activeTab === 'application' && (
              <OnboardingFormView
                caseId={caseId}
                clientData={collectedData?.client_data ?? {}}
                schema={schemaData?.fields ?? []}
                isLoading={schemaLoading || collectedLoading}
                readOnly={summary?.current_stage === 'KYC' || summary?.current_stage === 'COMPLETE'}
              />
            )}

            {activeTab === 'documents' && (
              <ClientDocumentHub caseId={caseId} readOnly={summary?.current_stage === 'KYC' || summary?.current_stage === 'COMPLETE'} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
