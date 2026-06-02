import { useState } from 'react';
import { Tabs } from '@mantine/core';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  IconArrowLeft,
  IconChevronRight,
  IconChevronDown,
  IconChevronUp,
  IconCheck,
  IconLock,
  IconEdit,
  IconMail,
  IconPhone,
  IconMessageCircle,
  IconSend,
  IconLoader2,
  IconAlertCircle,
  IconClipboardCheck,
  IconFileText,
  IconFiles,
  IconShieldCheck,
  IconFile,
  IconClipboardText,
  IconUser,
  IconReceipt2,
  IconArrowsTransferDown,
  IconUpload,
  IconDownload,
  IconCreditCard,
  IconMapPin,
  IconUserCheck,
} from '@tabler/icons-react';
import {
  casesService,
  documentsService,
  formsService,
  messagesService,
} from '../../../mocks/services/cases.service';
import { FileUploadZone } from '../../../components/common/FileUploadZone';
import { useAuth } from '../../../store/AuthContext';
import { StatusBadge } from '../../../components/common/StatusBadge';
import {
  PRODUCT_LABELS,
  WORKFLOW_STAGES,
} from '../../../types';
import type { FormSubmission, Document as CaseDocument, EnrollmentFormData } from '../../../types';
import { formatDate, initials } from '../../../utils/formatters';
import { MOCK_SALES_CONTACT } from '../../../mocks/data/users.mock';

// ─── Mock per-case product metadata ──────────────────────────────────────────

interface ProductMeta {
  tradingType: string;
  optionsTrading: string;
  salesOwner: string;
  opportunityId: string;
  authorizedUsers: { name: string; type: string }[];
}

const CASE_PRODUCT_META: Record<string, ProductMeta> = {
  'case-001': {
    tradingType: 'Prime Brokerage', optionsTrading: 'Yes', salesOwner: 'Marcus Chen',
    opportunityId: '007Pc000009PBrkGH',
    authorizedUsers: [{ name: 'Jordan Lee', type: 'Account Holder' }, { name: 'Sarah Kim', type: 'Authorized Trader' }],
  },
  'case-002': {
    tradingType: 'Margin', optionsTrading: 'No', salesOwner: 'Marcus Chen',
    opportunityId: '007Pc000009FCMrXY',
    authorizedUsers: [{ name: 'Sophia Reeves', type: 'General Partner' }],
  },
  'case-003': {
    tradingType: 'Cash', optionsTrading: 'No', salesOwner: 'Marcus Chen',
    opportunityId: '007Pc000009IBcZZ',
    authorizedUsers: [{ name: 'Jordan Lee', type: 'Account Holder' }],
  },
  'case-004': {
    tradingType: 'Retail', optionsTrading: 'Yes', salesOwner: 'Marcus Chen',
    opportunityId: '007Pc000009RETaBC',
    authorizedUsers: [{ name: 'Sophia Reeves', type: 'General Partner' }, { name: 'Alex Morgan', type: 'Advisor' }],
  },
};

// Total required items — matches REQUIRED_FORMS and REQUIRED_DOCS in this file
const TOTAL_FORMS_REQUIRED = 5; // ENROLLMENT + CDD + CONTROL_PERSON + TAX + SSI
const TOTAL_DOCS_REQUIRED  = 7; // mirrors REQUIRED_DOCS list

// ─── Progress computation ─────────────────────────────────────────────────────
// Pending-review/uploaded items (pre-filled via reuse) score 50%; approved score 100%.

function computeProgress(forms: FormSubmission[], docs: CaseDocument[], stageIndex: number): number {
  const stageProgress = (stageIndex / (WORKFLOW_STAGES.length - 1)) * 40;

  const approvedForms = forms.filter(f => f.status === 'approved').length;
  const pendingForms  = forms.filter(f => f.status === 'pending_review').length;
  const formProgress  = ((approvedForms + pendingForms * 0.5) / TOTAL_FORMS_REQUIRED) * 30;

  const approvedDocs = docs.filter(d => d.status === 'approved').length;
  const uploadedDocs = docs.filter(d => d.status !== 'rejected').length;
  const docProgress  = ((approvedDocs + (uploadedDocs - approvedDocs) * 0.5) / TOTAL_DOCS_REQUIRED) * 30;

  return Math.min(100, Math.round(stageProgress + formProgress + docProgress));
}

// ─── Form routes ─────────────────────────────────────────────────────────────

// Maps form type → dedicated route
const FORM_ROUTE: Record<string, (caseId: string) => string> = {
  ENROLLMENT:     caseId => `/client/enrollment/${caseId}`,
  CDD:            caseId => `/client/forms/${caseId}/cdd`,
  CONTROL_PERSON: caseId => `/client/forms/${caseId}/controller-person`,
  TAX:            caseId => `/client/forms/${caseId}/tax`,
  SSI:            caseId => `/client/forms/${caseId}/ssi`,
};

// ─── Required forms list (shown in the Forms collapsible — Enrollment is separate) ─

interface FormRequirement {
  type: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  required: boolean;
}

const REQUIRED_FORMS: FormRequirement[] = [
  {
    type: 'CDD',
    label: 'Customer Due Diligence (CDD)',
    description: 'Business activities, source of funds, and risk profile',
    icon: <IconClipboardText size={15} />,
    required: true,
  },
  {
    type: 'CONTROL_PERSON',
    label: 'Controller Person Form',
    description: 'Individuals with 25%+ ownership or significant control',
    icon: <IconUser size={15} />,
    required: true,
  },
  {
    type: 'TAX',
    label: 'Tax Form (W-9 / W-8BEN-E)',
    description: 'Tax classification, FATCA status, and withholding rate',
    icon: <IconReceipt2 size={15} />,
    required: true,
  },
  {
    type: 'SSI',
    label: 'Standard Settlement Instructions (SSI)',
    description: 'Beneficiary bank account details for settlement',
    icon: <IconArrowsTransferDown size={15} />,
    required: true,
  },
];

