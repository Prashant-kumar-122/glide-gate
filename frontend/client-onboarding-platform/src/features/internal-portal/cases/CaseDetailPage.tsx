import { useState, useEffect, useRef, startTransition } from 'react';
import DocViewer, { DocViewerRenderers } from '@cyntler/react-doc-viewer';
import { useParams, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  IconArrowLeft,
  IconCheck,
  IconFile,
  IconChevronRight,
  IconChevronDown,
  IconChevronUp,
  IconSend,
  IconAlertCircle,
  IconClipboardText,
  IconUser,
  IconBuildingCommunity,
  IconReceipt2,
  IconArrowsTransferDown,
  IconUpload,
  IconPlus,
  IconX,
  IconEye,
  IconUserPlus,
  IconTimeline,
  IconCircleCheck,
  IconCircleX,
  IconFolderPlus,
  IconPackage,
  IconArrowRight,
  IconMessage,
  IconFileText,
} from '@tabler/icons-react';
import { Link } from 'react-router-dom';
import { InviteUserModal } from './InviteUserModal';
import {
  casesService,
  tasksService,
  documentsService,
  messagesService,
  formsService,
} from '../../../mocks/services/cases.service';
import { useAuth } from '../../../store/AuthContext';
import { useActivity } from '../../../store/ActivityContext';
import { PageHeader } from '../../../components/common/PageHeader';
import { StatusBadge } from '../../../components/common/StatusBadge';
import {
  WORKFLOW_STAGES,
  STAGE_LABELS,
  PRODUCT_LABELS,
  TASK_TYPE_LABELS,
} from '../../../types';
import type { WorkflowStage, CommunicationMessage, FormSubmission, ActivityItem, ActivityType } from '../../../types';
import { formatDate, timeAgo } from '../../../utils/formatters';
import TaskDetailPage from '../tasks/TaskDetailPage';
import InternalFormPanel from '../forms/InternalFormPanel';

// ─── Document type labels ─────────────────────────────────────────────────────

const DOC_TYPE_LABELS: Record<string, string> = {
  PASSPORT: 'Passport',
  NATIONAL_ID: 'National ID',
  ARTICLES_OF_INCORPORATION: 'Articles of Incorporation',
  PROOF_OF_ADDRESS: 'Proof of Address',
  TAX_FORM: 'Tax Form',
  ENROLLMENT_FORM: 'Enrollment Form',
  CDD_FORM: 'CDD Form',
  CONTROL_PERSON_FORM: 'Control Person Form',
};

// ─── Sort helpers ─────────────────────────────────────────────────────────────

const TASK_STATUS_ORDER: Record<string, number> = {
  pending: 0, in_review: 1, info_requested: 2, approved: 3, rejected: 3,
};
const DOC_STATUS_ORDER: Record<string, number> = {
  uploaded: 0, under_review: 1, approved: 2, rejected: 2,
};

// ─── Required forms (shown for every case regardless of submission state) ────

const REQUIRED_FORM_TYPES: { type: string; label: string; icon: React.ReactNode }[] = [
  { type: 'ENROLLMENT',     label: 'Enrollment Form',                  icon: <IconBuildingCommunity size={15} /> },
  { type: 'CDD',            label: 'Customer Due Diligence (CDD)',     icon: <IconClipboardText size={15} /> },
  { type: 'CONTROL_PERSON', label: 'Control Persons',                  icon: <IconUser size={15} /> },
  { type: 'TAX',            label: 'Tax Form (W-9 / W-8BEN-E)',        icon: <IconReceipt2 size={15} /> },
  { type: 'SSI',            label: 'Standard Settlement Instructions', icon: <IconArrowsTransferDown size={15} /> },
];


// ─── Panel tab type ───────────────────────────────────────────────────────────

type PanelTab = {
  id: string;
  label: string;
  type: 'task' | 'form';
  formType?: string;
  submission?: FormSubmission | null;
};

// ─── Activity config — icon + colours per type ───────────────────────────────

const ACTIVITY_CFG: Record<ActivityType, { icon: React.ReactNode; bg: string; dot: string }> = {
  TASK_APPROVED:       { icon: <IconCircleCheck size={13} />, bg: 'bg-success/10 text-success',         dot: 'bg-success' },
  TASK_REJECTED:       { icon: <IconCircleX     size={13} />, bg: 'bg-danger/10 text-danger',           dot: 'bg-danger' },
  TASK_INFO_REQUESTED: { icon: <IconAlertCircle size={13} />, bg: 'bg-warning/10 text-warning',         dot: 'bg-warning' },
  CASE_CREATED:        { icon: <IconFolderPlus  size={13} />, bg: 'bg-primary/10 text-primary',         dot: 'bg-primary' },
  PRODUCT_ADDED:       { icon: <IconPackage     size={13} />, bg: 'bg-primary/10 text-primary',         dot: 'bg-primary' },
  STAGE_CHANGED:       { icon: <IconArrowRight  size={13} />, bg: 'bg-violet-500/10 text-violet-400',   dot: 'bg-violet-500' },
  COMMENT_ADDED:       { icon: <IconMessage     size={13} />, bg: 'bg-sky-500/10 text-sky-400',         dot: 'bg-sky-500' },
  DOCUMENT_UPLOADED:   { icon: <IconUpload      size={13} />, bg: 'bg-teal-500/10 text-teal-400',       dot: 'bg-teal-500' },
  FORM_SUBMITTED:      { icon: <IconFileText    size={13} />, bg: 'bg-indigo-500/10 text-indigo-400',   dot: 'bg-indigo-500' },
};

