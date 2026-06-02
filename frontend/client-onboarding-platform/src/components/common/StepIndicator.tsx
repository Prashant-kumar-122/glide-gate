import { IconCheck } from '@tabler/icons-react';

interface StepIndicatorProps {
  steps: string[];
  currentStep: number;   // 0-indexed
  completedSteps: number[];
}

export function StepIndicator({ steps, currentStep, completedSteps }: StepIndicatorProps) {
  const completed = new Set(completedSteps);

  return (
    <div className="flex items-start w-full">
      {steps.map((label, index) => {
        const isCompleted = completed.has(index);
        const isCurrent   = index === currentStep;
        const isLast      = index === steps.length - 1;

        return (
          <div key={index} className="flex flex-1 flex-col items-center min-w-0">
            {/* Circle + connector row */}
            <div className="flex items-center w-full">
              {/* Left connector line */}
              <div
                className={[
                  'flex-1 h-px',
                  index === 0 ? 'invisible' : isCompleted ? 'bg-primary' : 'bg-border-default',
                ].join(' ')}
              />

              {/* Circle */}
              <div
                className={[
                  'relative flex items-center justify-center w-8 h-8 rounded-full flex-shrink-0 transition-all duration-200',
                  isCompleted
                    ? 'bg-primary border-2 border-primary'
                    : isCurrent
                    ? 'bg-bg-surface border-2 border-primary ring-4 ring-primary/20'
                    : 'bg-bg-surface border-2 border-border-default',
                ].join(' ')}
              >
                {isCompleted ? (
                  <IconCheck size={14} className="text-white" strokeWidth={2.5} />
                ) : (
                  <span
                    className={[
                      'text-xs font-semibold',
                      isCurrent  ? 'text-primary'      : 'text-text-muted',
                    ].join(' ')}
                  >
                    {index + 1}
                  </span>
                )}
              </div>

              {/* Right connector line */}
              <div
                className={[
                  'flex-1 h-px',
                  isLast     ? 'invisible' : completed.has(index + 1) || isCompleted
                                             ? 'bg-primary'
                                             : 'bg-border-default',
                ].join(' ')}
              />
            </div>

            {/* Label */}
            <p
              className={[
                'mt-2 text-xs text-center font-medium truncate w-full px-1',
                isCompleted
                  ? 'text-primary'
                  : isCurrent
                  ? 'text-text-primary'
                  : 'text-text-muted',
              ].join(' ')}
              title={label}
            >
              {label}
            </p>
          </div>
        );
      })}
    </div>
  );
}

export default StepIndicator;