// ─── Required document list ───────────────────────────────────────────────────

interface DocRequirement {
  type: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  required: boolean;
}

const REQUIRED_DOCS: DocRequirement[] = [
  {
    type: 'PASSPORT',
    label: 'Passport / Government-issued ID',
    description: 'Valid passport or government-issued photo ID for each authorized signatory',
    icon: <IconCreditCard size={15} />,
    required: true,
  },
  {
    type: 'NATIONAL_ID',
    label: 'National ID / Driver\'s License',
    description: 'National identity card or driver\'s license as supplementary identification',
    icon: <IconCreditCard size={15} />,
    required: false,
  },
  {
    type: 'ARTICLES_OF_INCORPORATION',
    label: 'Articles of Incorporation',
    description: 'Certificate of incorporation, formation, or equivalent entity registration document',
    icon: <IconFileText size={15} />,
    required: true,
  },
  {
    type: 'PROOF_OF_ADDRESS',
    label: 'Proof of Address',
    description: 'Utility bill or bank statement dated within the last 3 months',
    icon: <IconMapPin size={15} />,
    required: true,
  },
  {
    type: 'TAX_FORM',
    label: 'Tax Form (W-9 / W-8BEN-E)',
    description: 'Completed and signed tax certification form appropriate for entity type',
    icon: <IconReceipt2 size={15} />,
    required: true,
  },
  {
    type: 'CDD_FORM',
    label: 'CDD Supporting Document',
    description: 'Additional documentation supporting Customer Due Diligence requirements',
    icon: <IconClipboardText size={15} />,
    required: false,
  },
  {
    type: 'CONTROL_PERSON_FORM',
    label: 'Control Person Identity Documents',
    description: 'Government-issued ID for all individuals with 25%+ ownership or significant control',
    icon: <IconUserCheck size={15} />,
    required: false,
  },
];

// ─── Collapsible checklist section ───────────────────────────────────────────

function CollapsibleSection({
  icon, title, subtitle, badge, expanded, onToggle, children,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  badge: React.ReactNode;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-bg-surface border border-border-default rounded-xl overflow-hidden">
      {/* Header row — always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-4 px-5 py-4 hover:bg-bg-hover transition-colors text-left"
      >
        <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-bg-elevated flex items-center justify-center text-text-muted">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-semibold text-text-primary">{title}</span>
            {badge}
          </div>
          <p className="text-xs text-text-muted">{subtitle}</p>
        </div>
        <span className="flex-shrink-0 text-text-muted">
          {expanded ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
        </span>
      </button>

      {/* Expandable list */}
      {expanded && (
        <div className="border-t border-border-subtle divide-y divide-border-subtle">
          {children}
        </div>
      )}
    </div>
  );
}

// ─── Enrollment checklist item (non-collapsible) ──────────────────────────────

function ChecklistItem({ icon, title, subtitle, badge, action }: {
  icon: React.ReactNode; title: string; subtitle: string;
  badge: React.ReactNode; action?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-4 px-5 py-4 bg-bg-surface border border-border-default rounded-xl">
      <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-bg-elevated flex items-center justify-center text-text-muted">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-semibold text-text-primary">{title}</span>
          {badge}
        </div>
        <p className="text-xs text-text-muted">{subtitle}</p>
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  );
}

// ─── Post-review task card ────────────────────────────────────────────────────

