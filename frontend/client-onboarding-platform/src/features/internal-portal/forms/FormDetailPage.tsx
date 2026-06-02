import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  IconArrowLeft,
  IconAlertCircle,
  IconLoader2,
  IconClipboardText,
  IconUser,
  IconBuildingCommunity,
  IconCalendar,
} from '@tabler/icons-react';
import { formsService } from '../../../mocks/services/cases.service';
import { StatusBadge } from '../../../components/common/StatusBadge';
import {
  EnrollmentFormViewer,
  CDDFormViewer,
  ControlPersonFormViewer,
} from '../../../components/common/FormViewers';
import type {
  EnrollmentFormData,
  CDDFormData,
  ControlPersonFormData,
} from '../../../types';
import { formatDateTime } from '../../../utils/formatters';

// ─── Form type meta ───────────────────────────────────────────────────────────

const FORM_META: Record<string, { label: string; icon: React.ReactNode; description: string }> = {
  ENROLLMENT: {
    label: 'Enrollment Form',
    icon: <IconBuildingCommunity size={18} />,
    description: 'Entity registration details, registered address, and primary contact information.',
  },
  CDD: {
    label: 'Customer Due Diligence (CDD)',
    icon: <IconClipboardText size={18} />,
    description: 'Business nature, source of funds, trading volume, and compliance declarations.',
  },
  CONTROL_PERSON: {
    label: 'Control Persons',
    icon: <IconUser size={18} />,
    description: 'Details of individuals with significant control or ownership of the entity.',
  },
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function FormDetailPage({
  caseId: caseIdProp,
  formId: formIdProp,
  embedded = false,
}: {
  caseId?: string;
  formId?: string;
  embedded?: boolean;
} = {}) {
  const { caseId: routeCaseId, formId: routeFormId } = useParams<{ caseId: string; formId: string }>();
  const caseId = caseIdProp ?? routeCaseId;
  const formId = formIdProp ?? routeFormId;

  const { data: forms = [], isLoading } = useQuery({
    queryKey: ['forms', 'case', caseId],
    queryFn: () => formsService.getFormsByCase(caseId!),
    enabled: !!caseId,
  });

  const form = forms.find(f => f.id === formId);
  const meta = form ? FORM_META[form.type] : undefined;

  // ── Loading ────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <IconLoader2 size={28} className="animate-spin text-text-muted" />
      </div>
    );
  }

  if (!form || !meta) {
    return (
      <div className={`${embedded ? 'p-6' : 'p-8'} flex flex-col items-center justify-center py-24 gap-3`}>
        <IconAlertCircle size={36} className="text-danger" />
        <p className="text-text-secondary">Form not found.</p>
        {!embedded && (
          <Link
            to={`/internal/cases/${caseId}`}
            className="text-sm text-primary hover:underline flex items-center gap-1"
          >
            <IconArrowLeft size={14} />
            Back to Case
          </Link>
        )}
      </div>
    );
  }

  return (
    <div className={embedded ? 'p-5' : 'p-8 max-w-3xl'}>

      {/* Header card */}
      <div className={`bg-bg-elevated border border-border-default rounded-xl p-5 ${embedded ? 'mb-4' : 'mb-6'}`}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary-subtle flex items-center justify-center text-primary flex-shrink-0 mt-0.5">
              {meta.icon}
            </div>
            <div>
              <h1 className="text-base font-bold text-text-primary mb-0.5">{meta.label}</h1>
              <p className="text-sm text-text-secondary">{meta.description}</p>
            </div>
          </div>
          <StatusBadge status={form.status} />
        </div>

        {/* Metadata row */}
        <div className="flex items-center gap-5 mt-4 pt-4 border-t border-border-subtle text-xs text-text-muted">
          <span className="flex items-center gap-1.5">
            <IconCalendar size={12} />
            Submitted {formatDateTime(form.submittedAt)}
          </span>
          <span className="font-mono bg-bg-elevated px-2 py-0.5 rounded border border-border-subtle">
            {form.id}
          </span>
        </div>
      </div>

      {/* Form data card */}
      <div className="bg-bg-elevated border border-border-default rounded-xl p-6">
        <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-5">
          Form Data
          <span className="ml-2 font-normal normal-case text-text-muted">(read-only)</span>
        </p>

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

    </div>
  );
}
