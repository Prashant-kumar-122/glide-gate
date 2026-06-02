import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  IconArrowLeft,
  IconAlertCircle,
  IconCheck,
  IconX,
  IconMessageQuestion,
  IconChevronDown,
  IconChevronUp,
  IconClipboardText,
  IconUser,
  IconBuildingCommunity,
} from '@tabler/icons-react';
import {
  casesService,
  tasksService,
  formsService,
} from '../../../mocks/services/cases.service';
import { PageHeader } from '../../../components/common/PageHeader';
import { StatusBadge } from '../../../components/common/StatusBadge';
import {
  PRODUCT_LABELS,
  TASK_TYPE_LABELS,
  STAGE_LABELS,
} from '../../../types';
import type {
  TaskStatus,
  EnrollmentFormData,
  CDDFormData,
  ControlPersonFormData,
  FormSubmission,
} from '../../../types';
import { formatDate, formatDateTime } from '../../../utils/formatters';

// ─── Read-only field ──────────────────────────────────────────────────────────

function Field({ label, value }: { label: string; value: string | number | boolean | undefined }) {
  const display =
    value === undefined || value === '' ? '—'
    : typeof value === 'boolean' ? (value ? 'Yes' : 'No')
    : String(value);
  return (
    <div>
      <p className="text-xs text-text-muted mb-0.5">{label}</p>
      <p className="text-sm text-text-primary font-medium">{display}</p>
    </div>
  );
}

// ─── Enrollment form viewer ───────────────────────────────────────────────────

function EnrollmentFormViewer({ data }: { data: EnrollmentFormData }) {
  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-1.5">
          <IconBuildingCommunity size={13} />
          Entity Details
        </p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          <Field label="Legal Name"          value={data.legalName} />
          <Field label="Tax ID (EIN)"        value={data.taxId} />
          <Field label="Business Type"       value={data.businessType} />
          <Field label="Incorporation State" value={data.incorporationState} />
          <Field label="Incorporation Date"  value={data.incorporationDate} />
        </div>
      </div>
      <div className="border-t border-border-subtle pt-4">
        <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
          Registered Address
        </p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          <Field label="Street"  value={data.address.line1} />
          {data.address.line2 && <Field label="Suite / Unit" value={data.address.line2} />}
          <Field label="City"    value={data.address.city} />
          <Field label="State"   value={data.address.state} />
          <Field label="ZIP"     value={data.address.zip} />
          <Field label="Country" value={data.address.country} />
        </div>
      </div>
      <div className="border-t border-border-subtle pt-4">
        <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-1.5">
          <IconUser size={13} />
          Primary Contact
        </p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3">
          <Field label="Full Name" value={data.primaryContact.fullName} />
          <Field label="Title"     value={data.primaryContact.title} />
          <Field label="Email"     value={data.primaryContact.email} />
          <Field label="Phone"     value={data.primaryContact.phone} />
        </div>
      </div>
    </div>
  );
}

// ─── CDD form viewer ──────────────────────────────────────────────────────────

function CDDFormViewer({ data }: { data: CDDFormData }) {
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-3">
      <div className="col-span-2">
        <Field label="Nature of Business"     value={data.natureOfBusiness} />
      </div>
      <Field label="Source of Funds"          value={data.sourceOfFunds} />
      <Field label="Expected Trading Volume"  value={data.expectedTradingVolume} />
      <div className="col-span-2">
        <Field label="Operating Jurisdictions" value={data.jurisdictions.join(', ')} />
      </div>
      <Field label="PEP Status"               value={data.pepStatus} />
      <Field label="Sanctions Status"         value={data.sanctionsStatus} />
    </div>
  );
}

// ─── Control person form viewer ───────────────────────────────────────────────