function PostReviewTask({ title, subtitle, status, action }: {
  title: string; subtitle: string;
  status: 'pending' | 'done' | 'locked'; action: React.ReactNode;
}) {
  return (
    <div className={`flex items-center gap-4 px-5 py-4 rounded-xl border ${
      status === 'locked' ? 'bg-bg-surface border-border-subtle opacity-60' : 'bg-bg-surface border-border-default'
    }`}>
      <div className={`flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center ${
        status === 'done'   ? 'bg-success-subtle text-success'
        : status === 'locked' ? 'bg-bg-elevated text-text-muted'
        : 'bg-warning-subtle text-warning'
      }`}>
        {status === 'locked' ? <IconLock size={16} />
          : status === 'done'  ? <IconCheck size={16} />
          : <IconClipboardCheck size={16} />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-sm font-semibold text-text-primary">{title}</span>
          {status === 'locked' && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-bg-elevated border border-border-default text-xs text-text-muted">
              <IconLock size={10} /> Locked — Complete previous steps
            </span>
          )}
          {status === 'pending' && <StatusBadge status="pending_info" />}
          {status === 'done'    && <StatusBadge status="approved" />}
        </div>
        <p className="text-xs text-text-muted">{subtitle}</p>
      </div>
      <div className="flex-shrink-0">{action}</div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function ApplicationTrackingPage() {
  const { caseId }      = useParams<{ caseId: string }>();
  const { user }        = useAuth();
  const navigate        = useNavigate();
  const [searchParams]  = useSearchParams();
  const isOnboarding    = searchParams.get('onboarding') === '1';

  const [agreementAcknowledged, setAgreementAcknowledged] = useState(false);
  const [showMessageBox, setShowMessageBox] = useState(false);
  const [messageText, setMessageText]       = useState('');
  const [messageSent, setMessageSent]       = useState(false);

  // Collapse state — default open when arriving from onboarding flow
  const [formsExpanded, setFormsExpanded]           = useState(isOnboarding);
  const [docsExpanded,  setDocsExpanded]            = useState(isOnboarding);
  const [legalFormsExpanded, setLegalFormsExpanded] = useState(true);
  const [legalDocsExpanded,  setLegalDocsExpanded]  = useState(true);

  // Upload state — per document-type
  const [expandedDocType,    setExpandedDocType]    = useState<string | null>(null);
  const [pendingFilesByType, setPendingFilesByType] = useState<Record<string, File[]>>({});
  const [uploadingType,      setUploadingType]      = useState<string | null>(null);
  const [localDocs,          setLocalDocs]          = useState<CaseDocument[]>([]);

  // ── Queries ──────────────────────────────────────────────────────────────────

  const { data: caseData, isLoading, isError } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => casesService.getCaseById(caseId!),
    enabled: !!caseId,
  });

  const { data: forms = [] } = useQuery({
    queryKey: ['forms', 'case', caseId],
    queryFn: () => formsService.getFormsByCase(caseId!),
    enabled: !!caseId,
  });

  const { data: documents = [] } = useQuery({
    queryKey: ['documents', caseId],
    queryFn: () => documentsService.getDocumentsByCase(caseId!),
    enabled: !!caseId,
  });

  // ── Live-account queries (for "copied from" provenance) ────────────────────

  const { data: allClientCases = [] } = useQuery({
    queryKey: ['cases', 'client', user?.id],
    queryFn:  () => casesService.getCasesByClientId(user!.id),
    enabled:  !!user?.id,
  });

  const liveCase = allClientCases.find(c => c.status === 'completed' && c.id !== caseId);

  const { data: liveCaseForms = [] } = useQuery({
    queryKey: ['forms', 'case', liveCase?.id],
    queryFn:  () => formsService.getFormsByCase(liveCase!.id),
    enabled:  !!liveCase?.id,
  });

  const { data: liveCaseDocs = [] } = useQuery({
    queryKey: ['documents', liveCase?.id],
    queryFn:  () => documentsService.getDocumentsByCase(liveCase!.id),
    enabled:  !!liveCase?.id,
  });

  const uploadMutation = useMutation({
    mutationFn: ({ file, type }: { file: File; type: string }) =>
      documentsService.uploadDocument(caseId!, file, type),
  });

  const handleUploadForType = async (docType: string) => {
    const files = pendingFilesByType[docType] ?? [];
    if (!files.length) return;
    setUploadingType(docType);
    for (const file of files) {
      const doc = await uploadMutation.mutateAsync({ file, type: docType });
      setLocalDocs(prev => [doc, ...prev]);
    }
    setPendingFilesByType(prev => ({ ...prev, [docType]: [] }));
    setUploadingType(null);
    setExpandedDocType(null);
  };

  const allDocuments = [...localDocs, ...documents];

  // ── Loading / error ───────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <IconLoader2 size={32} className="animate-spin text-text-muted" />
      </div>
    );
  }

  if (isError || !caseData) {
    return (
      <div className="p-8 flex flex-col items-center justify-center py-20 gap-3">
        <IconAlertCircle size={36} className="text-danger" />
        <p className="text-text-secondary">Case not found.</p>
        <Link to="/client/dashboard" className="text-sm text-primary hover:underline">← Back to Dashboard</Link>
      </div>
    );
  }

  // ── Derived state ─────────────────────────────────────────────────────────

  const isLive         = caseData.status === 'completed';
  const stageIndex     = WORKFLOW_STAGES.indexOf(caseData.currentStage);
  const progress       = isLive ? 100 : computeProgress(forms, documents, stageIndex);
  const productMeta    = CASE_PRODUCT_META[caseData.id] ?? CASE_PRODUCT_META['case-001'];
  const primaryProduct = caseData.products[0];

  const enrollmentForm = forms.find(f => f.type === 'ENROLLMENT');
  const enrollmentDone = enrollmentForm?.status === 'approved';
  const approvedForms  = forms.filter(f => f.status === 'approved').length;
  const approvedDocs   = documents.filter(d => d.status === 'approved').length;

  const reviewPassed   = stageIndex >= WORKFLOW_STAGES.indexOf('KYC');
  const showPostReview = stageIndex >= WORKFLOW_STAGES.indexOf('SALES_MANAGER_REVIEW');

  const productProgress = Math.min(100, Math.round(
    (approvedForms  / Math.max(forms.length,     1)) * 50 +
    (approvedDocs   / Math.max(documents.length, 1)) * 30 +
    (stageIndex     / (WORKFLOW_STAGES.length - 1)) * 20
  ));

  // ── Reuse provenance ─────────────────────────────────────────────────────────

  const sourceAccountName = liveCase
    ? `${PRODUCT_LABELS[liveCase.products[0]]} (${liveCase.id})`
    : null;

  const liveFormTypes = new Set(liveCaseForms.map(f => f.type as string));
  const liveDocTypes  = new Set(liveCaseDocs.map(d => d.type as string));

  const copiedForms = forms.filter(f => liveFormTypes.has(f.type));
  const copiedDocs  = allDocuments.filter(d => liveDocTypes.has(d.type as string));

  const enrollmentData = enrollmentForm?.data as EnrollmentFormData | undefined;

  const totalCopied = copiedForms.length + copiedDocs.length;
  const totalItems  = TOTAL_FORMS_REQUIRED + TOTAL_DOCS_REQUIRED;

  const handleSendMessage = async () => {
    if (!messageText.trim()) return;
    await messagesService.sendMessage(caseData.id, user!.id, user!.fullName, messageText.trim());
    setMessageSent(true);
    setMessageText('');
    setTimeout(() => setMessageSent(false), 3000);
  };

  return (
    <div className="p-8">

      {/* Page title */}

      {/* ── Onboarding action banner ── */}
      {isOnboarding && !enrollmentDone && (
        <div className="mb-5 flex items-start gap-4 px-5 py-4 rounded-xl bg-primary-subtle border border-primary/25">
          <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-primary/15 flex items-center justify-center mt-0.5">
            <IconClipboardCheck size={17} className="text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-text-primary mb-0.5">
              Complete your {primaryProduct ? PRODUCT_LABELS[primaryProduct] : 'new product'} onboarding
            </p>
            <p className="text-xs text-text-secondary leading-relaxed">
              Your existing entity information has been carried over. Please complete the Enrollment
              form below, fill out any required forms, and upload the supporting documents to submit
              your application for review.
            </p>
          </div>
          <button
            onClick={() => navigate(`/client/enrollment/${caseData.id}`)}
            className="flex-shrink-0 flex items-center gap-1.5 px-4 h-8 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold transition-colors"
          >
            <IconEdit size={12} /> Start Enrollment
          </button>
        </div>
      )}

      {/* ── Mantine Tabs ── */}
      <Tabs
        defaultValue={`product-${caseData.products[0]}`}
        classNames={{
          list: 'flex gap-0 border-b border-border-default',
          tab: 'px-5 py-3 text-sm font-semibold border-b-2 -mb-px border-transparent text-text-muted hover:text-text-secondary transition-colors data-[active]:border-primary data-[active]:text-text-primary',
          panel: 'pt-6',
        }}
      >
        <Tabs.List>
          <Tabs.Tab value="legal-entity">Legal Entity Details</Tabs.Tab>
          {caseData.products.map(p => (
            <Tabs.Tab key={p} value={`product-${p}`}>{PRODUCT_LABELS[p]}</Tabs.Tab>
          ))}
        </Tabs.List>

        {/* ══ Tab 1: Legal Entity Details ═══════════════════════════════════════ */}
        <Tabs.Panel value="legal-entity">
          <div className="grid grid-cols-3 gap-6">

            {/* Left: col-span-2 */}
            <div className="col-span-2 space-y-3">

              {/* Enrollment Application */}
              <div className={isOnboarding && !enrollmentDone ? 'ring-2 ring-primary/40 rounded-xl' : ''}>
                <ChecklistItem
                  icon={<IconFileText size={17} />}
                  title="Enrollment Application"
                  subtitle={
                    isOnboarding && !enrollmentDone
                      ? 'Action required — complete your enrollment form to proceed'
                      : 'Fill out your profile information'
                  }
                  badge={
                    enrollmentDone ? <StatusBadge status="approved" />
                    : enrollmentForm ? <StatusBadge status="pending_info" />
                    : <StatusBadge status="active" />
                  }
                  action={
                    <button
                      onClick={() => navigate(`/client/enrollment/${caseData.id}`)}
                      className={`text-xs font-semibold flex items-center gap-1 transition-colors ${
                        isOnboarding && !enrollmentDone
                          ? 'px-3 h-7 rounded-lg bg-primary hover:bg-primary-hover text-white'
                          : 'text-primary hover:text-primary-hover'
                      }`}
                    >
                      <IconEdit size={13} />
                      {isOnboarding && !enrollmentDone ? 'Complete Now' : 'Edit'}
                    </button>
                  }
                />
              </div>

              {/* Forms — same structure as Product tab */}
              {(() => {
                const submittedCount = REQUIRED_FORMS.filter(f => forms.some(s => s.type === f.type)).length;
                const allApproved = REQUIRED_FORMS.every(f => forms.some(s => s.type === f.type && s.status === 'approved'));
                return (
                  <CollapsibleSection
                    icon={<IconClipboardCheck size={17} />}
                    title={`Forms (${submittedCount}/${REQUIRED_FORMS.length})`}
                    subtitle="Fill out required form details"
                    badge={allApproved ? <StatusBadge status="approved" /> : <StatusBadge status="active" />}
                    expanded={legalFormsExpanded}
                    onToggle={() => setLegalFormsExpanded(v => !v)}
                  >
                    {REQUIRED_FORMS.map(formMeta => {
                      const submission = forms.find(f => f.type === formMeta.type);
                      const href = FORM_ROUTE[formMeta.type](caseData.id);
                      const hasSubmission = !!submission;
                      const actionLabel = !hasSubmission ? 'Fill In' : submission.status === 'rejected' ? 'Resubmit' : submission.status === 'approved' ? 'View' : 'Edit';
                      return isLive ? (
                        <div key={formMeta.type} className="w-full flex items-center gap-4 px-5 py-3.5">
                          <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-success/10 text-success">{formMeta.icon}</div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <p className="text-sm font-medium text-text-primary">{formMeta.label}</p>
                              {liveFormTypes.has(formMeta.type) && <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-success/10 text-success border border-success/20 flex-shrink-0"><IconCheck size={9} strokeWidth={3} />Copied</span>}
                            </div>
                            <p className="text-xs text-text-muted">{submission ? `Submitted ${formatDate(submission.submittedAt)}` : formMeta.description}</p>
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0"><StatusBadge status="approved" /><span className="flex items-center gap-1 text-xs text-text-muted"><IconLock size={11} /> Locked</span></div>
                        </div>
                      ) : (
                        <button key={formMeta.type} onClick={() => navigate(href)} className="w-full flex items-center gap-4 px-5 py-3.5 text-left transition-colors group hover:bg-bg-hover cursor-pointer">
                          <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${hasSubmission ? 'bg-primary-subtle text-primary' : 'bg-bg-elevated text-text-muted'}`}>{formMeta.icon}</div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <p className={`text-sm font-medium ${hasSubmission ? 'text-text-primary' : 'text-text-secondary'}`}>{formMeta.label}</p>
                              {liveFormTypes.has(formMeta.type) ? <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-success/10 text-success border border-success/20 flex-shrink-0"><IconCheck size={9} strokeWidth={3} />Copied</span> : <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-warning/10 text-warning border border-warning/20 flex-shrink-0">New</span>}
                            </div>
                            <p className="text-xs text-text-muted">{submission ? `Submitted ${formatDate(submission.submittedAt)}` : formMeta.description}</p>
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            {submission ? <StatusBadge status={submission.status} /> : <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-warning/10 text-warning border border-warning/25">Not Started</span>}
                            <span className="text-xs font-semibold text-primary group-hover:text-primary-hover transition-colors flex items-center gap-0.5">{actionLabel}<IconChevronRight size={12} /></span>
                          </div>
                        </button>
                      );
                    })}
                  </CollapsibleSection>
                );
              })()}

              {/* Documents — same structure as Product tab */}
              {(() => {
                const uploadedCount = REQUIRED_DOCS.filter(d => allDocuments.some(u => u.type === d.type)).length;
                const approvedCount = REQUIRED_DOCS.filter(d => allDocuments.some(u => u.type === d.type && u.status === 'approved')).length;
                const allRequiredUploaded = approvedCount === REQUIRED_DOCS.filter(d => d.required).length && REQUIRED_DOCS.filter(d => d.required).length > 0;
                return (
                  <CollapsibleSection
                    icon={<IconFiles size={17} />}
                    title={`Documents (${uploadedCount}/${REQUIRED_DOCS.length})`}
                    subtitle="Upload required supporting documents"
                    badge={allRequiredUploaded ? <StatusBadge status="approved" /> : <StatusBadge status="active" />}
                    expanded={legalDocsExpanded}
                    onToggle={() => setLegalDocsExpanded(v => !v)}
                  >
                    {REQUIRED_DOCS.map(docMeta => {
                      const uploaded = allDocuments.filter(d => d.type === docMeta.type).sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime())[0];
                      const isExpanded = expandedDocType === docMeta.type;
                      const isUploading = uploadingType === docMeta.type;
                      const pendingFiles = pendingFilesByType[docMeta.type] ?? [];
                      const btnLabel = uploaded && uploaded.status !== 'rejected' ? 'Re-upload' : 'Upload';
                      return (
                        <div key={docMeta.type} className="divide-y divide-border-subtle">
                          <div className="flex items-start gap-4 px-5 py-4 hover:bg-bg-hover transition-colors">
                            <div className={`flex-shrink-0 mt-0.5 w-8 h-8 rounded-lg flex items-center justify-center ${isLive ? 'bg-success/10 text-success' : uploaded ? 'bg-primary-subtle text-primary' : 'bg-bg-elevated text-text-muted'}`}>{docMeta.icon}</div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-0.5">
                                <p className="text-sm font-medium text-text-primary">{docMeta.label}</p>
                                {liveDocTypes.has(docMeta.type) ? <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-success/10 text-success border border-success/20 flex-shrink-0"><IconCheck size={9} strokeWidth={3} />Copied</span> : <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-warning/10 text-warning border border-warning/20 flex-shrink-0">New</span>}
                                {!docMeta.required && <span className="text-xs text-text-muted">(Optional)</span>}
                              </div>
                              <p className="text-xs text-text-muted leading-snug">{docMeta.description}</p>
                              {uploaded && <div className="flex items-center gap-2 mt-1.5"><IconFile size={11} className="text-text-muted flex-shrink-0" /><span className="text-xs text-text-secondary truncate">{uploaded.fileName}</span><span className="text-xs text-text-muted">{uploaded.fileSize}</span><span className="text-xs text-text-muted">·</span><span className="text-xs text-text-muted">{formatDate(uploaded.uploadedAt)}</span></div>}
                            </div>
                            <div className="flex-shrink-0 flex items-center gap-2 mt-0.5">
                              {isLive ? (
                                <><StatusBadge status="approved" /><span className="flex items-center gap-1 text-xs text-text-muted"><IconLock size={11} /> Locked</span>{uploaded && <button onClick={() => {}} className="flex items-center gap-1.5 px-3 h-7 rounded-lg border border-border-default text-xs text-text-secondary hover:text-primary hover:border-primary transition-colors"><IconDownload size={11} />Download</button>}</>
                              ) : (
                                <>{uploaded ? <StatusBadge status={uploaded.status} /> : <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${docMeta.required ? 'bg-warning/10 text-warning border-warning/25' : 'bg-bg-elevated text-text-muted border-border-default'}`}>{docMeta.required ? 'Required' : 'Optional'}</span>}<button onClick={() => setExpandedDocType(isExpanded ? null : docMeta.type)} className="flex items-center gap-1.5 px-3 h-7 rounded-lg border border-border-default text-xs text-text-secondary hover:text-primary hover:border-primary transition-colors"><IconUpload size={11} />{btnLabel}</button></>
                              )}
                            </div>
                          </div>
                          {!isLive && isExpanded && (
                            <div className="px-5 py-4 bg-bg-elevated border-t border-border-subtle">
                              <FileUploadZone label="Drag & drop or click to browse" description="PDF, JPG, PNG — max 10 MB per file" onFilesAccepted={files => setPendingFilesByType(prev => ({ ...prev, [docMeta.type]: files }))} />
                              <div className="mt-3 flex items-center justify-end gap-2">
                                <button type="button" onClick={() => { setExpandedDocType(null); setPendingFilesByType(prev => ({ ...prev, [docMeta.type]: [] })); }} className="px-3 h-8 rounded-lg border border-border-default text-xs text-text-secondary hover:text-text-primary transition-colors">Cancel</button>
                                <button type="button" onClick={() => handleUploadForType(docMeta.type)} disabled={!pendingFiles.length || isUploading} className="flex items-center gap-1.5 px-4 h-8 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold disabled:opacity-40 transition-colors">
                                  <IconUpload size={12} />
                                  {isUploading ? 'Uploading…' : pendingFiles.length ? `Upload ${pendingFiles.length} file${pendingFiles.length > 1 ? 's' : ''}` : 'Select a file'}
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </CollapsibleSection>
                );
              })()}

            </div>

            {/* Right: col-span-1 */}
            <div className="space-y-4">

              {/* Sales Contact */}
              <div className="bg-bg-surface border border-border-default rounded-xl p-4">
                <h3 className="text-sm font-semibold text-text-primary mb-3">Sales Contact</h3>
                <div className="flex items-start gap-3 mb-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary-subtle border border-primary/20 flex items-center justify-center text-primary text-sm font-bold">
                    {initials(MOCK_SALES_CONTACT.name)}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-text-primary">{MOCK_SALES_CONTACT.name}</p>
                    <p className="text-xs text-text-muted">{MOCK_SALES_CONTACT.title} · ClearStreet</p>
                    <div className="flex flex-col gap-0.5 mt-1.5">
                      <a href={`mailto:${MOCK_SALES_CONTACT.email}`} className="flex items-center gap-1 text-xs text-text-secondary hover:text-primary transition-colors">
                        <IconMail size={11} />{MOCK_SALES_CONTACT.email}
                      </a>
                      <span className="flex items-center gap-1 text-xs text-text-secondary">
                        <IconPhone size={11} />{MOCK_SALES_CONTACT.phone}
                      </span>
                    </div>
                  </div>
                </div>
                {showMessageBox ? (
                  <div className="space-y-2">
                    <textarea rows={3} value={messageText} onChange={e => setMessageText(e.target.value)} placeholder="Write your message…" className="w-full px-3 py-2 rounded-lg bg-bg-elevated border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 resize-none transition-colors" />
                    <div className="flex gap-2">
                      <button onClick={handleSendMessage} disabled={!messageText.trim()} className="flex-1 flex items-center justify-center gap-1.5 h-8 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold disabled:opacity-40 transition-colors">
                        <IconSend size={12} />{messageSent ? 'Sent!' : 'Send'}
                      </button>
                      <button onClick={() => { setShowMessageBox(false); setMessageText(''); }} className="px-3 h-8 rounded-lg border border-border-default text-xs text-text-secondary hover:text-text-primary transition-colors">Cancel</button>
                    </div>
                  </div>
                ) : (
                  <button onClick={() => setShowMessageBox(true)} className="w-full flex items-center justify-center gap-2 h-9 rounded-lg border border-border-default text-sm text-text-secondary hover:text-text-primary hover:border-primary hover:bg-primary-subtle transition-colors">
                    <IconMessageCircle size={14} />Send a message
                  </button>
                )}
              </div>
            </div>
          </div>
        </Tabs.Panel>

        {/* ══ Product Tabs (one per product in the case) ════════════════════════ */}
        {caseData.products.map(product => (
          <Tabs.Panel key={product} value={`product-${product}`}>
            <div className="grid grid-cols-3 gap-6">

              {/* Left: col-span-2 */}
              <div className="col-span-2 space-y-3">

                {/* Progress bar */}
                <div className="bg-bg-surface border border-border-default rounded-xl px-5 py-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-text-secondary">Application Progression Status:</span>
                    <span className="text-xs font-semibold text-success">{progress}% completed</span>
                  </div>
                  <div className="w-full h-2 bg-bg-elevated rounded-full overflow-hidden">
                    <div className="h-full bg-success rounded-full transition-all duration-700" style={{ width: `${progress}%` }} />
                  </div>
                </div>

                {/* Forms */}
                {(() => {
                  const submittedCount = REQUIRED_FORMS.filter(f => forms.some(s => s.type === f.type)).length;
                  const allApproved = REQUIRED_FORMS.every(f => forms.some(s => s.type === f.type && s.status === 'approved'));
                  return (
                    <CollapsibleSection
                      icon={<IconClipboardCheck size={17} />}
                      title={`Forms (${submittedCount}/${REQUIRED_FORMS.length})`}
                      subtitle="Fill out required form details"
                      badge={allApproved ? <StatusBadge status="approved" /> : <StatusBadge status="active" />}
                      expanded={formsExpanded}
                      onToggle={() => setFormsExpanded(v => !v)}
                    >
                      {REQUIRED_FORMS.map(formMeta => {
                        const submission = forms.find(f => f.type === formMeta.type);
                        const href = FORM_ROUTE[formMeta.type](caseData.id);
                        const hasSubmission = !!submission;
                        const actionLabel = !hasSubmission ? 'Fill In' : submission.status === 'rejected' ? 'Resubmit' : submission.status === 'approved' ? 'View' : 'Edit';
                        return isLive ? (
                          <div key={formMeta.type} className="w-full flex items-center gap-4 px-5 py-3.5">
                            <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-success/10 text-success">{formMeta.icon}</div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-0.5">
                                <p className="text-sm font-medium text-text-primary">{formMeta.label}</p>
                                {liveFormTypes.has(formMeta.type) && <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-success/10 text-success border border-success/20 flex-shrink-0"><IconCheck size={9} strokeWidth={3} />Copied</span>}
                              </div>
                              <p className="text-xs text-text-muted">{submission ? `Submitted ${formatDate(submission.submittedAt)}` : formMeta.description}</p>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0"><StatusBadge status="approved" /><span className="flex items-center gap-1 text-xs text-text-muted"><IconLock size={11} /> Locked</span></div>
                          </div>
                        ) : (
                          <button key={formMeta.type} onClick={() => navigate(href)} className="w-full flex items-center gap-4 px-5 py-3.5 text-left transition-colors group hover:bg-bg-hover cursor-pointer">
                            <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${hasSubmission ? 'bg-primary-subtle text-primary' : 'bg-bg-elevated text-text-muted'}`}>{formMeta.icon}</div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-0.5">
                                <p className={`text-sm font-medium ${hasSubmission ? 'text-text-primary' : 'text-text-secondary'}`}>{formMeta.label}</p>
                                {liveFormTypes.has(formMeta.type) ? <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-success/10 text-success border border-success/20 flex-shrink-0"><IconCheck size={9} strokeWidth={3} />Copied</span> : <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-warning/10 text-warning border border-warning/20 flex-shrink-0">New</span>}
                              </div>
                              <p className="text-xs text-text-muted">{submission ? `Submitted ${formatDate(submission.submittedAt)}` : formMeta.description}</p>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              {submission ? <StatusBadge status={submission.status} /> : <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-warning/10 text-warning border border-warning/25">Not Started</span>}
                              <span className="text-xs font-semibold text-primary group-hover:text-primary-hover transition-colors flex items-center gap-0.5">{actionLabel}<IconChevronRight size={12} /></span>
                            </div>
                          </button>
                        );
                      })}
                    </CollapsibleSection>
                  );
                })()}

                {/* Documents */}
                {(() => {
                  const uploadedCount = REQUIRED_DOCS.filter(d => allDocuments.some(u => u.type === d.type)).length;
                  const approvedCount = REQUIRED_DOCS.filter(d => allDocuments.some(u => u.type === d.type && u.status === 'approved')).length;
                  const allRequiredUploaded = approvedCount === REQUIRED_DOCS.filter(d => d.required).length && REQUIRED_DOCS.filter(d => d.required).length > 0;
                  return (
                    <CollapsibleSection
                      icon={<IconFiles size={17} />}
                      title={`Documents (${uploadedCount}/${REQUIRED_DOCS.length})`}
                      subtitle="Upload required supporting documents"
                      badge={allRequiredUploaded ? <StatusBadge status="approved" /> : <StatusBadge status="active" />}
                      expanded={docsExpanded}
                      onToggle={() => setDocsExpanded(v => !v)}
                    >
                      {REQUIRED_DOCS.map(docMeta => {
                        const uploaded = allDocuments.filter(d => d.type === docMeta.type).sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime())[0];
                        const isExpanded = expandedDocType === docMeta.type;
                        const isUploading = uploadingType === docMeta.type;
                        const pendingFiles = pendingFilesByType[docMeta.type] ?? [];
                        const btnLabel = uploaded && uploaded.status !== 'rejected' ? 'Re-upload' : 'Upload';
                        return (
                          <div key={docMeta.type} className="divide-y divide-border-subtle">
                            <div className="flex items-start gap-4 px-5 py-4 hover:bg-bg-hover transition-colors">
                              <div className={`flex-shrink-0 mt-0.5 w-8 h-8 rounded-lg flex items-center justify-center ${isLive ? 'bg-success/10 text-success' : uploaded ? 'bg-primary-subtle text-primary' : 'bg-bg-elevated text-text-muted'}`}>{docMeta.icon}</div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-0.5">
                                  <p className="text-sm font-medium text-text-primary">{docMeta.label}</p>
                                  {liveDocTypes.has(docMeta.type) ? <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-success/10 text-success border border-success/20 flex-shrink-0"><IconCheck size={9} strokeWidth={3} />Copied</span> : <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-warning/10 text-warning border border-warning/20 flex-shrink-0">New</span>}
                                  {!docMeta.required && <span className="text-xs text-text-muted">(Optional)</span>}
                                </div>
                                <p className="text-xs text-text-muted leading-snug">{docMeta.description}</p>
                                {uploaded && <div className="flex items-center gap-2 mt-1.5"><IconFile size={11} className="text-text-muted flex-shrink-0" /><span className="text-xs text-text-secondary truncate">{uploaded.fileName}</span><span className="text-xs text-text-muted">{uploaded.fileSize}</span><span className="text-xs text-text-muted">·</span><span className="text-xs text-text-muted">{formatDate(uploaded.uploadedAt)}</span></div>}
                              </div>
                              <div className="flex-shrink-0 flex items-center gap-2 mt-0.5">
                                {isLive ? (
                                  <><StatusBadge status="approved" /><span className="flex items-center gap-1 text-xs text-text-muted"><IconLock size={11} /> Locked</span>{uploaded && <button onClick={() => {}} className="flex items-center gap-1.5 px-3 h-7 rounded-lg border border-border-default text-xs text-text-secondary hover:text-primary hover:border-primary transition-colors"><IconDownload size={11} />Download</button>}</>
                                ) : (
                                  <>{uploaded ? <StatusBadge status={uploaded.status} /> : <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${docMeta.required ? 'bg-warning/10 text-warning border-warning/25' : 'bg-bg-elevated text-text-muted border-border-default'}`}>{docMeta.required ? 'Required' : 'Optional'}</span>}<button onClick={() => setExpandedDocType(isExpanded ? null : docMeta.type)} className="flex items-center gap-1.5 px-3 h-7 rounded-lg border border-border-default text-xs text-text-secondary hover:text-primary hover:border-primary transition-colors"><IconUpload size={11} />{btnLabel}</button></>
                                )}
                              </div>
                            </div>
                            {!isLive && isExpanded && (
                              <div className="px-5 py-4 bg-bg-elevated border-t border-border-subtle">
                                <FileUploadZone label="Drag & drop or click to browse" description="PDF, JPG, PNG — max 10 MB per file" onFilesAccepted={files => setPendingFilesByType(prev => ({ ...prev, [docMeta.type]: files }))} />
                                <div className="mt-3 flex items-center justify-end gap-2">
                                  <button type="button" onClick={() => { setExpandedDocType(null); setPendingFilesByType(prev => ({ ...prev, [docMeta.type]: [] })); }} className="px-3 h-8 rounded-lg border border-border-default text-xs text-text-secondary hover:text-text-primary transition-colors">Cancel</button>
                                  <button type="button" onClick={() => handleUploadForType(docMeta.type)} disabled={!pendingFiles.length || isUploading} className="flex items-center gap-1.5 px-4 h-8 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold disabled:opacity-40 transition-colors">
                                    <IconUpload size={12} />
                                    {isUploading ? 'Uploading…' : pendingFiles.length ? `Upload ${pendingFiles.length} file${pendingFiles.length > 1 ? 's' : ''}` : 'Select a file'}
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </CollapsibleSection>
                  );
                })()}

                {/* Review banner */}
                {showPostReview && (
                  <div className="flex items-center justify-between gap-4 px-5 py-4 bg-bg-surface border border-border-default rounded-xl">
                    <p className="text-sm text-text-secondary leading-relaxed max-w-lg">
                      Your application is currently under review. In the meantime, you can review the agreement forms. Signing will be available once the review is complete.
                    </p>
                    <div className="flex-shrink-0 flex flex-col items-end gap-1">
                      <span className="text-xs text-text-muted">Application Review</span>
                      {reviewPassed ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-success text-white text-xs font-semibold"><IconCheck size={12} /> Passed</span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-warning-subtle text-warning border border-warning/30 text-xs font-semibold">In Progress</span>
                      )}
                    </div>
                  </div>
                )}

                {/* Post-review tasks */}
                {showPostReview && (
                  <div className="pt-2">
                    <h2 className="text-sm font-semibold text-text-primary mb-3">Tasks Post Application Review</h2>
                    <div className="space-y-3">
                      <PostReviewTask
                        title="Agreement"
                        subtitle="You can review the agreements."
                        status={isLive || agreementAcknowledged ? 'done' : 'pending'}
                        action={isLive || agreementAcknowledged ? <span className="flex items-center gap-1 text-xs text-success font-medium"><IconCheck size={13} /> Acknowledged</span> : <button onClick={() => setAgreementAcknowledged(true)} className="px-4 h-8 rounded-lg border border-primary text-primary text-xs font-semibold hover:bg-primary hover:text-white transition-colors">Acknowledge</button>}
                      />
                      <PostReviewTask
                        title="Sign & Execute"
                        subtitle="You can sign and start funding your account."
                        status={isLive ? 'done' : agreementAcknowledged ? 'pending' : 'locked'}
                        action={isLive ? <span className="flex items-center gap-1 text-xs text-success font-medium"><IconCheck size={13} /> Signed</span> : <button disabled={!agreementAcknowledged} className="px-4 h-8 rounded-lg bg-primary text-white text-xs font-semibold hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors">Sign</button>}
                      />
                    </div>
                  </div>
                )}

                {/* Agreement Downloads */}
                {(isLive || stageIndex >= WORKFLOW_STAGES.indexOf('SIGN_AND_EXECUTE')) && (
                  <div className="bg-bg-surface border border-border-default rounded-xl overflow-hidden">
                    <div className="flex items-center gap-2.5 px-5 py-3.5 border-b border-border-subtle bg-bg-elevated">
                      <IconDownload size={14} className="text-text-muted flex-shrink-0" />
                      <span className="text-sm font-semibold text-text-primary">Agreement Documents</span>
                    </div>
                    <div className="divide-y divide-border-subtle">
                      <div className="flex items-center justify-between gap-4 px-5 py-4">
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-text-primary">Agreement Form</p>
                          <p className="text-xs text-text-muted mt-0.5">Pre-signature — review before signing</p>
                        </div>
                        <button onClick={() => {}} className="flex-shrink-0 flex items-center gap-1.5 px-3 h-8 rounded-lg border border-border-default text-xs font-medium text-text-secondary hover:text-primary hover:border-primary transition-colors"><IconDownload size={12} />Download</button>
                      </div>
                      <div className={`flex items-center justify-between gap-4 px-5 py-4 ${!isLive ? 'opacity-50' : ''}`}>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <p className="text-sm font-medium text-text-primary">Signed Agreement</p>
                            {!isLive && <span className="inline-flex items-center gap-1 text-xs text-text-muted"><IconLock size={10} /> Available after signing</span>}
                            {isLive && <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium bg-success/10 text-success border border-success/20"><IconCheck size={9} strokeWidth={3} /> Executed</span>}
                          </div>
                          <p className="text-xs text-text-muted">Post-signature — executed copy with all signatures</p>
                        </div>
                        <button disabled={!isLive} onClick={() => {}} className="flex-shrink-0 flex items-center gap-1.5 px-3 h-8 rounded-lg border border-border-default text-xs font-medium text-text-secondary hover:text-primary hover:border-primary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"><IconDownload size={12} />Download</button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Right: col-span-1 */}
              <div className="space-y-4">

                {/* Product details */}
                <div className="bg-bg-surface border border-border-default rounded-xl p-4">
                  <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                    <div><p className="text-xs text-text-muted mb-0.5">Trading Type</p><p className="text-sm font-medium text-text-primary">{productMeta.tradingType}</p></div>
                    <div><p className="text-xs text-text-muted mb-0.5">Opportunity ID</p><p className="text-xs font-mono text-text-secondary">{productMeta.opportunityId}</p></div>
                    <div><p className="text-xs text-text-muted mb-0.5">Options Trading</p><p className="text-sm font-medium text-text-primary">{productMeta.optionsTrading}</p></div>
                    <div><p className="text-xs text-text-muted mb-0.5">Sales Owner</p><p className="text-sm font-medium text-text-primary">{productMeta.salesOwner}</p></div>
                  </div>
                </div>

                {/* Product progress */}
                <div className="bg-bg-surface border border-border-default rounded-xl p-4">
                  <h3 className="text-sm font-semibold text-text-primary mb-3">{PRODUCT_LABELS[product]} Progress</h3>
                  <div className="space-y-2.5 mb-3">
                    <div className="flex items-center justify-between text-sm"><span className="text-text-secondary">Copied items</span><span className="text-primary font-semibold">{totalCopied}/{totalItems}</span></div>
                    <div className="flex items-center justify-between text-sm"><span className="text-text-secondary">Forms pending review</span><span className="text-warning font-semibold">{forms.filter(f => f.status === 'pending_review').length}</span></div>
                    <div className="flex items-center justify-between text-sm"><span className="text-text-secondary">Stage</span><StatusBadge status={caseData.currentStage} /></div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-1.5 bg-bg-elevated rounded-full overflow-hidden">
                      <div className="h-full bg-success rounded-full transition-all duration-700" style={{ width: `${productProgress}%` }} />
                    </div>
                    <span className="text-sm font-bold text-text-primary flex-shrink-0">{productProgress}%</span>
                  </div>
                </div>
              </div>
            </div>
          </Tabs.Panel>
        ))}

      </Tabs>
    </div>
  );
}
