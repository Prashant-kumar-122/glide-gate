import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueries } from '@tanstack/react-query';
import {
  IconArrowRight,
  IconCheck,
  IconUserPlus,
  IconPackage,
  IconAlertTriangle,
} from '@tabler/icons-react';
import { casesService, formsService, documentsService } from '../../../mocks/services/cases.service';
import { notificationsService } from '../../../mocks/services/notifications.service';
import { useAuth } from '../../../store/AuthContext';
import { useNotifications } from '../../../store/NotificationContext';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { PRODUCT_LABELS, STAGE_LABELS, WORKFLOW_STAGES } from '../../../types';
import type { Case } from '../../../types';
import { formatDate } from '../../../utils/formatters';

// ── Constants ──────────────────────────────────────────────────────────────────

const TOTAL_FORMS = 5; // ENROLLMENT + CDD + CONTROL_PERSON + TAX + SSI
const TOTAL_DOCS  = 7; // matches REQUIRED_DOCS in ApplicationTrackingPage

const APP_DISPLAY_NAMES: Record<string, string> = {
  PB:         'PB-Application',
  DvP:        'DVP-Application',
  IB_CASH:    'IB-Application',
  FCM:        'FCM-Application',
  RETIREMENT: 'Retirement-Application',
  RETAIL:     'Retail-Application',
};

const APP_SHORT_NAMES: Record<string, string> = {
  PB: 'PB', DvP: 'DVP', IB_CASH: 'IB', FCM: 'FCM', RETIREMENT: 'Retirement', RETAIL: 'Retail',
};

const FORM_TYPE_LABELS: Record<string, string> = {
  ENROLLMENT:     'Enrollment Form',
  CDD:            'Customer Due Diligence',
  CONTROL_PERSON: 'Controller Person Form',
  TAX:            'Tax Form (W-9)',
  SSI:            'Standard Settlement Instructions',
};

const DOC_TYPE_LABELS: Record<string, string> = {
  PASSPORT:                  'Passport / Government ID',
  NATIONAL_ID:               'National ID / Driver\'s License',
  ARTICLES_OF_INCORPORATION: 'Articles of Incorporation',
  PROOF_OF_ADDRESS:          'Proof of Address',
  TAX_FORM:                  'Tax Form (W-9 / W-8BEN-E)',
  ENROLLMENT_FORM:           'Enrollment Form',
  CDD_FORM:                  'CDD Supporting Document',
  CONTROL_PERSON_FORM:       'Control Person Documents',
};

interface PendingItem {
  id: string;
  name: string;
  type: string;
  productCode: string;
  status: string;
  uploadedBy: string;
  href: string;
}

// ── Stage badge ────────────────────────────────────────────────────────────────

function StageBadge({ stage }: { stage: string }) {
  const isEarly = stage === 'CLIENT_ENROLLMENT';
  const label = isEarly
    ? 'Waiting Sales Person Approval'
    : (STAGE_LABELS[stage as keyof typeof STAGE_LABELS] ?? stage);

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${
      isEarly
        ? 'bg-bg-elevated text-text-muted border border-border-default'
        : 'bg-primary-subtle text-primary border border-primary/20'
    }`}>
      {label}
    </span>
  );
}

// ── Progress chip ──────────────────────────────────────────────────────────────

function ProgressChip({ label, done, pending }: { label: string; done?: boolean; pending?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${
      done    ? 'bg-success/10 text-success border-success/20' :
      pending ? 'bg-warning/10 text-warning border-warning/20' :
                'bg-bg-elevated text-text-muted border-border-default'
    }`}>
      {done && <IconCheck size={9} strokeWidth={3} className="flex-shrink-0" />}
      {label}
    </span>
  );
}

// ── Application card ───────────────────────────────────────────────────────────

