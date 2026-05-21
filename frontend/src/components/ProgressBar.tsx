interface ProgressBarProps {
  value: number
  label?: string
  showPercent?: boolean
  color?: 'default' | 'success' | 'warning' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

const COLOR_MAP = {
  default: 'bg-blue-500',
  success: 'bg-green-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
}

const SIZE_MAP = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
}

export default function ProgressBar({
  value,
  label,
  showPercent = false,
  color = 'default',
  size = 'md',
}: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value))
  const barColor = clamped === 100 ? 'bg-green-500' : COLOR_MAP[color]

  return (
    <div className="w-full">
      {(label || showPercent) && (
        <div className="mb-1 flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
          {label && <span>{label}</span>}
          {showPercent && <span className="tabular-nums">{clamped}%</span>}
        </div>
      )}
      <div className={['w-full rounded-full bg-gray-200 dark:bg-gray-700', SIZE_MAP[size]].join(' ')}>
        <div
          className={['rounded-full transition-all duration-500', barColor, SIZE_MAP[size]].join(' ')}
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
