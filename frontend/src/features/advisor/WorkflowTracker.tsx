import { Check, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { useCaseProgress, useCaseDetail } from '@/hooks/useDocuments'

const WORKFLOW_STEPS = [
  { label: 'Intake',    stage: 'INTAKE' },
  { label: 'Review',   stage: 'REVIEW' },
  { label: 'KYC',      stage: 'KYC' },
  { label: 'Products', stage: 'PARALLEL_PRODUCTS' },
  { label: 'Complete', stage: 'COMPLETE' },
]

const STAGE_INDEX: Record<string, number> = {
  INTAKE: 0,
  REVIEW: 1,
  KYC: 2,
  PARALLEL_PRODUCTS: 3,
  COMPLETE: 4,
}

type StepStatus = 'completed' | 'current' | 'upcoming'

function stepStatus(stepIndex: number, currentStage: string): StepStatus {
  const idx = STAGE_INDEX[currentStage] ?? 0
  if (stepIndex < idx) return 'completed'
  if (stepIndex === idx) return 'current'
  return 'upcoming'
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function relativeTime(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime()
  const days = Math.floor(diffMs / 86_400_000)
  if (days > 0) return `${days}d ago`
  const hours = Math.floor(diffMs / 3_600_000)
  if (hours > 0) return `${hours}h ago`
  return `${Math.floor(diffMs / 60_000)}m ago`
}

interface Props {
  caseId: string
}

export default function WorkflowTracker({ caseId }: Props) {
  const { data: summary, isLoading: summaryLoading } = useCaseProgress(caseId)
  const { data: caseDetail } = useCaseDetail(caseId)
  const [mobileExpanded, setMobileExpanded] = useState(false)

  const currentStage = summary?.current_stage ?? 'INTAKE'
  const isEscalated = summary?.escalated ?? false

  const currentStepIndex = STAGE_INDEX[currentStage] ?? 0
  const currentStepLabel = WORKFLOW_STEPS[currentStepIndex]?.label ?? currentStage

  return (
    <aside className="flex w-full shrink-0 flex-col border-b border-gray-200/60 bg-white dark:border-gray-700/60 dark:bg-gray-900 md:w-52 md:border-b-0 md:border-r">
      {/* Mobile toggle */}
      <button
        onClick={() => setMobileExpanded((v) => !v)}
        className="flex items-center justify-between px-5 py-3 text-sm text-gray-700 dark:text-gray-300 md:hidden"
      >
        <span className="flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-gray-500">Workflow</span>
          <span className={[
            'rounded px-1.5 py-0.5 text-[10px] font-semibold',
            isEscalated ? 'bg-amber-900/50 text-amber-400' : 'bg-gray-100 dark:bg-gray-700/80 text-gray-600 dark:text-gray-300',
          ].join(' ')}>
            {isEscalated ? 'Escalated' : currentStepLabel}
          </span>
        </span>
        <ChevronDown className={['h-4 w-4 text-gray-500 transition-transform', mobileExpanded ? 'rotate-180' : ''].join(' ')} />
      </button>

      {/* Collapsible content: hidden on mobile until toggled, always visible on md+ */}
      <div className={['flex-col flex-1 overflow-y-auto', mobileExpanded ? 'flex' : 'hidden md:flex'].join(' ')}>
        <div className="border-b border-gray-200/60 dark:border-gray-700/60 px-5 py-4">
        {caseDetail ? (
          <>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-500">Case Info</p>
            <div className="mt-2.5 space-y-1.5 text-xs">
              <div className="flex justify-between gap-2">
                <span className="text-gray-400 dark:text-gray-600">ID</span>
                <span className="font-mono text-gray-500 dark:text-gray-400 truncate">{caseDetail.id.slice(0, 8)}…</span>
              </div>
              {caseDetail.assigned_advisor_name && (
                <div className="flex justify-between gap-2">
                  <span className="text-gray-400 dark:text-gray-600">Advisor</span>
                  <span className="truncate text-gray-700 dark:text-gray-300">{caseDetail.assigned_advisor_name}</span>
                </div>
              )}
              <div className="flex justify-between gap-2">
                <span className="text-gray-400 dark:text-gray-600">Created</span>
                <span className="text-gray-500 dark:text-gray-400">{fmtDate(caseDetail.created_at)}</span>
              </div>
              <div className="flex justify-between gap-2">
                <span className="text-gray-400 dark:text-gray-600">Updated</span>
                <span className="text-gray-500 dark:text-gray-400">{relativeTime(caseDetail.updated_at)}</span>
              </div>
            </div>
          </>
        ) : (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-3 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
            ))}
          </div>
        )}
      </div>

      {/* Workflow steps */}
      <div className="flex-1 py-5">
        <p className="mb-4 px-5 text-[10px] font-semibold uppercase tracking-widest text-gray-500">
          Workflow Progress
        </p>

        {summaryLoading ? (
          <div className="space-y-5 px-5">
            {WORKFLOW_STEPS.map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="h-7 w-7 animate-pulse rounded-full bg-gray-200 dark:bg-gray-800" />
                <div className="h-3 w-20 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
              </div>
            ))}
          </div>
        ) : (
          <div className="px-5">
            {WORKFLOW_STEPS.map((step, index) => {
              const status = isEscalated && step.stage === currentStage
                ? 'current'
                : stepStatus(index, currentStage)
              const isLast = index === WORKFLOW_STEPS.length - 1

              return (
                <div key={step.stage} className="flex gap-3">
                  {/* Circle + connector */}
                  <div className="flex flex-col items-center">
                    <div
                      className={[
                        'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                        status === 'completed'
                          ? 'bg-blue-600 text-white'
                          : status === 'current'
                          ? isEscalated
                            ? 'bg-amber-500 text-white ring-4 ring-amber-500/20'
                            : 'bg-blue-600 text-white ring-4 ring-blue-600/20'
                          : 'border border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-600',
                      ].join(' ')}
                    >
                      {status === 'completed' ? (
                        <Check className="h-3.5 w-3.5" />
                      ) : (
                        <span>{index + 1}</span>
                      )}
                    </div>

                    {!isLast && (
                      <div
                        className={[
                          'my-1 min-h-[28px] w-px flex-1',
                          status === 'completed' ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700',
                        ].join(' ')}
                      />
                    )}
                  </div>

                  {/* Label */}
                  <div className={isLast ? 'pb-0' : 'pb-5'}>
                    <p
                      className={[
                        'pt-0.5 text-sm font-medium',
                        status === 'current'
                          ? 'text-gray-900 dark:text-white'
                          : status === 'completed'
                          ? 'text-gray-500 dark:text-gray-400'
                          : 'text-gray-400 dark:text-gray-600',
                      ].join(' ')}
                    >
                      {step.label}
                    </p>
                    {status === 'current' && (
                      <span
                        className={[
                          'mt-1 inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold',
                          isEscalated
                            ? 'bg-amber-900/50 text-amber-400'
                            : 'bg-gray-100 dark:bg-gray-700/80 text-gray-600 dark:text-gray-300',
                        ].join(' ')}
                      >
                        {isEscalated ? 'Escalated' : 'Current'}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
      </div>
    </aside>
  )
}
