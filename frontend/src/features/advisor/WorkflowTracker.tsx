import { Check, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { useCaseProgress } from '@/hooks/useDocuments'

const WORKFLOW_STEPS_INSTITUTIONAL = [
  { label: 'Intake',         stage: 'INTAKE' },
  { label: 'Advisor Review', stage: 'REVIEW' },
  { label: 'Sales Review',   stage: 'SALES_REVIEW' },
  { label: 'KYC',            stage: 'KYC' },
  { label: 'Product Setup',  stage: 'PARALLEL_PRODUCTS' },
  { label: 'Complete',       stage: 'COMPLETE' },
]

const WORKFLOW_STEPS_RETAIL = [
  { label: 'Intake',         stage: 'INTAKE' },
  { label: 'Advisor Review', stage: 'REVIEW' },
  { label: 'KYC',            stage: 'KYC' },
  { label: 'Product Setup',  stage: 'PARALLEL_PRODUCTS' },
  { label: 'Complete',       stage: 'COMPLETE' },
]

const STAGE_INDEX_INSTITUTIONAL: Record<string, number> = {
  INTAKE: 0, REVIEW: 1, SALES_REVIEW: 2, KYC: 3, PARALLEL_PRODUCTS: 4, COMPLETE: 5,
}

const STAGE_INDEX_RETAIL: Record<string, number> = {
  INTAKE: 0, REVIEW: 1, KYC: 2, PARALLEL_PRODUCTS: 3, COMPLETE: 4,
}

type StepStatus = 'completed' | 'current' | 'upcoming'

function stepStatus(stepIndex: number, currentStage: string, stageIndex: Record<string, number>): StepStatus {
  const idx = stageIndex[currentStage] ?? 0
  if (stepIndex < idx) return 'completed'
  if (stepIndex === idx) return 'current'
  return 'upcoming'
}

interface Props { caseId: string }

export default function WorkflowTracker({ caseId }: Props) {
  const { data: summary, isLoading: summaryLoading } = useCaseProgress(caseId)
  const [mobileExpanded, setMobileExpanded] = useState(false)

  const currentStage    = summary?.current_stage ?? 'INTAKE'
  const isEscalated     = summary?.escalated ?? false
  const isInstitutional = summary?.is_institutional ?? false

  const WORKFLOW_STEPS = isInstitutional ? WORKFLOW_STEPS_INSTITUTIONAL : WORKFLOW_STEPS_RETAIL
  const STAGE_INDEX    = isInstitutional ? STAGE_INDEX_INSTITUTIONAL : STAGE_INDEX_RETAIL

  const currentStepIndex = STAGE_INDEX[currentStage] ?? 0
  const currentStepLabel = WORKFLOW_STEPS[currentStepIndex]?.label ?? currentStage

  return (
    <aside className="flex w-full shrink-0 flex-col border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950 md:w-48 md:border-b-0 md:border-r">
      {/* Mobile toggle — visible only below md */}
      <button
        onClick={() => setMobileExpanded((v) => !v)}
        className="flex items-center justify-between px-4 py-2.5 text-xs text-gray-600 dark:text-gray-400 md:hidden"
      >
        <span className="flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400">Workflow</span>
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
        {/* Workflow steps */}
        <div className="flex-1 py-4">
          <p className="mb-3 px-4 text-[10px] font-semibold uppercase tracking-widest text-gray-500 dark:text-gray-400">
            Progress
          </p>

          {summaryLoading ? (
            <div className="space-y-5 px-4">
              {WORKFLOW_STEPS.map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="h-6 w-6 animate-pulse bg-gray-200 dark:bg-gray-800" />
                  <div className="h-2 w-20 animate-pulse bg-gray-200 dark:bg-gray-800" />
                </div>
              ))}
            </div>
          ) : (
            <div className="px-4">
              {WORKFLOW_STEPS.map((step, index) => {
                const status = isEscalated && step.stage === currentStage
                  ? 'current'
                  : stepStatus(index, currentStage, STAGE_INDEX)
                const isLast = index === WORKFLOW_STEPS.length - 1

                return (
                  <div key={step.stage} className="flex gap-2.5">
                    {/* Square step indicator */}
                    <div className="flex flex-col items-center">
                      <div
                        className={[
                          'flex h-6 w-6 shrink-0 items-center justify-center text-[10px] font-bold',
                          status === 'completed'
                            ? 'bg-primary text-white'
                            : status === 'current'
                            ? isEscalated
                              ? 'bg-amber-500 text-white ring-2 ring-amber-500/30'
                              : 'bg-primary text-white ring-2 ring-primary/30'
                            : 'border border-gray-300 text-gray-400 bg-white dark:border-gray-700 dark:text-gray-600 dark:bg-transparent',
                        ].join(' ')}
                      >
                        {status === 'completed' ? <Check className="h-3 w-3" /> : <span>{index + 1}</span>}
                      </div>

                      {!isLast && (
                        <div
                          className={[
                            'my-0.5 min-h-[24px] w-px flex-1',
                            status === 'completed'
                              ? 'bg-primary/60'
                              : 'bg-gray-200 dark:bg-gray-800',
                          ].join(' ')}
                        />
                      )}
                    </div>

                    {/* Step label */}
                    <div className={isLast ? 'pb-0' : 'pb-4'}>
                      <p
                        className={[
                          'pt-0.5 text-xs font-medium',
                          status === 'current'
                            ? 'text-gray-900 dark:text-white'
                            : status === 'completed'
                            ? 'text-gray-500 dark:text-gray-500'
                            : 'text-gray-400 dark:text-gray-700',
                        ].join(' ')}
                      >
                        {step.label}
                      </p>
                      {status === 'current' && (
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
      </div>
    </aside>
  )
}
