import { ROLE_COLORS, ROLE_LABEL, type TeamRole } from '@/design-system/tokens'

interface RoleBadgeProps {
  role: TeamRole
  size?: 'sm' | 'md'
}

export default function RoleBadge({ role, size = 'md' }: RoleBadgeProps) {
  const colors = ROLE_COLORS[role]
  const label = ROLE_LABEL[role]
  const sizeClass = size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-0.5 text-xs font-medium'

  return (
    <span
      className={[
        'inline-flex items-center rounded',
        colors.bg,
        colors.text,
        sizeClass,
      ].join(' ')}
    >
      {label}
    </span>
  )
}