function ControlPersonFormViewer({ data }: { data: ControlPersonFormData }) {
  return (
    <div className="space-y-4">
      {data.controlPersons.map((p, i) => (
        <div key={i} className="bg-bg-base rounded-lg p-3 border border-border-subtle">
          <p className="text-xs font-semibold text-text-secondary mb-2">
            Control Person {i + 1}
            <span className="ml-2 font-normal text-text-muted">
              {p.ownershipPercentage}% ownership
            </span>
          </p>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2">
            <Field label="Full Name"        value={p.fullName} />
            <Field label="Title"            value={p.title} />
            <Field label="Date of Birth"    value={p.dateOfBirth} />
            <Field label="Nationality"      value={p.nationality} />
            <Field label="ID Type"          value={p.idDocumentType} />
            <Field label="ID Number"        value={p.idDocumentNumber} />
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Form submission card (expandable) ───────────────────────────────────────

const FORM_LABELS: Record<string, string> = {
  ENROLLMENT:     'Enrollment Form',
  CDD:            'Customer Due Diligence (CDD)',
  CONTROL_PERSON: 'Control Persons',
};

const FORM_ICONS: Record<string, React.ReactNode> = {
  ENROLLMENT:     <IconBuildingCommunity size={14} />,
  CDD:            <IconClipboardText size={14} />,
  CONTROL_PERSON: <IconUser size={14} />,
};

function FormCard({
  form,
  defaultOpen = false,
}: {
  form: FormSubmission;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  const isPending = form.status === 'pending_review';

  return (
    <div
      className={[
        'rounded-lg border overflow-hidden',
        isPending
          ? 'border-border-default bg-bg-elevated'
          : 'border-border-subtle bg-bg-surface opacity-80',
      ].join(' ')}
    >
      {/* Header */}
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-bg-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className={isPending ? 'text-primary' : 'text-text-muted'}>
            {FORM_ICONS[form.type]}
          </span>
          <span className={`text-sm font-medium ${isPending ? 'text-text-primary' : 'text-text-secondary'}`}>
            {FORM_LABELS[form.type]}
          </span>
          {!isPending && (
            <span className="text-xs text-text-muted italic">(read-only)</span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusBadge status={form.status} />
          <span className="text-text-muted">
            {open ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
          </span>
        </div>
      </button>

      {/* Body */}
      {open && (
        <div className={`px-4 pb-4 pt-1 border-t border-border-subtle ${!isPending ? 'pointer-events-none select-none' : ''}`}>
          {form.type === 'ENROLLMENT' && (
            <EnrollmentFormViewer data={form.data as EnrollmentFormData} />
          )}
          {form.type === 'CDD' && (
            <CDDFormViewer data={form.data as CDDFormData} />
          )}
          {form.type === 'CONTROL_PERSON' && (
            <ControlPersonFormViewer data={form.data as ControlPersonFormData} />
          )}
        </div>
      )}
    </div>
  );
}

// ─── Which form types are relevant per task type ──────────────────────────────

const TASK_TO_FORM_TYPES: Record<string, string[]> = {
  ENROLLMENT_FORM_REVIEW: ['ENROLLMENT'],
  DOCUMENT_VERIFICATION:  ['ENROLLMENT'],
  KYC_REVIEW:             ['ENROLLMENT', 'CDD', 'CONTROL_PERSON'],
  COMPLIANCE_CHECK:       ['CDD', 'CONTROL_PERSON'],
  SIGN_AND_EXECUTE:       ['ENROLLMENT', 'CDD', 'CONTROL_PERSON'],
};

// ─── Action panel type ────────────────────────────────────────────────────────

type ActivePanel = 'approve' | 'reject' | 'request_info' | null;

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TaskDetailPage({ taskId: taskIdProp, embedded = false }: { taskId?: string; embedded?: boolean } = {}) {
  const { taskId: routeTaskId } = useParams<{ taskId: string }>();
  const taskId = taskIdProp ?? routeTaskId;
  const queryClient = useQueryClient();

  const [activePanel, setActivePanel] = useState<ActivePanel>(null);
  const [notes, setNotes] = useState('');
  const [message, setMessage] = useState('');
  const [successAction, setSuccessAction] = useState<TaskStatus | null>(null);

  // ── Queries ──────────────────────────────────────────────────────────────────

  const { data: task, isLoading: taskLoading } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => tasksService.getTaskById(taskId!),
    enabled: !!taskId,
  });

  const { data: caseData, isLoading: caseLoading } = useQuery({
    queryKey: ['case', task?.caseId],
    queryFn: () => casesService.getCaseById(task!.caseId),
    enabled: !!task?.caseId,
  });

  const { data: allForms = [] } = useQuery({
    queryKey: ['forms', 'case', task?.caseId],
    queryFn: () => formsService.getFormsByCase(task!.caseId),
    enabled: !!task?.caseId,
  });

  // Filter forms relevant to this task type
  const relevantFormTypes = task ? (TASK_TO_FORM_TYPES[task.type] ?? []) : [];
  const relevantForms = allForms.filter(f => relevantFormTypes.includes(f.type));

  // ── Mutations ────────────────────────────────────────────────────────────────

  const approveMutation = useMutation({
    mutationFn: () => tasksService.approveTask(taskId!, notes || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setSuccessAction('approved');
      setActivePanel(null);
      setNotes('');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => tasksService.rejectTask(taskId!, notes || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setSuccessAction('rejected');
      setActivePanel(null);
      setNotes('');
    },
  });

  const requestInfoMutation = useMutation({
    mutationFn: () => tasksService.requestInfo(taskId!, message),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setSuccessAction('info_requested');
      setActivePanel(null);
      setMessage('');
    },
  });

  // ── Helpers ───────────────────────────────────────────────────────────────

  function togglePanel(panel: ActivePanel) {
    setActivePanel(prev => (prev === panel ? null : panel));
    setNotes('');
    setMessage('');
  }

  const isResolved =
    task?.status === 'approved' ||
    task?.status === 'rejected' ||
    task?.status === 'info_requested' ||
    successAction !== null;

  const isPending =
    approveMutation.isPending ||
    rejectMutation.isPending ||
    requestInfoMutation.isPending;

  // ── Loading ────────────────────────────────────────────────────────────────

  if (taskLoading || caseLoading) {
    return (
      <div className={embedded ? 'p-6' : 'p-8'}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 w-40 bg-bg-elevated rounded" />
          <div className="h-10 w-72 bg-bg-elevated rounded" />
          <div className="grid grid-cols-5 gap-6">
            <div className="col-span-3 h-64 bg-bg-surface border border-border-default rounded-xl" />
            <div className="col-span-2 h-64 bg-bg-surface border border-border-default rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className={`${embedded ? 'p-6' : 'p-8'} flex flex-col items-center justify-center gap-4 py-24`}>
        <IconAlertCircle size={40} className="text-danger" />
        <p className="text-text-secondary text-lg">Task not found.</p>
        {!embedded && (
          <Link to="/internal/dashboard" className="flex items-center gap-2 text-primary hover:underline">
            <IconArrowLeft size={16} />
            Back to Dashboard
          </Link>
        )}
      </div>
    );
  }

  return (
    <div className={embedded ? 'p-5' : 'p-8'}>
      {!embedded && (
        <PageHeader
          title={TASK_TYPE_LABELS[task.type]}
          actions={
            <span className="font-mono text-xs px-2 py-1 rounded bg-bg-elevated border border-border-default text-text-muted">
              {task.caseId}
            </span>
          }
        />
      )}

      {/* Two-column layout */}
      <div className="grid grid-cols-5 gap-6">

        {/* ── Left: 3 cols ─────────────────────────────────────────────────── */}
        <div className="col-span-3 space-y-5">

          {/* Forms to review */}
          {relevantForms.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-text-primary">
                  Forms to Review
                </h2>
                <span className="text-xs text-text-muted">
                  {relevantForms.filter(f => f.status === 'pending_review').length} pending ·{' '}
                  {relevantForms.filter(f => f.status !== 'pending_review').length} completed
                </span>
              </div>

              {/* Pending forms first — open by default */}
              {relevantForms
                .filter(f => f.status === 'pending_review')
                .map(form => (
                  <FormCard key={form.id} form={form} defaultOpen />
                ))}

              {/* Completed forms — collapsed by default */}
              {relevantForms.filter(f => f.status !== 'pending_review').length > 0 && (
                <>
                  <p className="text-xs text-text-muted pt-1">Completed (read-only)</p>
                  {relevantForms
                    .filter(f => f.status !== 'pending_review')
                    .map(form => (
                      <FormCard key={form.id} form={form} defaultOpen={false} />
                    ))}
                </>
              )}
            </div>
          )}

          {/* Task Details */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-4">
            <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3">
              Task Details
            </h2>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <div>
                <dt className="text-xs text-text-muted mb-0.5">Task ID</dt>
                <dd className="font-mono text-xs text-text-secondary">{task.id}</dd>
              </div>
              <div>
                <dt className="text-xs text-text-muted mb-0.5">Type</dt>
                <dd className="text-text-primary font-medium">{TASK_TYPE_LABELS[task.type]}</dd>
              </div>
              <div>
                <dt className="text-xs text-text-muted mb-0.5">Stage</dt>
                <dd><StatusBadge status={task.stage} /></dd>
              </div>
              <div>
                <dt className="text-xs text-text-muted mb-0.5">Assigned To</dt>
                <dd className="text-text-secondary">{task.assignedToName}</dd>
              </div>
              <div>
                <dt className="text-xs text-text-muted mb-0.5">Created</dt>
                <dd className="text-text-secondary">{formatDate(task.createdAt)}</dd>
              </div>
              {task.resolvedAt && (
                <div>
                  <dt className="text-xs text-text-muted mb-0.5">Resolved</dt>
                  <dd className="text-text-secondary">{formatDateTime(task.resolvedAt)}</dd>
                </div>
              )}
            </dl>

            {task.notes && (
              <div className="mt-4 border-l-4 border-warning bg-warning-subtle p-3 rounded-r-lg">
                <p className="text-xs text-text-muted font-semibold uppercase tracking-wider mb-1">Notes</p>
                <p className="text-sm text-text-primary leading-relaxed">{task.notes}</p>
              </div>
            )}
          </div>
        </div>

        {/* ── Right: 2 cols ────────────────────────────────────────────────── */}
        <div className="col-span-2 space-y-4">

          {/* Task Status card */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-4 flex flex-col items-center justify-center gap-2 py-6">
            <p className="text-xs text-text-muted uppercase tracking-wider font-semibold">Task Status</p>
            <StatusBadge status={task.status} className="text-sm px-3 py-1" />
            <p className="text-xs text-text-muted mt-1">Created {formatDate(task.createdAt)}</p>
          </div>

          {/* Action Panel */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-4">
            <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-4">
              Actions
            </h2>

            {/* Success banner */}
            {successAction && (
              <div className={[
                'mb-4 flex items-start gap-2 px-3 py-3 rounded-lg border text-sm',
                successAction === 'approved'     ? 'bg-success-subtle border-success/30 text-success'
                : successAction === 'rejected'   ? 'bg-danger-subtle border-danger/30 text-danger'
                :                                  'bg-warning-subtle border-warning/30 text-warning',
              ].join(' ')}>
                <IconCheck size={16} className="flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">
                    {successAction === 'approved' ? 'Task Approved'
                    : successAction === 'rejected' ? 'Task Rejected'
                    : 'Information Requested'}
                  </p>
                  <p className="text-xs opacity-80 mt-0.5">
                    Resolved at {formatDateTime(new Date().toISOString())}
                  </p>
                </div>
              </div>
            )}

            {isResolved && !successAction ? (
              <div className={[
                'flex items-start gap-2 px-3 py-3 rounded-lg border text-sm',
                task.status === 'approved'     ? 'bg-success-subtle border-success/30 text-success'
                : task.status === 'rejected'   ? 'bg-danger-subtle border-danger/30 text-danger'
                :                               'bg-warning-subtle border-warning/30 text-warning',
              ].join(' ')}>
                <div>
                  <p className="font-semibold">
                    {task.status === 'approved' ? 'Task Approved'
                    : task.status === 'rejected' ? 'Task Rejected'
                    : 'Information Requested'}
                  </p>
                  {task.resolvedAt && (
                    <p className="text-xs opacity-80 mt-0.5">Resolved at {formatDateTime(task.resolvedAt)}</p>
                  )}
                  {task.notes && (
                    <p className="text-xs mt-1.5 opacity-90 leading-relaxed">{task.notes}</p>
                  )}
                </div>
              </div>
            ) : !successAction ? (
              <div className="space-y-2">

                {/* Approve */}
                <div>
                  <button
                    onClick={() => togglePanel('approve')}
                    disabled={isPending}
                    className={[
                      'w-full flex items-center justify-center gap-2 h-10 rounded-lg text-sm font-semibold border transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
                      activePanel === 'approve'
                        ? 'bg-success text-white border-success'
                        : 'bg-success-subtle text-success border-success/30 hover:bg-success hover:text-white',
                    ].join(' ')}
                  >
                    <IconCheck size={16} />
                    Approve
                  </button>
                  {activePanel === 'approve' && (
                    <div className="mt-2 p-3 bg-bg-elevated border border-success/20 rounded-lg space-y-2">
                      <textarea
                        rows={2}
                        placeholder="Optional approval notes…"
                        value={notes}
                        onChange={e => setNotes(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-bg-surface border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-success focus:ring-1 focus:ring-success/30 resize-none transition-colors"
                      />
                      <button
                        onClick={() => approveMutation.mutate()}
                        disabled={approveMutation.isPending}
                        className="w-full h-9 rounded-lg bg-success hover:bg-success/90 text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {approveMutation.isPending ? 'Approving…' : 'Confirm Approve'}
                      </button>
                    </div>
                  )}
                </div>

                {/* Reject */}
                <div>
                  <button
                    onClick={() => togglePanel('reject')}
                    disabled={isPending}
                    className={[
                      'w-full flex items-center justify-center gap-2 h-10 rounded-lg text-sm font-semibold border transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
                      activePanel === 'reject'
                        ? 'bg-danger text-white border-danger'
                        : 'bg-danger-subtle text-danger border-danger/30 hover:bg-danger hover:text-white',
                    ].join(' ')}
                  >
                    <IconX size={16} />
                    Reject
                  </button>
                  {activePanel === 'reject' && (
                    <div className="mt-2 p-3 bg-bg-elevated border border-danger/20 rounded-lg space-y-2">
                      <textarea
                        rows={2}
                        placeholder="Reason for rejection…"
                        value={notes}
                        onChange={e => setNotes(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-bg-surface border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-danger focus:ring-1 focus:ring-danger/30 resize-none transition-colors"
                      />
                      <button
                        onClick={() => rejectMutation.mutate()}
                        disabled={rejectMutation.isPending}
                        className="w-full h-9 rounded-lg bg-danger hover:bg-danger/90 text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {rejectMutation.isPending ? 'Rejecting…' : 'Confirm Reject'}
                      </button>
                    </div>
                  )}
                </div>

                {/* Request Information */}
                <div>
                  <button
                    onClick={() => togglePanel('request_info')}
                    disabled={isPending}
                    className={[
                      'w-full flex items-center justify-center gap-2 h-10 rounded-lg text-sm font-semibold border transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
                      activePanel === 'request_info'
                        ? 'bg-warning text-white border-warning'
                        : 'bg-warning-subtle text-warning border-warning/30 hover:bg-warning hover:text-white',
                    ].join(' ')}
                  >
                    <IconMessageQuestion size={16} />
                    Request Information
                  </button>
                  {activePanel === 'request_info' && (
                    <div className="mt-2 p-3 bg-bg-elevated border border-warning/20 rounded-lg space-y-2">
                      <textarea
                        rows={3}
                        placeholder="Describe what information is needed from the client…"
                        value={message}
                        onChange={e => setMessage(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-bg-surface border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-warning focus:ring-1 focus:ring-warning/30 resize-none transition-colors"
                      />
                      <button
                        onClick={() => { if (message.trim()) requestInfoMutation.mutate(); }}
                        disabled={!message.trim() || requestInfoMutation.isPending}
                        className="w-full h-9 rounded-lg bg-warning hover:bg-warning/90 text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {requestInfoMutation.isPending ? 'Sending…' : 'Send Request'}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
