import { ArrowLeft, CheckCircle, Clock, AlertCircle, FileText } from 'lucide-react'
import { useCaseProgress } from '@/hooks/useDocuments'
import ClientDocumentHub from '@/features/client/ClientDocumentHub'

const STAGES = ['INTAKE', 'KYC', 'PARALLEL_PRODUCTS', 'REVIEW', 'COMPLETE'] as const

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

interface Props {
  caseId: string
  onBack: () => void
}

export default function CaseDetailView({ caseId, onBack }: Props) {
  const { data: summary, isLoading } = useCaseProgress(caseId)

  const activeStageIndex = STAGES.indexOf(
    (summary?.current_stage ?? 'INTAKE') as (typeof STAGES)[number],
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              My Cases
            </button>
            {!isLoading && summary && (
              <>
                <div className="h-4 w-px bg-gray-200" />
                <div>
                  <p className="text-sm font-semibold text-gray-900">
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
                  ? 'bg-emerald-100 text-emerald-700'
                  : summary.current_stage === 'ESCALATED'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-blue-100 text-blue-700',
              ].join(' ')}
            >
              {STAGE_LABELS[summary.current_stage] ?? summary.current_stage}
            </span>
          )}
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Stage timeline */}
        <div className="rounded-2xl border border-gray-200 bg-white p-5">
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
                  {/* Step dot + label */}
                  <div className="flex flex-col items-center gap-1.5 shrink-0">
                    <div
                      className={[
                        'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold',
                        isCompleted
                          ? 'bg-emerald-500 text-white'
                          : isActive
                          ? 'bg-blue-600 text-white ring-4 ring-blue-100'
                          : 'bg-gray-100 text-gray-400',
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
                        isActive ? 'text-blue-600' : isCompleted ? 'text-gray-600' : 'text-gray-300',
                      ].join(' ')}
                    >
                      {STAGE_LABELS[stage]}
                    </span>
                  </div>
                  {/* Connector line */}
                  {!isLast && (
                    <div
                      className={[
                        'flex-1 h-0.5 mx-1',
                        isCompleted ? 'bg-emerald-300' : 'bg-gray-100',
                      ].join(' ')}
                    />
                  )}
                </div>
              )
            })}
          </div>

          {/* Progress bar */}
          {summary && (
            <div className="mt-5 pt-4 border-t border-gray-100">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400">Overall progress</span>
                <span className="text-xs font-semibold text-gray-700">
                  {summary.overall_progress ?? 0}%
                </span>
              </div>
              <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 rounded-full transition-all"
                  style={{ width: `${summary.overall_progress ?? 0}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Escalation / action banner */}
        {summary?.escalated && (
          <div className="flex items-start gap-3 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3">
            <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800">
              Your case has been escalated for enhanced review. Our compliance team will be in touch.
            </p>
          </div>
        )}

        {/* Documents */}
        <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
          <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100">
            <FileText className="w-4 h-4 text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-900">Documents</h2>
            {summary && (
              <span className="text-xs text-gray-400">
                {summary.documents_approved} of {summary.documents_total} approved
              </span>
            )}
          </div>
          <div className="p-5">
            <ClientDocumentHub caseId={caseId} />
          </div>
        </div>
      </div>
    </div>
  )
}
