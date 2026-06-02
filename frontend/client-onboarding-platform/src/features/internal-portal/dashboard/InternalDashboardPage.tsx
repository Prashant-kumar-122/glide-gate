import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Paper, Group, Text, ThemeIcon, Divider, Button } from '@mantine/core';
import {
  IconBriefcase,
  IconClipboardList,
  IconEye,
  IconSearch,
  IconChevronRight,
  IconPlus,
} from '@tabler/icons-react';
import { OpenNewAccountModal } from './OpenNewAccountModal';

type TabId = 'tasks' | 'cases';
import {
  casesService,
  tasksService,
} from '../../../mocks/services/cases.service';
import { useAuth } from '../../../store/AuthContext';
import { PageHeader } from '../../../components/common/PageHeader';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { DataTable } from '../../../components/common/DataTable';
import type { Column } from '../../../components/common/DataTable';
import { TASK_TYPE_LABELS } from '../../../types';
import type { Case, Task, CaseStatus, WorkflowStage } from '../../../types';
import { formatDate, timeAgo } from '../../../utils/formatters';

// ─── Main page ────────────────────────────────────────────────────────────────

export default function InternalDashboardPage() {
  const { user }        = useAuth();
  const navigate        = useNavigate();
  const [activeTab,        setActiveTab]        = useState<TabId>('tasks');
  const [caseSearch,       setCaseSearch]       = useState('');
  const [caseStatusFilter, setCaseStatusFilter] = useState<CaseStatus | ''>('');
  const [caseStageFilter,  setCaseStageFilter]  = useState<WorkflowStage | ''>('');
  const [modalOpen,        setModalOpen]        = useState(false);

  // ── Queries ──────────────────────────────────────────────────────────────────

  const { data: allCases = [], isLoading: casesLoading } = useQuery({
    queryKey: ['cases', 'all'],
    queryFn:  () => casesService.getCases(),
  });

  const { data: myTasks = [], isLoading: tasksLoading } = useQuery({
    queryKey: ['tasks', 'mine', user?.id],
    queryFn:  () => tasksService.getMyTasks(user!.id),
    enabled:  !!user,
  });

  // ── Derived counts ────────────────────────────────────────────────────────

  const openCasesCount    = allCases.filter(c => c.status !== 'completed').length;
  const myTasksCount      = myTasks.length;
  const pendingReviewCount = myTasks.filter(t => t.status === 'in_review' || t.status === 'pending').length;

  // ── Filtered cases ────────────────────────────────────────────────────────

  const filteredCases = allCases.filter(c => {
    const matchesSearch  = !caseSearch || c.clientName.toLowerCase().includes(caseSearch.toLowerCase()) || c.id.toLowerCase().includes(caseSearch.toLowerCase());
    const matchesStatus  = !caseStatusFilter || c.status === caseStatusFilter;
    const matchesStage   = !caseStageFilter  || c.currentStage === caseStageFilter;
    return matchesSearch && matchesStatus && matchesStage;
  });

  // ── Task columns ──────────────────────────────────────────────────────────

  const taskColumns: Column<Task>[] = [
    { key: 'clientName', header: 'Client',    render: t => <span className="font-medium text-text-primary">{t.clientName}</span> },
    { key: 'caseId',     header: 'Case',      render: t => <span className="font-mono text-xs text-text-muted">{t.caseId}</span> },
    { key: 'type',       header: 'Task',      render: t => <span className="text-text-secondary">{t.title ?? TASK_TYPE_LABELS[t.type]}</span> },
    { key: 'stage',      header: 'Stage',     render: t => <StatusBadge status={t.stage} /> },
    { key: 'status',     header: 'Status',    render: t => <StatusBadge status={t.status} /> },
    { key: 'createdAt',  header: 'Created',   render: t => <span className="text-text-muted text-xs">{formatDate(t.createdAt)}</span> },
    {
      key: 'actions', header: '', width: '90px',
      render: t => (
        <Link
          to={`/internal/cases/${t.caseId}?task=${t.id}`}
          onClick={e => e.stopPropagation()}
          className="flex items-center gap-1 text-xs text-primary hover:text-primary-hover font-medium transition-colors"
        >
          Open in Case <IconChevronRight size={12} />
        </Link>
      ),
    },
  ];

  // ── Case columns ──────────────────────────────────────────────────────────

  const caseColumns: Column<Case>[] = [
    { key: 'id',           header: 'Case ID',     render: c => <span className="font-mono text-xs text-text-secondary">{c.id}</span> },
    { key: 'clientName',   header: 'Client',      render: c => <span className="font-medium text-text-primary">{c.clientName}</span> },
    {
      key: 'products', header: 'Products',
      render: c => (
        <div className="flex flex-wrap gap-1">
          {c.products.map(p => (
            <span key={p} className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-primary-subtle text-primary border border-primary/20">{p}</span>
          ))}
        </div>
      ),
    },
    { key: 'currentStage', header: 'Stage',       render: c => <StatusBadge status={c.currentStage} /> },
    { key: 'status',       header: 'Status',      render: c => <StatusBadge status={c.status} /> },
    { key: 'assignedToName', header: 'Assigned To', render: c => <span className="text-text-secondary text-sm">{c.assignedToName ?? <span className="text-text-muted">—</span>}</span> },
    { key: 'updatedAt',    header: 'Updated',     render: c => <span className="text-text-muted text-xs">{timeAgo(c.updatedAt)}</span> },
    {
      key: 'actions', header: '', width: '80px',
      render: c => (
        <Link to={`/internal/cases/${c.id}`} onClick={e => e.stopPropagation()} className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-md bg-bg-elevated border border-border-default text-text-secondary hover:text-text-primary hover:border-primary hover:bg-primary-subtle transition-colors">
          <IconEye size={12} /> View
        </Link>
      ),
    },
  ];

  const caseStatusOptions: { label: string; value: CaseStatus | '' }[] = [
    { label: 'All Statuses',  value: '' },
    { label: 'Active',        value: 'active' },
    { label: 'Pending Info',  value: 'pending_info' },
    { label: 'Approved',      value: 'approved' },
    { label: 'Rejected',      value: 'rejected' },
    { label: 'Completed',     value: 'completed' },
  ];

  const stageOptions: { label: string; value: WorkflowStage | '' }[] = [
    { label: 'All Stages',      value: '' },
    { label: 'Client Enrollment', value: 'CLIENT_ENROLLMENT' },
    { label: 'Sales Review',    value: 'SALES_MANAGER_REVIEW' },
    { label: 'KYC',             value: 'KYC' },
    { label: 'Due Diligence',   value: 'DUE_DILIGENCE' },
    { label: 'Sign & Execute',  value: 'SIGN_AND_EXECUTE' },
    { label: 'Account Setup',   value: 'ACCOUNT_SETUP' },
    { label: 'Live',            value: 'LIVE' },
  ];

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="py-3 px-8 space-y-6">

      {/* Header */}
      <PageHeader
        title="Internal Dashboard"
        subtitle={`Welcome back, ${user?.fullName?.split(' ')[0] ?? 'team'}`}
        actions={
          <Button
            size="sm"
            leftSection={<IconPlus size={14} />}
            onClick={() => setModalOpen(true)}
          >
            Open New Account
          </Button>
        }
      />

      {/* ── Tabbed section: My Tasks / All Cases ──────────────────────────── */}
      <section>
        <div className="flex items-center gap-1 border-b border-border-default mb-6">
          {(['tasks', 'cases'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab
                  ? 'border-primary text-primary'
                  : 'border-transparent text-text-secondary hover:text-text-primary hover:border-border-default'
              }`}
            >
              {tab === 'tasks' ? (
                <>My Tasks {!tasksLoading && myTasksCount > 0 && <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-white text-xs font-bold">{myTasksCount}</span>}</>
              ) : (
                <>All Cases {!casesLoading && <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-bg-elevated border border-border-default text-text-muted text-xs font-bold">{filteredCases.length}</span>}</>
              )}
            </button>
          ))}
        </div>

        {activeTab === 'tasks' && (
          <DataTable
            columns={taskColumns}
            data={myTasks}
            loading={tasksLoading}
            emptyMessage="No tasks assigned to you."
            onRowClick={t => navigate(`/internal/cases/${t.caseId}?task=${t.id}`)}
          />
        )}

        {activeTab === 'cases' && (
          <>
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <div className="relative">
                <IconSearch size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
                <input
                  type="text"
                  placeholder="Search cases…"
                  value={caseSearch}
                  onChange={e => setCaseSearch(e.target.value)}
                  className="pl-8 pr-3 h-8 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors"
                />
              </div>
              <select value={caseStatusFilter} onChange={e => setCaseStatusFilter(e.target.value as CaseStatus | '')} className="h-8 px-2 rounded-md bg-bg-elevated border border-border-default text-sm text-text-secondary focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors">
                {caseStatusOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <select value={caseStageFilter} onChange={e => setCaseStageFilter(e.target.value as WorkflowStage | '')} className="h-8 px-2 rounded-md bg-bg-elevated border border-border-default text-sm text-text-secondary focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors">
                {stageOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <DataTable
              columns={caseColumns}
              data={filteredCases}
              loading={casesLoading}
              emptyMessage="No cases match your filters."
              onRowClick={c => navigate(`/internal/cases/${c.id}`)}
            />
          </>
        )}
      </section>

      <OpenNewAccountModal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
      />

    </div>
  );
}
