import { DOC_STATUS_COLORS, DOC_STATUS_LABEL, type DocumentStatus } from '@/design-system/tokens'

interface StatusBadgeProps {
  status: DocumentStatus
  size?: 'sm' | 'md'
  showDot?: boolean
}

export default function StatusBadge({ status, size = 'md', showDot = true }: StatusBadgeProps) {
  const colors = DOC_STATUS_COLORS[status]
  const label = DOC_STATUS_LABEL[status]
  const sizeClass = size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium'

  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full ring-1 ring-inset',
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
        <span className={['h-1.5 w-1.5 rounded-full', colors.dot, colors.dark.dot].join(' ')} />
      )}
      {label}
    </span>
  )
}