// ─── Case activity + comments slide-in panel ──────────────────────────────────

type ActivityFilter = 'all' | 'activity' | 'comments';

type TItem =
  | { kind: 'activity'; ts: number; data: ActivityItem }
  | { kind: 'message';  ts: number; data: CommunicationMessage };

function CaseActivityPanel({
  caseId,
  messages,
  newMessage,
  onNewMessage,
  onSend,
  isSending,
  onClose,
}: {
  caseId: string;
  messages: CommunicationMessage[];
  newMessage: string;
  onNewMessage: (v: string) => void;
  onSend: () => void;
  isSending: boolean;
  onClose: () => void;
}) {
  const { activities, unseenCount, markAllSeen } = useActivity();
  const [filter, setFilter] = useState<ActivityFilter>('all');
  const feedRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom whenever messages arrive
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [messages.length]);

  const caseActivities = activities.filter(a => a.caseId === caseId);
  const actItems: TItem[] = caseActivities.map(a => ({
    kind: 'activity', ts: new Date(a.createdAt).getTime(), data: a,
  }));
  const msgItems: TItem[] = messages.map(m => ({
    kind: 'message', ts: new Date(m.createdAt).getTime(), data: m,
  }));

  const timeline = (
    filter === 'all'      ? [...actItems, ...msgItems] :
    filter === 'activity' ? actItems :
    msgItems
  ).sort((a, b) => a.ts - b.ts);

  // Keyboard: Ctrl/Cmd+Enter sends
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      if (newMessage.trim()) onSend();
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-30 bg-black/30"
        onClick={onClose}
      />

      {/* Slide-in panel */}
      <div className="fixed right-0 top-14 bottom-0 z-40 w-[400px] flex flex-col bg-bg-elevated border-l border-border-default shadow-2xl">

        {/* ── Header ── */}
        <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-border-default bg-bg-surface">
          <div className="flex items-center gap-2">
            <IconTimeline size={16} className="text-primary" />
            <span className="text-sm font-semibold text-text-primary">Activity &amp; Comments</span>
            <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-bg-elevated border border-border-default text-xs text-text-muted font-medium">
              {timeline.length}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            {unseenCount > 0 && (
              <button
                onClick={markAllSeen}
                className="text-xs text-primary hover:text-primary-hover transition-colors px-2 py-1 rounded-md hover:bg-primary-subtle"
              >
                Mark seen
              </button>
            )}
            <button
              onClick={onClose}
              className="w-7 h-7 flex items-center justify-center rounded-md text-text-muted hover:text-text-primary hover:bg-bg-hover transition-colors"
            >
              <IconX size={15} />
            </button>
          </div>
        </div>

        {/* ── Filter tabs ── */}
        <div className="flex-shrink-0 flex gap-0 border-b border-border-default bg-bg-surface">
          {(['all', 'activity', 'comments'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors capitalize ${
                filter === f
                  ? 'border-primary text-primary'
                  : 'border-transparent text-text-muted hover:text-text-secondary hover:bg-bg-hover'
              }`}
            >
              {f === 'all' ? 'All' : f === 'activity' ? 'Activity' : 'Comments'}
              <span className="inline-flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-bg-elevated border border-border-default text-[10px] text-text-muted font-medium">
                {f === 'all' ? actItems.length + msgItems.length
                  : f === 'activity' ? actItems.length
                  : msgItems.length}
              </span>
            </button>
          ))}
        </div>

        {/* ── Timeline feed ── */}
        <div ref={feedRef} className="flex-1 overflow-y-auto py-3">
          {timeline.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 py-16">
              <IconTimeline size={28} className="text-text-muted opacity-40" />
              <p className="text-sm text-text-muted">No {filter === 'comments' ? 'comments' : filter === 'activity' ? 'activity' : 'activity'} yet</p>
            </div>
          ) : (
            <div className="relative px-4">
              {/* Vertical timeline line */}
              <div className="absolute left-[28px] top-0 bottom-0 w-px bg-border-subtle" />

              <div className="space-y-1">
                {timeline.map((item, idx) => {
                  // Date separator
                  const prevTs  = idx > 0 ? timeline[idx - 1].ts : null;
                  const curDate = new Date(item.ts).toDateString();
                  const prevDate = prevTs ? new Date(prevTs).toDateString() : null;
                  const showDate = curDate !== prevDate;

                  return (
                    <div key={item.kind === 'activity' ? item.data.id : item.data.id + '-msg'}>
                      {showDate && (
                        <div className="flex items-center gap-3 py-2 pl-10">
                          <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                            {curDate === new Date().toDateString() ? 'Today'
                              : curDate === new Date(Date.now() - 86400000).toDateString() ? 'Yesterday'
                              : new Date(item.ts).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                          </span>
                        </div>
                      )}

                      {item.kind === 'activity' ? (
                        /* ─ Activity row ─ */
                        <div className={`relative flex items-start gap-3 py-2 rounded-lg px-2 transition-colors hover:bg-bg-hover ${!item.data.seen ? 'bg-primary/5' : ''}`}>
                          {/* Icon node on the timeline */}
                          <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center z-10 border border-border-subtle ${ACTIVITY_CFG[item.data.type].bg}`}>
                            {ACTIVITY_CFG[item.data.type].icon}
                          </div>
                          <div className="flex-1 min-w-0 pt-0.5">
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-semibold text-text-primary">{item.data.title}</span>
                              {!item.data.seen && (
                                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${ACTIVITY_CFG[item.data.type].dot}`} />
                              )}
                            </div>
                            <p className="text-xs text-text-secondary leading-relaxed mt-0.5 line-clamp-2">
                              {item.data.description}
                            </p>
                            <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                              <span className="text-[11px] text-text-muted">{timeAgo(item.data.createdAt)}</span>
                              <span className="text-[11px] text-text-muted opacity-40">·</span>
                              <span className="text-[11px] text-text-muted">{item.data.actor}</span>
                            </div>
                          </div>
                        </div>
                      ) : (
                        /* ─ Message / comment row ─ */
                        <div className="relative flex items-start gap-3 py-2 px-2">
                          {/* Avatar node on the timeline */}
                          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-bg-surface border border-border-default flex items-center justify-center z-10">
                            <span className="text-[10px] font-bold text-text-secondary">
                              {item.data.senderName.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
                            </span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-baseline gap-2 mb-1">
                              <span className="text-xs font-semibold text-text-primary">{item.data.senderName}</span>
                              <span className="text-[11px] text-text-muted">{timeAgo(item.data.createdAt)}</span>
                            </div>
                            <div className={`inline-block max-w-full px-3 py-2 rounded-xl text-xs text-text-primary leading-relaxed ${
                              item.data.direction === 'outbound'
                                ? 'bg-bg-surface border border-border-default'
                                : 'bg-primary/10 border border-primary/20'
                            }`}>
                              {item.data.body}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* ── Chat input ── */}
        {filter !== 'activity' && (
          <div className="flex-shrink-0 border-t border-border-default p-4 bg-bg-surface">
            <textarea
              rows={2}
              placeholder="Write a comment… (Ctrl+Enter to send)"
              value={newMessage}
              onChange={e => onNewMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full px-3 py-2.5 rounded-lg bg-bg-elevated border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 resize-none transition-colors"
            />
            <div className="flex items-center justify-between mt-2">
              <span className="text-[11px] text-text-muted">Ctrl+Enter to send</span>
              <button
                onClick={onSend}
                disabled={!newMessage.trim() || isSending}
                className="flex items-center gap-1.5 px-4 h-8 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <IconSend size={12} />
                {isSending ? 'Sending…' : 'Send'}
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

// ─── Collapsible overview section ─────────────────────────────────────────────

function OverviewSection({
  title,
  count,
  pendingCount,
  expanded,
  onToggle,
  children,
  action,
}: {
  title: string;
  count: number;
  pendingCount?: number;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="border-b border-border-subtle last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-bg-hover transition-colors text-left"
      >
        <div className="flex items-center gap-2.5">
          <span className="text-sm font-semibold text-text-primary">{title}</span>
          <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-bg-elevated border border-border-default text-xs text-text-secondary font-medium">
            {count}
          </span>
          {pendingCount !== undefined && pendingCount > 0 && (
            <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-warning-subtle border border-warning/30 text-xs text-warning font-medium">
              {pendingCount} pending
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {action && <div onClick={e => e.stopPropagation()}>{action}</div>}
          <span className="text-text-muted">
            {expanded ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
          </span>
        </div>
      </button>
      {expanded && (
        <div className="border-t border-border-subtle">
          {children}
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CaseDetailPage({ caseId: caseIdProp }: { caseId?: string } = {}) {
  const { caseId: routeCaseId } = useParams<{ caseId: string }>();
  const caseId = caseIdProp ?? routeCaseId;
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [newMessage, setNewMessage]       = useState('');
  const [localMessages, setLocalMessages] = useState<CommunicationMessage[]>([]);
  const [selectedStage, setSelectedStage] = useState<WorkflowStage | ''>('');
  const [previewDoc, setPreviewDoc]       = useState<{ fileName: string; fileSize: string; type: string; status: string } | null>(null);
  const [inviteModalOpen, setInviteModalOpen]   = useState(false);
  const [activityPanelOpen, setActivityPanelOpen] = useState(false);

  // Overview collapsible state
  const [tasksExpanded, setTasksExpanded] = useState(true);
  const [formsExpanded, setFormsExpanded] = useState(true);
  const [docsExpanded, setDocsExpanded]   = useState(true);
  const [showUpload, setShowUpload]       = useState(false);

  // Inline upload state
  const [uploadFile, setUploadFile]       = useState<File | null>(null);
  const [uploadDocType, setUploadDocType] = useState('PASSPORT');
  const [localDocs, setLocalDocs]         = useState<typeof documents>([]);

  // DocView panel tabs — 'overview' is always the first tab (non-closable)
  const [openPanelTabs, setOpenPanelTabs]   = useState<PanelTab[]>([]);
  const [activePanelTab, setActivePanelTab] = useState<string>('overview');

  // URL param: ?task=<taskId> — used to deep-link into a task tab from the dashboard
  const [searchParams, setSearchParams] = useSearchParams();

  // ── Queries ──────────────────────────────────────────────────────────────────

  const { data: caseData, isLoading: caseLoading } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => casesService.getCaseById(caseId!),
    enabled: !!caseId,
  });

  const { data: tasks = [], isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks', 'case', caseId],
    queryFn: () => tasksService.getTasksByCase(caseId!),
    enabled: !!caseId,
  });

  const { data: documents = [], isLoading: docsLoading } = useQuery({
    queryKey: ['documents', 'case', caseId],
    queryFn: () => documentsService.getDocumentsByCase(caseId!),
    enabled: !!caseId,
  });

  const { data: serverMessages = [] } = useQuery({
    queryKey: ['messages', caseId],
    queryFn: () => messagesService.getMessages(caseId!),
    enabled: !!caseId,
  });

  const { data: forms = [] } = useQuery({
    queryKey: ['forms', 'case', caseId],
    queryFn: () => formsService.getFormsByCase(caseId!),
    enabled: !!caseId,
  });

  const allMessages = [...serverMessages, ...localMessages].sort(
    (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
  );

  // ── Mutations ────────────────────────────────────────────────────────────────

  const sendMessageMutation = useMutation({
    mutationFn: (body: string) =>
      messagesService.sendMessage(caseId!, user!.id, user!.fullName, body),
    onSuccess: msg => { setLocalMessages(prev => [...prev, msg]); setNewMessage(''); },
  });

  const updateStageMutation = useMutation({
    mutationFn: (stage: WorkflowStage) => casesService.updateCaseStage(caseId!, stage),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case', caseId] });
      queryClient.invalidateQueries({ queryKey: ['cases', 'all'] });
      setSelectedStage('');
    },
  });

  const uploadMutation = useMutation({
    mutationFn: () => documentsService.uploadDocument(caseId!, uploadFile!, uploadDocType),
    onSuccess: doc => {
      setLocalDocs(prev => [doc, ...prev]);
      setUploadFile(null);
      setShowUpload(false);
    },
  });

  // ── Helpers ───────────────────────────────────────────────────────────────

  const sortedTasks = [...tasks].sort((a, b) => {
    const d = (TASK_STATUS_ORDER[a.status] ?? 9) - (TASK_STATUS_ORDER[b.status] ?? 9);
    return d !== 0 ? d : new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
  });

  const allDocuments    = [...localDocs, ...documents];
  const sortedDocuments = [...allDocuments].sort((a, b) => {
    const d = (DOC_STATUS_ORDER[a.status] ?? 9) - (DOC_STATUS_ORDER[b.status] ?? 9);
    return d !== 0 ? d : new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime();
  });

  const pendingForms = forms.filter(f => f.status === 'pending_review');

  const stageIndex      = caseData ? WORKFLOW_STAGES.indexOf(caseData.currentStage) : -1;
  const completedStages = stageIndex > 0
    ? Array.from({ length: stageIndex }, (_, i) => i)
    : [];

  // ── DocView panel tab helpers ─────────────────────────────────────────────

  function openTab(tab: PanelTab) {
    if (!openPanelTabs.find(t => t.id === tab.id)) {
      setOpenPanelTabs(prev => [...prev, tab]);
    }
    setActivePanelTab(tab.id);
  }

  function closeTab(tabId: string) {
    const remaining = openPanelTabs.filter(t => t.id !== tabId);
    setOpenPanelTabs(remaining);
    if (activePanelTab === tabId) {
      setActivePanelTab(remaining.length > 0 ? remaining[remaining.length - 1].id : 'overview');
    }
  }

  const activeTab = openPanelTabs.find(t => t.id === activePanelTab);

  // ── Auto-open task tab from ?task= URL param (deep-link from dashboard) ──
  useEffect(() => {
    const taskIdParam = searchParams.get('task');
    if (!taskIdParam || tasksLoading || tasks.length === 0) return;

    const task = tasks.find(t => t.id === taskIdParam);
    if (!task) return;

    const tabLabel = task.title ?? TASK_TYPE_LABELS[task.type];

    // startTransition defers these state updates so they don't cascade synchronously
    startTransition(() => {
      setOpenPanelTabs(prev =>
        prev.find(t => t.id === taskIdParam)
          ? prev
          : [...prev, { id: taskIdParam, label: tabLabel, type: 'task' }]
      );
      setActivePanelTab(taskIdParam);
      // Remove ?task= from the URL so back-button works cleanly
      setSearchParams(prev => {
        const next = new URLSearchParams(prev);
        next.delete('task');
        return next;
      }, { replace: true });
    });
  }, [tasks, tasksLoading, searchParams.get('task')]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Loading / not found ───────────────────────────────────────────────────

  if (caseLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-64 bg-bg-elevated rounded" />
          <div className="h-48 bg-bg-surface border border-border-default rounded-lg" />
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="p-8 flex flex-col items-center justify-center gap-4 py-24">
        <IconAlertCircle size={40} className="text-danger" />
        <p className="text-text-secondary text-lg">Case not found.</p>
        <Link
          to="/internal/cases"
          className="flex items-center gap-2 text-primary hover:underline"
        >
          <IconArrowLeft size={16} />
          Back to Cases
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Page header */}
      <PageHeader
        title={`Case: ${caseData.id}`}
        subtitle={caseData.clientName}
        chips={
          <>
            {caseData.products.map(p => (
              <span
                key={p}
                className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-primary-subtle text-primary border border-primary/20"
              >
                {PRODUCT_LABELS[p]}
              </span>
            ))}
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-bg-elevated text-text-secondary border border-border-default">
              {STAGE_LABELS[caseData.currentStage]}
            </span>
            <StatusBadge status={caseData.status} />
          </>
        }
        meta={[
          { label: 'Entity ID', value: <span className="font-mono">{caseData.entityId}</span> },
          { label: 'Assigned To', value: caseData.assignedToName ?? '—' },
          { label: 'Created', value: formatDate(caseData.createdAt) },
          { label: 'Updated', value: timeAgo(caseData.updatedAt) },
        ]}
        actions={
          <button
            onClick={() => setActivityPanelOpen(true)}
            className="relative flex items-center gap-2 px-3 h-8 rounded-lg border border-border-default text-xs font-medium text-text-secondary hover:text-primary hover:border-primary hover:bg-primary-subtle transition-colors"
          >
            <IconTimeline size={15} />
            Activity &amp; Comments
            {allMessages.length > 0 && (
              <span className="inline-flex items-center justify-center min-w-[18px] h-4 px-1 rounded-full bg-primary text-white text-[10px] font-bold">
                {allMessages.length}
              </span>
            )}
          </button>
        }
      />

      {/* Three-column layout: stepper | main panel | sidebar */}
      <div className="grid grid-cols-5 gap-x-3 gap-y-6 items-start mt-3">

        {/* ── Leftmost: vertical workflow stepper ────────────────────────── */}
        <div className="col-span-1 sticky top-6">
          <div className="p-4">
            <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-4">
              Workflow Progress
            </h2>
            <div className="flex flex-col">
              {WORKFLOW_STAGES.map((stage, index) => {
                const isCompleted = completedStages.includes(index);
                const isCurrent   = index === stageIndex;
                const isLast      = index === WORKFLOW_STAGES.length - 1;
                const label       = STAGE_LABELS[stage];
                return (
                  <div key={stage} className="flex items-start gap-3">
                    <div className="flex flex-col items-center flex-shrink-0">
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center border-2 transition-all ${
                        isCompleted
                          ? 'bg-primary border-primary'
                          : isCurrent
                          ? 'bg-bg-surface border-primary ring-4 ring-primary/15'
                          : 'bg-bg-surface border-border-default'
                      }`}>
                        {isCompleted ? (
                          <IconCheck size={13} className="text-white" strokeWidth={2.5} />
                        ) : (
                          <span className={`text-xs font-semibold ${isCurrent ? 'text-primary' : 'text-text-muted'}`}>
                            {index + 1}
                          </span>
                        )}
                      </div>
                      {!isLast && (
                        <div className={`w-px mt-1 mb-1 h-6 ${isCompleted ? 'bg-primary' : 'bg-border-default'}`} />
                      )}
                    </div>
                    <div className={`pt-1 pb-1 ${!isLast ? 'mb-1' : ''}`}>
                      <p className={`text-xs font-medium leading-tight ${
                        isCompleted ? 'text-primary' : isCurrent ? 'text-text-primary' : 'text-text-muted'
                      }`}>
                        {label}
                      </p>
                      {isCurrent && (
                        <span className="inline-flex items-center mt-1 px-1.5 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary border border-primary/20">
                          Current
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── Middle: DocView panel (2 cols) ─────────────────────────────── */}
        <div className="col-span-3">

          {/* ── DocView tab bar — same style as the screenshot ── */}
          <div className="flex bg-bg-surface border border-border-default rounded-t-xl overflow-x-auto">

            {/* Overview tab — always present, no close button */}
            <button
              onClick={() => setActivePanelTab('overview')}
              className={`flex-shrink-0 flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activePanelTab === 'overview'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-text-muted hover:text-text-primary hover:bg-bg-hover'
              }`}
            >
              Overview
              {(sortedTasks.filter(t => t.status === 'pending' || t.status === 'in_review').length > 0 ||
                pendingForms.length > 0) && (
                <span className="inline-flex items-center justify-center min-w-[18px] h-4 px-1 rounded-full bg-warning-subtle border border-warning/30 text-xs text-warning font-medium">
                  {sortedTasks.filter(t => t.status === 'pending' || t.status === 'in_review').length + pendingForms.length}
                </span>
              )}
            </button>

            {/* Dynamically opened task / form tabs — all closable */}
            {openPanelTabs.map(tab => (
              <div
                key={tab.id}
                className={`flex-shrink-0 flex items-center border-b-2 transition-colors ${
                  activePanelTab === tab.id
                    ? 'border-primary'
                    : 'border-transparent hover:bg-bg-hover'
                }`}
              >
                <button
                  onClick={() => setActivePanelTab(tab.id)}
                  className={`pl-5 pr-2 py-3 text-sm font-medium whitespace-nowrap ${
                    activePanelTab === tab.id ? 'text-primary' : 'text-text-muted hover:text-text-primary'
                  }`}
                >
                  {tab.label}
                </button>
                <button
                  onClick={() => closeTab(tab.id)}
                  title="Close tab"
                  className={`pr-4 py-3 transition-colors ${
                    activePanelTab === tab.id
                      ? 'text-primary/50 hover:text-primary'
                      : 'text-text-muted hover:text-text-primary'
                  }`}
                >
                  <IconX size={12} />
                </button>
              </div>
            ))}
          </div>

          {/* ── Panel content — fixed height so tall forms/tasks scroll inside ── */}
          <div className="bg-bg-surface border border-border-default border-t-0 rounded-b-xl overflow-y-auto" style={{ height: '68vh' }}>

            {/* ── OVERVIEW tab ── */}
            {activePanelTab === 'overview' && (
              <div>

                {/* Tasks section */}
                <OverviewSection
                  title="Tasks"
                  count={sortedTasks.length}
                  pendingCount={sortedTasks.filter(t => t.status === 'pending' || t.status === 'in_review').length}
                  expanded={tasksExpanded}
                  onToggle={() => setTasksExpanded(v => !v)}
                >
                  {tasksLoading ? (
                    <div className="p-4 space-y-3">
                      {[1, 2].map(i => (
                        <div key={i} className="h-16 bg-bg-elevated rounded-lg animate-pulse" />
                      ))}
                    </div>
                  ) : sortedTasks.length === 0 ? (
                    <div className="flex items-center justify-center py-10">
                      <p className="text-text-muted text-sm">No tasks for this case.</p>
                    </div>
                  ) : (
                    <div className="divide-y divide-border-subtle">
                      {sortedTasks.map(task => (
                        <div key={task.id} className="flex items-start justify-between gap-3 px-5 py-4 hover:bg-bg-hover transition-colors">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap mb-1.5">
                              <span className="font-medium text-text-primary text-sm">
                                {TASK_TYPE_LABELS[task.type]}
                              </span>
                              <StatusBadge status={task.stage} />
                              <StatusBadge status={task.status} />
                            </div>
                            <div className="flex items-center gap-4 text-xs text-text-muted flex-wrap">
                              <span>Assignee: <span className="text-text-secondary">{task.assignedToName}</span></span>
                              <span>Created: <span className="text-text-secondary">{formatDate(task.createdAt)}</span></span>
                            </div>
                            {task.notes && (
                              <div className="mt-2 px-3 py-2 rounded-md bg-warning-subtle border-l-4 border-warning text-xs text-text-secondary">
                                {task.notes}
                              </div>
                            )}
                          </div>
                          {/* Opens task detail as a new tab inside this panel */}
                          <button
                            onClick={() => openTab({
                              id: task.id,
                              label: TASK_TYPE_LABELS[task.type],
                              type: 'task',
                            })}
                            className="flex-shrink-0 flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-md bg-bg-surface border border-border-default text-text-secondary hover:text-primary hover:border-primary hover:bg-primary-subtle transition-colors whitespace-nowrap"
                          >
                            Review Task
                            <IconChevronRight size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </OverviewSection>

                {/* Forms & Submissions section */}
                <OverviewSection
                  title="Forms & Submissions"
                  count={REQUIRED_FORM_TYPES.length}
                  pendingCount={pendingForms.length}
                  expanded={formsExpanded}
                  onToggle={() => setFormsExpanded(v => !v)}
                >
                  <div className="divide-y divide-border-subtle">
                    {[...REQUIRED_FORM_TYPES]
                      .sort((a, b) => {
                        const rank = (s?: string) =>
                          s === 'pending_review' ? 0 : !s ? 1 : s === 'under_review' ? 2 : 3;
                        return rank(forms.find(f => f.type === a.type)?.status) -
                               rank(forms.find(f => f.type === b.type)?.status);
                      })
                      .map(formMeta => {
                        const submission = forms.find(f => f.type === formMeta.type) ?? null;
                        const isPending  = submission?.status === 'pending_review';

                        return (
                          <div
                            key={formMeta.type}
                            className="flex items-center gap-4 px-5 py-3.5 hover:bg-bg-hover transition-colors group cursor-pointer"
                            onClick={() =>
                              openTab({
                                id:         `form-${formMeta.type}`,
                                label:      formMeta.label,
                                type:       'form',
                                formType:   formMeta.type,
                                submission: submission,
                              })
                            }
                          >
                            <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
                              isPending    ? 'bg-primary-subtle text-primary'
                              : submission ? 'bg-bg-elevated text-text-muted'
                              : 'bg-bg-elevated text-text-muted'
                            }`}>
                              {formMeta.icon}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className={`text-sm font-medium ${isPending ? 'text-text-primary' : 'text-text-secondary'}`}>
                                {formMeta.label}
                              </p>
                              <p className="text-xs text-text-muted mt-0.5">
                                {submission ? `Submitted ${formatDate(submission.submittedAt)}` : 'Not submitted yet'}
                              </p>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              {submission ? (
                                <StatusBadge status={submission.status} />
                              ) : (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-warning/10 text-warning border border-warning/25">
                                  Not Started
                                </span>
                              )}
                              <IconChevronRight size={14} className="text-text-muted group-hover:text-primary transition-colors" />
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </OverviewSection>

                {/* Documents section */}
                <OverviewSection
                  title="Documents"
                  count={allDocuments.length}
                  pendingCount={allDocuments.filter(d => d.status === 'uploaded' || d.status === 'under_review').length}
                  expanded={docsExpanded}
                  onToggle={() => setDocsExpanded(v => !v)}
                  action={
                    <button
                      onClick={() => setShowUpload(v => !v)}
                      className={`flex items-center gap-1.5 px-3 h-7 rounded-lg text-xs font-semibold border transition-colors ${
                        showUpload
                          ? 'bg-primary text-white border-primary'
                          : 'border-border-default text-text-secondary hover:border-primary hover:text-primary hover:bg-primary-subtle'
                      }`}
                    >
                      {showUpload ? <IconX size={12} /> : <IconPlus size={12} />}
                      {showUpload ? 'Cancel' : 'Upload'}
                    </button>
                  }
                >
                  {docsLoading ? (
                    <div className="p-4 space-y-2">
                      {[1, 2, 3].map(i => (
                        <div key={i} className="h-12 bg-bg-elevated rounded animate-pulse" />
                      ))}
                    </div>
                  ) : (
                    <>
                      {showUpload && (
                        <div className="px-5 py-4 border-b border-border-subtle bg-bg-elevated">
                          <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
                            Upload New Document
                          </p>
                          <label className={`flex flex-col items-center justify-center gap-2 border-2 border-dashed rounded-lg py-6 cursor-pointer transition-colors ${
                            uploadFile ? 'border-primary bg-primary-subtle' : 'border-border-default hover:border-primary hover:bg-primary-subtle/40'
                          }`}>
                            <input
                              type="file"
                              className="sr-only"
                              onChange={e => setUploadFile(e.target.files?.[0] ?? null)}
                            />
                            <IconUpload size={20} className={uploadFile ? 'text-primary' : 'text-text-muted'} />
                            {uploadFile ? (
                              <p className="text-sm text-primary font-medium">{uploadFile.name}</p>
                            ) : (
                              <p className="text-sm text-text-muted">Click or drag a file here</p>
                            )}
                          </label>
                          <div className="flex items-center gap-3 mt-3">
                            <select
                              value={uploadDocType}
                              onChange={e => setUploadDocType(e.target.value)}
                              className="flex-1 h-9 px-3 rounded-lg bg-bg-surface border border-border-default text-sm text-text-primary focus:outline-none focus:border-primary transition-colors"
                            >
                              {Object.entries(DOC_TYPE_LABELS).map(([val, label]) => (
                                <option key={val} value={val}>{label}</option>
                              ))}
                            </select>
                            <button
                              onClick={() => uploadFile && uploadMutation.mutate()}
                              disabled={!uploadFile || uploadMutation.isPending}
                              className="flex items-center gap-1.5 px-4 h-9 rounded-lg bg-primary hover:bg-primary-hover text-white text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                            >
                              <IconUpload size={14} />
                              {uploadMutation.isPending ? 'Uploading…' : 'Upload'}
                            </button>
                          </div>
                        </div>
                      )}

                      {sortedDocuments.length === 0 ? (
                        <div className="flex items-center justify-center py-10">
                          <p className="text-text-muted text-sm">No documents uploaded yet.</p>
                        </div>
                      ) : (
                        <div className="divide-y divide-border-subtle">
                          {sortedDocuments.map((doc, idx) => {
                            const prevDoc = sortedDocuments[idx - 1];
                            const isFirstCompleted =
                              idx > 0 &&
                              (doc.status === 'approved' || doc.status === 'rejected') &&
                              prevDoc &&
                              prevDoc.status !== 'approved' &&
                              prevDoc.status !== 'rejected';
                            return (
                              <div key={doc.id}>
                                {isFirstCompleted && (
                                  <div className="px-5 py-1.5 bg-bg-elevated">
                                    <span className="text-xs text-text-muted">Completed</span>
                                  </div>
                                )}
                                <div
                                  className={`flex items-center gap-3 px-5 py-3 hover:bg-bg-hover transition-colors cursor-pointer ${
                                    doc.status === 'approved' || doc.status === 'rejected' ? 'opacity-65' : ''
                                  }`}
                                  onClick={() => setPreviewDoc({ fileName: doc.fileName, fileSize: doc.fileSize, type: doc.type as string, status: doc.status })}
                                >
                                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-bg-elevated flex items-center justify-center">
                                    <IconFile size={15} className="text-text-muted" />
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-text-primary truncate">{doc.fileName}</p>
                                    <p className="text-xs text-text-muted">
                                      {DOC_TYPE_LABELS[doc.type] ?? doc.type} · {doc.fileSize}
                                    </p>
                                  </div>
                                  <div className="flex items-center gap-3 flex-shrink-0">
                                    <StatusBadge status={doc.status} />
                                    <span className="text-xs text-text-muted">{formatDate(doc.uploadedAt)}</span>
                                    <span className="flex items-center gap-1 text-xs text-primary font-medium">
                                      <IconEye size={12} /> Preview
                                    </span>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </>
                  )}
                </OverviewSection>
              </div>
            )}

            {/* ── TASK tab ── */}
            {activePanelTab !== 'overview' && activeTab?.type === 'task' && (
              <TaskDetailPage key={activePanelTab} taskId={activePanelTab} embedded />
            )}

            {/* ── FORM tab ── */}
            {activePanelTab !== 'overview' && activeTab?.type === 'form' && (
              <InternalFormPanel
                key={activePanelTab}
                formType={activeTab.formType!}
                submission={activeTab.submission ?? null}
              />
            )}
          </div>
        </div>

        {/* ── Right: 1 col sidebar ─────────────────────────────────────────── */}
        <div className="space-y-4">

          {/* Invite User */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-text-primary">Invite User</h2>
              <button
                onClick={() => setInviteModalOpen(true)}
                className="flex items-center gap-1.5 px-3 h-7 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-semibold transition-colors"
              >
                <IconUserPlus size={12} /> Invite
              </button>
            </div>
            <p className="text-xs text-text-muted leading-relaxed">
              Add team members or clients to collaborate on this case.
            </p>
          </div>

          {/* Stage Action */}
          <div className="bg-bg-surface border border-border-default rounded-xl p-4">
            <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-3">
              Move to Stage
            </h2>
            <select
              value={selectedStage}
              onChange={e => setSelectedStage(e.target.value as WorkflowStage | '')}
              className="w-full h-9 px-3 rounded-lg bg-bg-elevated border border-border-default text-sm text-text-primary focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 mb-3 transition-colors"
            >
              <option value="">Select stage…</option>
              {WORKFLOW_STAGES.map(s => (
                <option key={s} value={s} disabled={s === caseData.currentStage}>
                  {STAGE_LABELS[s]}{s === caseData.currentStage ? ' (current)' : ''}
                </option>
              ))}
            </select>
            <button
              onClick={() => { if (selectedStage) updateStageMutation.mutate(selectedStage as WorkflowStage); }}
              disabled={!selectedStage || selectedStage === caseData.currentStage || updateStageMutation.isPending}
              className="w-full h-9 rounded-lg bg-primary hover:bg-primary-hover text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {updateStageMutation.isPending ? 'Updating…' : 'Update Stage'}
            </button>
            {updateStageMutation.isSuccess && (
              <p className="mt-2 text-xs text-success text-center">Stage updated successfully.</p>
            )}
          </div>
        </div>
      </div>

      {/* ── Activity & Comments panel ── */}
      {activityPanelOpen && (
        <CaseActivityPanel
          caseId={caseId!}
          messages={allMessages}
          newMessage={newMessage}
          onNewMessage={setNewMessage}
          onSend={() => { if (newMessage.trim()) sendMessageMutation.mutate(newMessage.trim()); }}
          isSending={sendMessageMutation.isPending}
          onClose={() => setActivityPanelOpen(false)}
        />
      )}

      {/* ── Invite User modal ── */}
      <InviteUserModal
        opened={inviteModalOpen}
        onClose={() => setInviteModalOpen(false)}
        existingContacts={[
          { name: caseData.clientName, type: 'Client' },
          ...(caseData.assignedToName ? [{ name: caseData.assignedToName, type: 'Assigned Specialist' }] : []),
        ]}
      />

      {/* ── Document preview modal (full-screen DocViewer) ── */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex flex-col bg-black/70" onClick={() => setPreviewDoc(null)}>
          <div
            className="flex-shrink-0 flex items-center justify-between gap-4 px-6 py-3 bg-bg-surface border-b border-border-default"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-bg-elevated flex items-center justify-center">
                <IconFile size={15} className="text-text-muted" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-text-primary truncate">{previewDoc.fileName}</p>
                <p className="text-xs text-text-muted">{DOC_TYPE_LABELS[previewDoc.type] ?? previewDoc.type} · {previewDoc.fileSize}</p>
              </div>
              <StatusBadge status={previewDoc.status} />
            </div>
            <button
              onClick={() => setPreviewDoc(null)}
              className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-hover transition-colors"
            >
              <IconX size={16} />
            </button>
          </div>
          <div className="flex-1 overflow-hidden" onClick={e => e.stopPropagation()}>
            <DocViewer
              documents={[{
                uri: 'https://mozilla.github.io/pdf.js/web/compressed.tracemonkey-pldi-09.pdf',
                fileType: 'pdf',
                fileName: previewDoc.fileName,
              }]}
              pluginRenderers={DocViewerRenderers}
              style={{ height: '100%', background: '#1a1a2e' }}
              config={{ header: { disableHeader: true } }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
