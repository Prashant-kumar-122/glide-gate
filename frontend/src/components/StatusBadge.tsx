import { DOC_STATUS_COLORS, DOC_STATUS_LABEL, type DocumentStatus } from '@/design-system/tokens'

interface StatusBadgeProps {
  status: DocumentStatus
  size?: 'sm' | 'md'
  showDot?: boolean
}

export default function StatusBadge({ status, size = 'md', showDot = true }: StatusBadgeProps) {
  const colors = DOC_STATUS_COLORS[status]
  const label  = DOC_STATUS_LABEL[status]
  // IB badges: squared, tight, no pill
  const sizeClass = size === 'sm'
    ? 'px-1.5 py-0.5 text-[10px] font-medium'
    : 'px-2 py-0.5 text-[10px] font-semibold'

  return (
    <span
      className={[
        'inline-flex items-center gap-1 ring-1 ring-inset uppercase tracking-wide',
        colors.bg,
        colors.text,
        colors.ring,
        colors.dark.bg,
        colors.dark.text,
        colors.dark.ring,
        sizeClass,
      ].join(' ')}
    >
      {showDot && (
        <span className={['h-1.5 w-1.5 rounded-full shrink-0', colors.dot, colors.dark.dot].join(' ')} />
      )}
      {label}
    </span>
  )
}
