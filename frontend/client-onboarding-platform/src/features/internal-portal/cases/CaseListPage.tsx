import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  IconSearch,
  IconEye,
  IconFilter,
} from '@tabler/icons-react';
import { casesService } from '../../../mocks/services/cases.service';
import { PageHeader } from '../../../components/common/PageHeader';
import { StatusBadge } from '../../../components/common/StatusBadge';
import { DataTable } from '../../../components/common/DataTable';
import type { Column } from '../../../components/common/DataTable';
import type { Case, CaseStatus, WorkflowStage } from '../../../types';
import { timeAgo } from '../../../utils/formatters';

// ─── Filter controls ──────────────────────────────────────────────────────────

const STATUS_OPTIONS: { label: string; value: CaseStatus | '' }[] = [
  { label: 'All Statuses', value: '' },
  { label: 'Active', value: 'active' },
  { label: 'Pending Info', value: 'pending_info' },
  { label: 'Approved', value: 'approved' },
  { label: 'Rejected', value: 'rejected' },
  { label: 'Completed', value: 'completed' },
];

const STAGE_OPTIONS: { label: string; value: WorkflowStage | '' }[] = [
  { label: 'All Stages', value: '' },
  { label: 'Client Enrollment', value: 'CLIENT_ENROLLMENT' },
  { label: 'Sales Review', value: 'SALES_MANAGER_REVIEW' },
  { label: 'KYC', value: 'KYC' },
  { label: 'Due Diligence', value: 'DUE_DILIGENCE' },
  { label: 'Sign & Execute', value: 'SIGN_AND_EXECUTE' },
  { label: 'Account Setup', value: 'ACCOUNT_SETUP' },
  { label: 'Live', value: 'LIVE' },
];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CaseListPage() {
  const navigate = useNavigate();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<CaseStatus | ''>('');
  const [stageFilter, setStageFilter] = useState<WorkflowStage | ''>('');
  const [assignedFilter, setAssignedFilter] = useState('');

  const { data: allCases = [], isLoading } = useQuery({
    queryKey: ['cases', 'all'],
    queryFn: () => casesService.getCases(),
  });

  // ── Filter logic ────────────────────────────────────────────────────────────

  const filteredCases = allCases.filter(c => {
    const matchesSearch =
      !search ||
      c.clientName.toLowerCase().includes(search.toLowerCase()) ||
      c.id.toLowerCase().includes(search.toLowerCase()) ||
      (c.assignedToName ?? '').toLowerCase().includes(search.toLowerCase());
    const matchesStatus = !statusFilter || c.status === statusFilter;
    const matchesStage = !stageFilter || c.currentStage === stageFilter;
    const matchesAssigned =
      !assignedFilter ||
      (c.assignedToName ?? '').toLowerCase().includes(assignedFilter.toLowerCase());
    return matchesSearch && matchesStatus && matchesStage && matchesAssigned;
  });

  // ── Unique assignees for the filter ────────────────────────────────────────

  const assignees = Array.from(
    new Set(allCases.map(c => c.assignedToName).filter(Boolean))
  ) as string[];

  // ── Table columns ────────────────────────────────────────────────────────

  const columns: Column<Case>[] = [
    {
      key: 'id',
      header: 'Case ID',
      width: '120px',
      render: c => (
        <span className="font-mono text-xs text-text-secondary">{c.id}</span>
      ),
    },
    {
      key: 'clientName',
      header: 'Client Name',
      render: c => (
        <span className="font-medium text-text-primary">{c.clientName}</span>
      ),
    },
    {
      key: 'products',
      header: 'Products',
      render: c => (
        <div className="flex flex-wrap gap-1">
          {c.products.map(p => (
            <span
              key={p}
              className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-primary-subtle text-primary border border-primary/20"
            >
              {p}
            </span>
          ))}
        </div>
      ),
    },
    {
      key: 'currentStage',
      header: 'Stage',
      render: c => <StatusBadge status={c.currentStage} />,
    },
    {
      key: 'status',
      header: 'Status',
      render: c => <StatusBadge status={c.status} />,
    },
    {
      key: 'assignedToName',
      header: 'Assigned To',
      render: c =>
        c.assignedToName ? (
          <span className="text-text-secondary text-sm">{c.assignedToName}</span>
        ) : (
          <span className="text-text-muted">—</span>
        ),
    },
    {
      key: 'updatedAt',
      header: 'Updated',
      render: c => (
        <span className="text-text-muted text-xs">{timeAgo(c.updatedAt)}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      width: '80px',
      render: c => (
        <Link
          to={`/internal/cases/${c.id}`}
          onClick={e => e.stopPropagation()}
          className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-md bg-bg-elevated border border-border-default text-text-secondary hover:text-text-primary hover:border-primary hover:bg-primary-subtle transition-colors"
        >
          <IconEye size={12} />
          View
        </Link>
      ),
    },
  ];

  // ── Filter controls UI ──────────────────────────────────────────────────────

  const filterControls = (
    <div className="flex flex-wrap items-center gap-2">
      {/* Search */}
      <div className="relative">
        <IconSearch
          size={14}
          className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none"
        />
        <input
          type="text"
          placeholder="Search by client or ID…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="pl-8 pr-3 h-8 rounded-md bg-bg-elevated border border-border-default text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors w-52"
        />
      </div>

      {/* Status */}
      <select
        value={statusFilter}
        onChange={e => setStatusFilter(e.target.value as CaseStatus | '')}
        className="h-8 px-2 rounded-md bg-bg-elevated border border-border-default text-sm text-text-secondary focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors"
      >
        {STATUS_OPTIONS.map(o => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      {/* Stage */}
      <select
        value={stageFilter}
        onChange={e => setStageFilter(e.target.value as WorkflowStage | '')}
        className="h-8 px-2 rounded-md bg-bg-elevated border border-border-default text-sm text-text-secondary focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors"
      >
        {STAGE_OPTIONS.map(o => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      {/* Assigned to */}
      <select
        value={assignedFilter}
        onChange={e => setAssignedFilter(e.target.value)}
        className="h-8 px-2 rounded-md bg-bg-elevated border border-border-default text-sm text-text-secondary focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30 transition-colors"
      >
        <option value="">All Assignees</option>
        {assignees.map(a => (
          <option key={a} value={a}>
            {a}
          </option>
        ))}
      </select>

      {/* Reset */}
      {(search || statusFilter || stageFilter || assignedFilter) && (
        <button
          onClick={() => {
            setSearch('');
            setStatusFilter('');
            setStageFilter('');
            setAssignedFilter('');
          }}
          className="flex items-center gap-1 h-8 px-2.5 rounded-md text-xs text-text-muted hover:text-text-primary border border-border-subtle hover:border-border-default transition-colors"
        >
          <IconFilter size={12} />
          Clear
        </button>
      )}
    </div>
  );

  return (
    <div className="p-8">
      <PageHeader
        title="All Cases"
        subtitle="View and manage all onboarding cases"
        actions={filterControls}
      />

      {/* Record count */}
      {!isLoading && (
        <p className="text-xs text-text-muted mb-4">
          Showing{' '}
          <span className="font-semibold text-text-secondary">
            {filteredCases.length}
          </span>{' '}
          of{' '}
          <span className="font-semibold text-text-secondary">
            {allCases.length}
          </span>{' '}
          cases
        </p>
      )}

      <DataTable
        columns={columns}
        data={filteredCases}
        loading={isLoading}
        emptyMessage="No cases match your current filters."
        onRowClick={c => navigate(`/internal/cases/${c.id}`)}
      />
    </div>
  );
}
