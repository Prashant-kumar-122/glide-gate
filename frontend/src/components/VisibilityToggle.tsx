import type { VisibilityLevel } from '@/design-system/tokens'

interface VisibilityToggleProps {
  value: VisibilityLevel
  onChange: (v: VisibilityLevel) => void
  disabled?: boolean
}

const OPTIONS: { value: VisibilityLevel; label: string }[] = [
  { value: 'ALL', label: 'All' },
  { value: 'ADVISOR_ONLY', label: 'Advisor' },
  { value: 'CLIENT_VISIBLE', label: 'Client' },
]

export default function VisibilityToggle({ value, onChange, disabled = false }: VisibilityToggleProps) {
  return (
    <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          disabled={disabled}
          className={[
            'rounded-md px-3 py-1 text-xs font-medium transition-all',
            value === opt.value
              ? 'bg-white text-gray-900 shadow-sm ring-1 ring-gray-200'
              : 'text-gray-500 hover:text-gray-700',
            disabled ? 'cursor-not-allowed opacity-50' : '',
          ].join(' ')}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
