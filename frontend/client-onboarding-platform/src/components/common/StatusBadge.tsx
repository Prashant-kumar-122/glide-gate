import type { CaseStatus, TaskStatus, AccountStatus, DocumentStatus, WorkflowStage } from '../../types';

// ─── Variant config ───────────────────────────────────────────────────────────

type BadgeVariant = 'info' | 'warning' | 'success' | 'danger' | 'muted' | 'primary';

interface BadgeConfig {
  label: string;
  variant: BadgeVariant;
}

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  info:    'bg-info-subtle    text-info    border border-info/20',
  warning: 'bg-warning-subtle text-warning border border-warning/20',
  success: 'bg-success-subtle text-success border border-success/20',
  danger:  'bg-danger-subtle  text-danger  border border-danger/20',
  muted:   'bg-bg-elevated    text-text-muted border border-border-default',
  primary: 'bg-primary-subtle text-primary  border border-primary/20',
};

// ─── Status → config maps ─────────────────────────────────────────────────────

const CASE_STATUS_MAP: Record<CaseStatus, BadgeConfig> = {
  active:       { label: 'Active',       variant: 'info'    },
  pending_info: { label: 'Pending Info', variant: 'warning' },
  approved:     { label: 'Approved',     variant: 'success' },
  rejected:     { label: 'Rejected',     variant: 'danger'  },
  completed:    { label: 'Completed',    variant: 'success' },
};

const TASK_STATUS_MAP: Record<TaskStatus, BadgeConfig> = {
  pending:        { label: 'Pending',        variant: 'muted'   },
  in_review:      { label: 'In Review',      variant: 'info'    },
  approved:       { label: 'Approved',       variant: 'success' },
  rejected:       { label: 'Rejected',       variant: 'danger'  },
  info_requested: { label: 'Info Requested', variant: 'warning' },
};

const ACCOUNT_STATUS_MAP: Record<AccountStatus, BadgeConfig> = {
  in_progress: { label: 'In Progress', variant: 'info'    },
  live:        { label: 'Live',        variant: 'success' },
  suspended:   { label: 'Suspended',   variant: 'warning' },
  closed:      { label: 'Closed',      variant: 'muted'   },
};

const DOCUMENT_STATUS_MAP: Record<DocumentStatus, BadgeConfig> = {
  uploaded:     { label: 'Uploaded',     variant: 'info'    },
  under_review: { label: 'Under Review', variant: 'warning' },
  approved:     { label: 'Approved',     variant: 'success' },
  rejected:     { label: 'Rejected',     variant: 'danger'  },
};

const WORKFLOW_STAGE_MAP: Record<WorkflowStage, BadgeConfig> = {
  CLIENT_ENROLLMENT:    { label: 'Client Enrollment', variant: 'primary' },
  SALES_MANAGER_REVIEW: { label: 'Sales Review',      variant: 'primary' },
  KYC:                  { label: 'KYC',               variant: 'primary' },
  DUE_DILIGENCE:        { label: 'Due Diligence',     variant: 'primary' },
  SIGN_AND_EXECUTE:     { label: 'Sign & Execute',    variant: 'primary' },
  ACCOUNT_SETUP:        { label: 'Account Setup',     variant: 'primary' },
  LIVE:                 { label: 'Live',              variant: 'primary' },
};

// ─── Lookup helper ────────────────────────────────────────────────────────────

function resolveConfig(status: string): BadgeConfig {
  if (status in CASE_STATUS_MAP)     return CASE_STATUS_MAP[status as CaseStatus];
  if (status in TASK_STATUS_MAP)     return TASK_STATUS_MAP[status as TaskStatus];
  if (status in ACCOUNT_STATUS_MAP)  return ACCOUNT_STATUS_MAP[status as AccountStatus];
  if (status in DOCUMENT_STATUS_MAP) return DOCUMENT_STATUS_MAP[status as DocumentStatus];
  if (status in WORKFLOW_STAGE_MAP)  return WORKFLOW_STAGE_MAP[status as WorkflowStage];
  // Fallback: format the raw key as a readable label
  return {
    label: status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    variant: 'muted',
  };
}

// ─── Component ────────────────────────────────────────────────────────────────

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const { label, variant } = resolveConfig(status);
  return (
    <span
      className={[
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap',
        VARIANT_CLASSES[variant],
        className,
      ].join(' ')}
    >
      {label}
    </span>
  );
}

export default StatusBadge;