function AppCard({
  caseItem,
  forms,
  documents,
  highlighted = false,
}: {
  caseItem:    Case;
  forms:       { type: string; status: string }[];
  documents:   { status: string }[];
  highlighted?: boolean;
}) {
  const navigate = useNavigate();
  const product   = caseItem.products[0];
  const appName   = APP_DISPLAY_NAMES[product] ?? `${product}-Application`;
  const isEarly   = caseItem.currentStage === 'CLIENT_ENROLLMENT';
  const stageIdx  = WORKFLOW_STAGES.indexOf(caseItem.currentStage);

  const enrollmentDone  = forms.some(f => f.type === 'ENROLLMENT' && f.status === 'approved');
  const totalSubmitted  = forms.length;
  const totalApproved   = forms.filter(f => f.status === 'approved').length;
  const docsUploaded    = documents.length;
  const docsApproved    = documents.filter(d => d.status === 'approved').length;
  const isSignExecute   = caseItem.currentStage === 'SIGN_AND_EXECUTE';
  const signDone        = stageIdx > WORKFLOW_STAGES.indexOf('SIGN_AND_EXECUTE');

  const stageProgress = (stageIdx / Math.max(WORKFLOW_STAGES.length - 1, 1)) * 40;
  const formProgress  = totalSubmitted > 0 ? (totalApproved / TOTAL_FORMS) * 30 : 0;
  const docProgress   = docsUploaded > 0 ? (docsApproved / TOTAL_DOCS) * 30 : 0;
  const progress      = Math.min(100, Math.round(stageProgress + formProgress + docProgress));

  return (
    <div
      onClick={() => navigate(`/client/applications/${caseItem.id}`)}
      className={`rounded-xl border bg-bg-surface p-5 cursor-pointer transition-all ${
        highlighted
          ? 'border-primary/50 ring-1 ring-primary/15'
          : 'border-border-default hover:border-primary/30'
      }`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-bold text-text-primary truncate">{appName}</span>
          <StageBadge stage={caseItem.currentStage} />
        </div>
        <button
          type="button"
          onClick={e => { e.stopPropagation(); navigate(`/client/applications/${caseItem.id}`); }}
          className="flex-shrink-0 flex items-center gap-1 text-sm font-semibold text-primary hover:text-primary-hover transition-colors"
        >
          {isEarly ? 'Start' : 'Continue'}
          <IconArrowRight size={14} />
        </button>
      </div>

      {isEarly ? (
        <p className="text-xs text-text-muted leading-relaxed border border-dashed border-border-default rounded-lg px-3 py-2.5">
          We've received your interest in opening an account.
          Your application will be initiated by our team.
        </p>
      ) : (
        <>
          {/* Progress bar */}
          <div className="w-full h-1.5 rounded-full bg-bg-elevated mb-3 overflow-hidden">
            <div
              className="h-full rounded-full bg-success transition-all duration-700"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Status chips row */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <ProgressChip label="Enrollment" done={enrollmentDone} />
            <ProgressChip
              label={`Form (${totalSubmitted}/${TOTAL_FORMS})`}
              done={totalSubmitted >= TOTAL_FORMS}
            />
            <ProgressChip
              label={`Documents(${docsUploaded}/${TOTAL_DOCS})`}
              done={docsUploaded >= TOTAL_DOCS}
            />
            <ProgressChip
              label="Sign & Execute"
              done={signDone}
              pending={isSignExecute}
            />
            <span className="ml-auto text-sm font-bold text-text-primary">{progress}%</span>
          </div>
        </>
      )}
    </div>
  );
}

// ── Live account card ──────────────────────────────────────────────────────────

function LiveCard({ caseItem }: { caseItem: Case }) {
  const navigate = useNavigate();
  const product  = caseItem.products[0];

  return (
    <div
      onClick={() => navigate(`/client/applications/${caseItem.id}`)}
      className="rounded-xl border border-border-default bg-bg-surface p-5 cursor-pointer hover:border-primary/30 transition-colors"
    >
      <div className="flex items-start gap-3 mb-3">
        <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center flex-shrink-0">
          <IconPackage size={18} className="text-success" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-text-primary">
            {APP_DISPLAY_NAMES[product] ?? `${product}-Application`}
          </p>
          <p className="text-xs text-text-muted font-mono mt-0.5">{caseItem.entityId}</p>
        </div>
        <StatusBadge status="completed" />
      </div>
      <p className="text-xs text-text-muted">
        Live since {formatDate(caseItem.updatedAt)}
      </p>
    </div>
  );
}

// ── Immediate action card ──────────────────────────────────────────────────────

interface ImmediateAction {
  id:          string;
  title:       string;
  date:        string;
  appName:     string;
  urgent:      boolean;
  description: string;
  actionLabel: string;
  caseId:      string;
}

function ActionCard({ action, navigate }: { action: ImmediateAction; navigate: (p: string) => void }) {
  return (
    <div className="bg-bg-surface border border-border-default rounded-xl p-4">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-semibold text-text-primary">{action.title}</span>
        <span className="text-xs text-text-muted">{action.date}</span>
      </div>
      <div className="flex items-center gap-2 mb-2">
        <button
          onClick={() => navigate(`/client/applications/${action.caseId}`)}
          className="text-xs font-semibold text-primary hover:underline"
        >
          {action.appName}
        </button>
        {action.urgent && (
          <span className="text-xs font-semibold text-warning">Urgent</span>
        )}
      </div>
      <p className="text-xs text-text-secondary leading-relaxed mb-3">
        {action.description}
      </p>
      <button
        onClick={() => navigate(`/client/applications/${action.caseId}`)}
        className="text-sm text-primary hover:underline font-medium"
      >
        {action.actionLabel}
      </button>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function ClientDashboardPage() {
  const { user }              = useAuth();
  const navigate              = useNavigate();
  const { setNotifications }  = useNotifications();

  const [activeTab,  setActiveTab]  = useState<'pending' | 'live'>('pending');
  const [bottomTab, setBottomTab]  = useState<'items' | 'activity'>('items');

  // ── Queries ──────────────────────────────────────────────────────────────────

  const { data: cases = [] } = useQuery({
    queryKey: ['cases', 'client', user?.id],
    queryFn:  () => casesService.getCasesByClientId(user!.id),
    enabled:  !!user,
  });

  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications', user?.id],
    queryFn:  () => notificationsService.getForUser(user!.id),
    enabled:  !!user,
  });

  useEffect(() => {
    if (notifications.length > 0) setNotifications(notifications);
  }, [notifications, setNotifications]);

  const pendingCases = cases.filter(c => c.status !== 'completed');
  const liveCases    = cases.filter(c => c.status === 'completed');

  // Batch-fetch forms + docs for every pending case
  const formQueries = useQueries({
    queries: pendingCases.map(c => ({
      queryKey: ['forms', 'case', c.id],
      queryFn:  () => formsService.getFormsByCase(c.id),
    })),
  });

  const docQueries = useQueries({
    queries: pendingCases.map(c => ({
      queryKey: ['documents', c.id],
      queryFn:  () => documentsService.getDocumentsByCase(c.id),
    })),
  });

  // ── Pending items (forms + docs awaiting review) ───────────────────────────

  const pendingItems: PendingItem[] = pendingCases.flatMap((c, i) => {
    const product = c.products[0];
    const forms   = formQueries[i].data ?? [];
    const docs    = docQueries[i].data ?? [];

    const formItems: PendingItem[] = forms
      .filter(f => f.status === 'pending_review')
      .map(f => ({
        id:          f.id,
        name:        FORM_TYPE_LABELS[f.type] ?? f.type,
        type:        'Form',
        productCode: product,
        status:      'Pending Review',
        uploadedBy:  user?.fullName ?? 'You',
        href:        `/client/applications/${c.id}`,
      }));

    const docItems: PendingItem[] = docs
      .filter(d => d.status === 'uploaded' || d.status === 'under_review')
      .map(d => ({
        id:          d.id,
        name:        DOC_TYPE_LABELS[d.type as string] ?? (d.type as string).replace(/_/g, ' '),
        type:        'Document',
        productCode: product,
        status:      d.status === 'under_review' ? 'Under Review' : 'Pending Review',
        uploadedBy:  user?.fullName ?? 'You',
        href:        `/client/applications/${c.id}`,
      }));

    return [...formItems, ...docItems];
  });

  // ── Immediate actions (derived from pending_info cases / late-stage items) ─

  const immediateActions: ImmediateAction[] = pendingCases
    .filter(c =>
      c.status === 'pending_info' ||
      c.currentStage === 'SIGN_AND_EXECUTE' ||
      c.currentStage === 'ACCOUNT_SETUP'
    )
    .slice(0, 3)
    .map((c, i) => ({
      id:          `action-${c.id}`,
      title:       c.currentStage === 'SIGN_AND_EXECUTE' ? 'Sign & Execute' : 'Action Required',
      date:        new Date(Date.now() + (i + 1) * 7 * 86400000).toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' }),
      appName:     APP_DISPLAY_NAMES[c.products[0]] ?? `${c.products[0]}-Application`,
      urgent:      true,
      description: 'If we need clarifications we will flag the specific item so our team can respond quickly.',
      actionLabel: c.currentStage === 'SIGN_AND_EXECUTE' ? 'Sign' : 'Open',
      caseId:      c.id,
    }));

  // Pad with static mock actions when live data is sparse (always show 2)
  if (immediateActions.length === 0 && pendingCases.length > 0) {
    immediateActions.push(
      {
        id:          'mock-action-1',
        title:       'Sign & Execute',
        date:        '09-22-2026',
        appName:     APP_DISPLAY_NAMES[pendingCases[0].products[0]] ?? 'Application',
        urgent:      true,
        description: 'If we need clarifications we will flag the specific item so our team can respond quickly.',
        actionLabel: 'Sign',
        caseId:      pendingCases[0].id,
      },
    );
    if (pendingCases.length > 1) {
      immediateActions.push({
        id:          'mock-action-2',
        title:       'Pricing Sheet',
        date:        '09-22-2026',
        appName:     APP_DISPLAY_NAMES[pendingCases[1].products[0]] ?? 'Application',
        urgent:      true,
        description: 'If we need clarifications we will flag the specific item so our team can respond quickly.',
        actionLabel: 'Open',
        caseId:      pendingCases[1].id,
      });
    }
  }

  // ── Tab helpers ────────────────────────────────────────────────────────────

  const tabClass = (active: boolean) =>
    `px-4 pb-3 text-sm font-semibold border-b-2 transition-colors ${
      active
        ? 'border-primary text-text-primary'
        : 'border-transparent text-text-muted hover:text-text-secondary'
    }`;

  // ── Distribute pending cases across 2 sub-columns ─────────────────────────
  // Left column: first ceil(n/2), Right column: rest (may be empty)

  const leftCards  = pendingCases.slice(0, Math.ceil(pendingCases.length / 2));
  const rightCards = pendingCases.slice(Math.ceil(pendingCases.length / 2));

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="p-6">

      {/* ── Top tabs ── */}
      <div className="flex items-center border-b border-border-default mb-6">
        <button onClick={() => setActiveTab('pending')} className={tabClass(activeTab === 'pending')}>
          Pending Applications ({String(pendingCases.length).padStart(2, '0')})
        </button>
        <button onClick={() => setActiveTab('live')} className={tabClass(activeTab === 'live')}>
          Live Accounts ({String(liveCases.length).padStart(2, '0')})
        </button>
      </div>

      {/* ══ Pending Applications ═══════════════════════════════════════════════ */}
      {activeTab === 'pending' && (
        <div className="grid grid-cols-3 gap-5">

          {/* ── Left 2/3: cards + pending table ── */}
          <div className="col-span-2 space-y-5">

            {/* App card grid — 2 sub-columns */}
            {pendingCases.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 bg-bg-surface border border-border-default rounded-xl text-center gap-3">
                <p className="text-text-muted text-sm">No applications in progress.</p>
                <button
                  type="button"
                  onClick={() => navigate('/client/onboarding/new')}
                  className="text-sm text-primary hover:underline"
                >
                  Open a new account →
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {/* Left sub-column */}
                <div className="space-y-4">
                  {leftCards.map((c, i) => (
                    <AppCard
                      key={c.id}
                      caseItem={c}
                      forms={formQueries[i].data ?? []}
                      documents={docQueries[i].data ?? []}
                      highlighted={i === 0}
                    />
                  ))}
                </div>
                {/* Right sub-column */}
                <div className="space-y-4">
                  {rightCards.map((c, i) => {
                    const qi = leftCards.length + i;
                    return (
                      <AppCard
                        key={c.id}
                        caseItem={c}
                        forms={formQueries[qi].data ?? []}
                        documents={docQueries[qi].data ?? []}
                      />
                    );
                  })}
                </div>
              </div>
            )}

            {/* ── Pending Items / Recent Activities table ── */}
            <div className="bg-bg-surface border border-border-default rounded-xl overflow-hidden">
              {/* Sub-tabs */}
              <div className="flex items-center gap-1 border-b border-border-default px-5 pt-1">
                {(['items', 'activity'] as const).map(tab => {
                  const isActive = bottomTab === tab;
                  const label = tab === 'items'
                    ? `Pending Items (${String(pendingItems.length).padStart(2, '0')})`
                    : 'Recent Activities (00)';
                  return (
                    <button
                      key={tab}
                      onClick={() => setBottomTab(tab)}
                      className={`px-4 py-3 text-sm font-semibold border-b-2 transition-colors ${
                        isActive
                          ? 'border-primary text-primary'
                          : 'border-transparent text-text-muted hover:text-text-secondary hover:border-border-default'
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>

              {bottomTab === 'items' && (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="bg-bg-elevated border-b border-border-default">
                        {['Task Item', 'Type', 'Application', 'Status', 'Uploaded By'].map(col => (
                          <th key={col} className="px-5 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wide whitespace-nowrap">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle">
                      {pendingItems.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="px-5 py-10 text-center text-sm text-text-muted">
                            No pending items.
                          </td>
                        </tr>
                      ) : (
                        pendingItems.map(item => (
                          <tr key={item.id} className="hover:bg-bg-hover transition-colors group">
                            <td className="px-5 py-3.5 max-w-[200px]">
                              <button
                                onClick={() => navigate(item.href)}
                                className="text-sm font-medium text-text-primary group-hover:text-primary transition-colors text-left truncate block max-w-full"
                              >
                                {item.name}
                              </button>
                            </td>
                            <td className="px-5 py-3.5">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${
                                item.type === 'Form'
                                  ? 'bg-primary-subtle text-primary border-primary/20'
                                  : 'bg-bg-elevated text-text-secondary border-border-default'
                              }`}>
                                {item.type}
                              </span>
                            </td>
                            <td className="px-5 py-3.5">
                              <span className="text-xs font-medium text-text-secondary bg-bg-elevated border border-border-default px-2 py-0.5 rounded">
                                {APP_SHORT_NAMES[item.productCode] ?? item.productCode}
                              </span>
                            </td>
                            <td className="px-5 py-3.5">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                                item.status === 'Under Review'
                                  ? 'bg-primary/10 text-primary border-primary/20'
                                  : 'bg-warning/10 text-warning border-warning/20'
                              }`}>
                                {item.status}
                              </span>
                            </td>
                            <td className="px-5 py-3.5 text-sm text-text-secondary whitespace-nowrap">
                              {item.uploadedBy}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {bottomTab === 'activity' && (
                <div className="flex flex-col items-center justify-center py-14 gap-2 text-center">
                  <div className="w-10 h-10 rounded-full bg-bg-elevated flex items-center justify-center mb-1">
                    <IconCheck size={18} className="text-text-muted" />
                  </div>
                  <p className="text-sm font-medium text-text-secondary">All caught up</p>
                  <p className="text-xs text-text-muted">No recent activities to show.</p>
                </div>
              )}
            </div>
          </div>

          {/* ── Right 1/3: Add New Account + Immediate Actions + Ownership ── */}
          <div className="space-y-5">
            {/* Add New Account */}
            <button
              type="button"
              onClick={() => navigate('/client/onboarding/add-product')}
              className="flex items-center gap-2 px-4 h-9 rounded-lg bg-primary hover:bg-primary-hover text-white text-sm font-semibold transition-colors"
            >
              <IconArrowRight size={15} />
              Add New Account
            </button>

            {/* Immediate Actions */}
            <div>
              <h2 className="text-base font-bold text-text-primary mb-3">Immediate Actions</h2>
              {immediateActions.length === 0 ? (
                <div className="bg-bg-surface border border-border-default rounded-xl p-5 text-center">
                  <p className="text-xs text-text-muted">No immediate actions required.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {immediateActions.map(action => (
                    <ActionCard key={action.id} action={action} navigate={navigate} />
                  ))}
                </div>
              )}
            </div>

            {/* Ownership & Control */}
            <div className="bg-bg-surface border border-border-default rounded-xl p-4">
              <div className="flex items-start justify-between gap-3 mb-2">
                <h2 className="text-sm font-semibold text-text-primary">Ownership & Control</h2>
                <button
                  type="button"
                  className="flex-shrink-0 flex items-center gap-1.5 px-3 h-8 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold transition-colors"
                >
                  <IconUserPlus size={12} />
                  Invite User
                </button>
              </div>
              <p className="text-xs text-text-muted leading-relaxed">
                Manage authorized users and control persons for your entity accounts.
              </p>
            </div>

            {/* Pending info alert (if any case needs attention) */}
            {pendingCases.some(c => c.status === 'pending_info') && (
              <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-warning/10 border border-warning/20">
                <IconAlertTriangle size={16} className="text-warning flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-warning mb-0.5">Action Required</p>
                  <p className="text-xs text-text-secondary">
                    {pendingCases.filter(c => c.status === 'pending_info').length} application(s)
                    require additional information.
                  </p>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {pendingCases
                      .filter(c => c.status === 'pending_info')
                      .map(c => (
                        <button
                          key={c.id}
                          onClick={() => navigate(`/client/applications/${c.id}`)}
                          className="text-xs font-medium text-warning hover:underline"
                        >
                          {APP_DISPLAY_NAMES[c.products[0]] ?? c.id} →
                        </button>
                      ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ══ Live Accounts ══════════════════════════════════════════════════════ */}
      {activeTab === 'live' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {liveCases.length === 0 ? (
            <div className="col-span-3 py-16 text-center">
              <p className="text-text-muted text-sm">No live accounts yet.</p>
              <button
                type="button"
                onClick={() => navigate('/client/onboarding/new')}
                className="mt-3 text-sm text-primary hover:underline"
              >
                Open a new account →
              </button>
            </div>
          ) : (
            liveCases.map(c => <LiveCard key={c.id} caseItem={c} />)
          )}
        </div>
      )}

    </div>
  );
}
