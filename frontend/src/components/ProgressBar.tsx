interface ProgressBarProps {
  value: number
  label?: string
  showPercent?: boolean
  color?: 'default' | 'success' | 'warning' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

const COLOR_MAP = {
  default: 'bg-primary',
  success: 'bg-green-500',
  warning: 'bg-amber-500',
  danger:  'bg-red-500',
}

const SIZE_MAP = {
  sm: 'h-1',
  md: 'h-1.5',
  lg: 'h-2',
}

export default function ProgressBar({
  value,
  label,
  showPercent = false,
  color = 'default',
  size = 'md',
}: ProgressBarProps) {
  const clamped  = Math.min(100, Math.max(0, value))
  const barColor = clamped === 100 ? 'bg-green-500' : COLOR_MAP[color]

  return (
    <div className="w-full">
      {(label || showPercent) && (
        <div className="mb-1 flex items-center justify-between text-[10px] text-gray-500">
          {label && <span>{label}</span>}
          {showPercent && <span className="font-mono tabular-nums">{clamped}%</span>}
        </div>
      )}
      {/* Square-capped track — no rounded-full */}
      <div className={['w-full bg-gray-200 dark:bg-gray-800', SIZE_MAP[size]].join(' ')}>
        <div
          className={['transition-all duration-500', barColor, SIZE_MAP[size]].join(' ')}
          style={{ width: `${clamped}%` }}
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  )
}
