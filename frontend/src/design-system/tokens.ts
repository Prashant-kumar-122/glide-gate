export type DocumentStatus =
  | 'NOT_REQUESTED'
  | 'REQUESTED'
  | 'RECEIVED'
  | 'UNDER_REVIEW'
  | 'NEEDS_REVISION'
  | 'APPROVED'

export type TeamRole = 'Advisor' | 'Client' | 'ComplianceOfficer' | 'CCRep' | 'Admin' | 'SalesManager'

export type VisibilityLevel = 'ALL' | 'ADVISOR_ONLY' | 'CLIENT_VISIBLE'

export const DOC_STATUS_LABEL: Record<DocumentStatus, string> = {
  NOT_REQUESTED: 'Not Requested',
  REQUESTED:     'Requested',
  RECEIVED:      'Received',
  UNDER_REVIEW:  'Under Review',
  NEEDS_REVISION:'Needs Revision',
  APPROVED:      'Approved',
}

// Investment banking status colors — muted, formal, border-based
export const DOC_STATUS_COLORS: Record<
  DocumentStatus,
  { bg: string; text: string; ring: string; dot: string; dark: { bg: string; text: string; ring: string; dot: string } }
> = {
  NOT_REQUESTED: {
    bg:   'bg-gray-100',
    text: 'text-gray-500',
    ring: 'ring-gray-300/60',
    dot:  'bg-gray-400',
    dark: {
      bg:   'dark:bg-gray-800/60',
      text: 'dark:text-gray-400',
      ring: 'dark:ring-gray-600/60',
      dot:  'dark:bg-gray-500',
    },
  },
  REQUESTED: {
    bg:   'bg-blue-50',
    text: 'text-blue-700',
    ring: 'ring-blue-300/60',
    dot:  'bg-blue-500',
    dark: {
      bg:   'dark:bg-blue-950/70',
      text: 'dark:text-blue-300',
      ring: 'dark:ring-blue-700/60',
      dot:  'dark:bg-blue-400',
    },
  },
  RECEIVED: {
    bg:   'bg-violet-50',
    text: 'text-violet-700',
    ring: 'ring-violet-300/60',
    dot:  'bg-violet-500',
    dark: {
      bg:   'dark:bg-violet-950/70',
      text: 'dark:text-violet-300',
      ring: 'dark:ring-violet-700/60',
      dot:  'dark:bg-violet-400',
    },
  },
  UNDER_REVIEW: {
    bg:   'bg-amber-50',
    text: 'text-amber-700',
    ring: 'ring-amber-300/60',
    dot:  'bg-amber-500',
    dark: {
      bg:   'dark:bg-amber-950/70',
      text: 'dark:text-amber-300',
      ring: 'dark:ring-amber-700/60',
      dot:  'dark:bg-amber-400',
    },
  },
  NEEDS_REVISION: {
    bg:   'bg-red-50',
    text: 'text-red-700',
    ring: 'ring-red-300/60',
    dot:  'bg-red-500',
    dark: {
      bg:   'dark:bg-red-950/70',
      text: 'dark:text-red-300',
      ring: 'dark:ring-red-700/60',
      dot:  'dark:bg-red-400',
    },
  },
  APPROVED: {
    bg:   'bg-green-50',
    text: 'text-green-700',
    ring: 'ring-green-300/60',
    dot:  'bg-green-500',
    dark: {
      bg:   'dark:bg-green-950/70',
      text: 'dark:text-green-300',
      ring: 'dark:ring-green-700/60',
      dot:  'dark:bg-green-400',
    },
  },
}

export const ROLE_COLORS: Record<TeamRole, { bg: string; text: string; dark: { bg: string; text: string } }> = {
  Advisor: {
    bg:   'bg-blue-100',
    text: 'text-blue-800',
    dark: { bg: 'dark:bg-blue-950/80', text: 'dark:text-blue-300' },
  },
  Client: {
    bg:   'bg-emerald-100',
    text: 'text-emerald-800',
    dark: { bg: 'dark:bg-emerald-950/80', text: 'dark:text-emerald-300' },
  },
  ComplianceOfficer: {
    bg:   'bg-violet-100',
    text: 'text-violet-800',
    dark: { bg: 'dark:bg-violet-950/80', text: 'dark:text-violet-300' },
  },
  CCRep: {
    bg:   'bg-amber-100',
    text: 'text-amber-800',
    dark: { bg: 'dark:bg-amber-950/80', text: 'dark:text-amber-300' },
  },
  Admin: {
    bg:   'bg-gray-100',
    text: 'text-gray-700',
    dark: { bg: 'dark:bg-gray-800/80', text: 'dark:text-gray-300' },
  },
  SalesManager: {
    bg:   'bg-indigo-100',
    text: 'text-indigo-800',
    dark: { bg: 'dark:bg-indigo-950/80', text: 'dark:text-indigo-300' },
  },
}

export const ROLE_LABEL: Record<TeamRole, string> = {
  Advisor:           'Advisor',
  Client:            'Client',
  ComplianceOfficer: 'Compliance',
  CCRep:             'CC Rep',
  Admin:             'Admin',
  SalesManager:      'Sales Mgr',
}

export const PROGRESS_COLOR = {
  default: 'bg-blue-500',
  success: 'bg-green-500',
  warning: 'bg-amber-500',
  danger:  'bg-red-500',
} as const

export const DOC_STATUS_ORDER: DocumentStatus[] = [
  'NOT_REQUESTED',
  'REQUESTED',
  'RECEIVED',
  'UNDER_REVIEW',
  'NEEDS_REVISION',
  'APPROVED',
]
