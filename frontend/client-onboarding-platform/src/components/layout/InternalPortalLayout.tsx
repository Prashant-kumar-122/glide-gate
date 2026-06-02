import { useState, useRef, useEffect, useCallback } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  DockviewReact,
  type DockviewReadyEvent,
  type IDockviewPanelProps,
  type IDockviewPanelHeaderProps,
  type DockviewApi,
} from 'dockview-react';
import 'dockview-react/dist/styles/dockview.css';
import {
  IconBuildingBank,
  IconLayoutDashboard,
  IconBriefcase,
  IconChecklist,
  IconLogout,
  IconBell,
  IconCheck,
  IconChevronDown,
  IconChevronRight,
  IconMenu2,
} from '@tabler/icons-react';
import { useAuth } from '../../store/AuthContext';
import { useNotifications } from '../../store/NotificationContext';
import { DockviewApiContext } from '../../store/DockviewApiContext';
import { initials, timeAgo } from '../../utils/formatters';

// ─── Page components (rendered inside dockview panels) ────────────────────────
// Lazy-style: import at module level so they're code-split with the layout

import InternalDashboardPage from '../../features/internal-portal/dashboard/InternalDashboardPage';
import CaseListPage from '../../features/internal-portal/cases/CaseListPage';
import CaseDetailPage from '../../features/internal-portal/cases/CaseDetailPage';
import TaskDetailPage from '../../features/internal-portal/tasks/TaskDetailPage';

// ─── Panel content components ─────────────────────────────────────────────────
// Defined outside Layout to avoid recreation on every render.

const DashboardPanel = () => (
  <div className="h-full overflow-y-auto bg-bg-base">
    <InternalDashboardPage />
  </div>
);

const AllCasesPanel = () => (
  <div className="h-full overflow-y-auto bg-bg-base">
    <CaseListPage />
  </div>
);

const CaseDetailPanel = (props: IDockviewPanelProps<{ caseId: string }>) => (
  <div className="h-full overflow-y-auto bg-bg-base">
    <CaseDetailPage caseId={props.params.caseId} />
  </div>
);

const TaskDetailPanel = (props: IDockviewPanelProps<{ taskId: string }>) => (
  <div className="h-full overflow-y-auto bg-bg-base">
    <TaskDetailPage taskId={props.params.taskId} />
  </div>
);

const PANEL_COMPONENTS = {
  dashboard:  DashboardPanel,
  allCases:   AllCasesPanel,
  caseDetail: CaseDetailPanel,
  taskDetail: TaskDetailPanel,
};

// ─── Custom tab: Dashboard (no close button) ──────────────────────────────────

const PermanentTab = ({ api }: IDockviewPanelHeaderProps) => (
  <div
    onClick={() => api.setActive()}
    style={{
      display:        'flex',
      alignItems:     'center',
      padding:        '0 14px',
      height:         '100%',
      cursor:         'pointer',
      fontSize:       '13px',
      fontWeight:     600,
      userSelect:     'none',
      whiteSpace:     'nowrap',
      color:          api.isActive ? 'var(--color-text-primary, #e2e8f0)' : 'var(--color-text-muted, #64748b)',
      borderBottom:   api.isActive ? '2px solid var(--color-primary, #6366f1)' : '2px solid transparent',
    }}
  >
    Dashboard
  </div>
);

const TAB_COMPONENTS = { permanentTab: PermanentTab };

// ─── Breadcrumb builder ───────────────────────────────────────────────────────

interface Crumb { label: string; to?: string }

function useInternalBreadcrumbs(): Crumb[] {
  const { pathname } = useLocation();

  if (pathname === '/internal/dashboard')
    return [{ label: 'Dashboard' }];
  if (pathname === '/internal/cases')
    return [{ label: 'Dashboard', to: '/internal/dashboard' }, { label: 'All Cases' }];

  const caseFormMatch = pathname.match(/^\/internal\/cases\/([^/]+)\/forms\/([^/]+)$/);
  if (caseFormMatch)
    return [
      { label: 'Dashboard', to: '/internal/dashboard' },
      { label: 'Cases', to: '/internal/cases' },
      { label: caseFormMatch[1], to: `/internal/cases/${caseFormMatch[1]}` },
      { label: 'Form' },
    ];

  const caseMatch = pathname.match(/^\/internal\/cases\/([^/]+)$/);
  if (caseMatch)
    return [
      { label: 'Dashboard', to: '/internal/dashboard' },
      { label: 'Cases', to: '/internal/cases' },
      { label: caseMatch[1] },
    ];

  const taskMatch = pathname.match(/^\/internal\/tasks\/([^/]+)$/);
  if (taskMatch)
    return [
      { label: 'Dashboard', to: '/internal/dashboard' },
      { label: 'Tasks' },
      { label: taskMatch[1] },
    ];

  return [{ label: 'Dashboard', to: '/internal/dashboard' }];
}

// ─── Notification dropdown ────────────────────────────────────────────────────

function NotificationDropdown() {
  const { notifications, unreadCount, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function outside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener('mousedown', outside);
    return () => document.removeEventListener('mousedown', outside);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(p => !p)}
        className="relative flex items-center justify-center w-9 h-9 rounded-lg text-text-secondary hover:bg-bg-hover hover:text-text-primary transition-colors"
        aria-label="Notifications"
      >
        <IconBell size={20} />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 min-w-[16px] h-4 flex items-center justify-center rounded-full bg-primary text-white text-[10px] font-bold px-0.5 leading-none">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-11 w-80 bg-bg-elevated border border-border-default rounded-xl shadow-xl z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border-default">
            <span className="text-sm font-semibold text-text-primary">Notifications</span>
            {unreadCount > 0 && (
              <button onClick={markAllRead} className="flex items-center gap-1 text-xs text-primary hover:text-primary-hover transition-colors">
                <IconCheck size={12} /> Mark all read
              </button>
            )}
          </div>
          <div className="max-h-72 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="py-8 text-center text-sm text-text-muted">No notifications</p>
            ) : (
              notifications.slice(0, 5).map(n => (
                <div key={n.id} className={['px-4 py-3 border-b border-border-subtle last:border-0 transition-colors', !n.read ? 'bg-primary-subtle' : 'hover:bg-bg-hover'].join(' ')}>
                  <div className="flex items-start gap-2">
                    {!n.read && <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />}
                    <div className={!n.read ? '' : 'pl-3.5'}>
                      <p className="text-sm text-text-primary leading-snug">{n.message}</p>
                      <p className="text-xs text-text-muted mt-0.5">{timeAgo(n.createdAt)}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── User menu ────────────────────────────────────────────────────────────────

function UserMenu() {
  const { user, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function outside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener('mousedown', outside);
    return () => document.removeEventListener('mousedown', outside);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(p => !p)} className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-bg-hover transition-colors">
        <div className="w-7 h-7 rounded-full bg-primary-subtle border border-primary/20 flex items-center justify-center flex-shrink-0">
          <span className="text-xs font-bold text-primary">{user ? initials(user.fullName) : '?'}</span>
        </div>
        <div className="text-left hidden sm:block">
          <p className="text-xs font-semibold text-text-primary leading-tight max-w-[120px] truncate">{user?.fullName ?? '—'}</p>
          <p className="text-[10px] text-text-muted leading-tight max-w-[120px] truncate">{user?.email ?? '—'}</p>
        </div>
        <IconChevronDown size={13} className="text-text-muted" />
      </button>

      {open && (
        <div className="absolute right-0 top-11 w-48 bg-bg-elevated border border-border-default rounded-xl shadow-xl z-50 py-1">
          <button onClick={() => { signOut(); setOpen(false); }} className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-text-secondary hover:bg-bg-hover hover:text-danger transition-colors">
            <IconLogout size={15} /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Layout ───────────────────────────────────────────────────────────────────

export default function InternalPortalLayout() {
  const navigate    = useNavigate();
  const location    = useLocation();
  const breadcrumbs = useInternalBreadcrumbs();

  const [dockviewApi, setDockviewApi] = useState<DockviewApi | null>(null);

  // Keep a stable ref so event callbacks don't go stale
  const navigateRef = useRef(navigate);
  useEffect(() => { navigateRef.current = navigate; }, [navigate]);

  // ── Dockview ready ──────────────────────────────────────────────────────────

  const onReady = useCallback((event: DockviewReadyEvent) => {
    const api = event.api;
    setDockviewApi(api);

    // Add the permanent Dashboard tab (always first, cannot be closed)
    api.addPanel({
      id:           'dashboard',
      component:    'dashboard',
      title:        'Dashboard',
      tabComponent: 'permanentTab',
    });

    // If the user removed the dashboard somehow (e.g. drag-off), re-add it
    api.onDidRemovePanel(removed => {
      if (removed.id === 'dashboard') {
        api.addPanel({
          id:           'dashboard',
          component:    'dashboard',
          title:        'Dashboard',
          tabComponent: 'permanentTab',
        });
      }
    });

    // Sync active panel → URL (so the breadcrumb and browser address stay in sync)
    api.onDidActivePanelChange(panel => {
      if (!panel) return;
      if (panel.id === 'dashboard') {
        navigateRef.current('/internal/dashboard', { replace: true });
      } else if (panel.id === 'cases') {
        navigateRef.current('/internal/cases', { replace: true });
      } else if (panel.id.startsWith('case-')) {
        navigateRef.current(`/internal/cases/${panel.id.slice(5)}`, { replace: true });
      } else if (panel.id.startsWith('task-')) {
        navigateRef.current(`/internal/tasks/${panel.id.slice(5)}`, { replace: true });
      }
    });
  }, []);

  // ── URL → panel sync ────────────────────────────────────────────────────────

  useEffect(() => {
    if (!dockviewApi) return;

    const path = location.pathname;

    const focusOrAdd = (
      panelId:   string,
      component: string,
      title:     string,
      params?:   Record<string, string>,
    ) => {
      const existing = dockviewApi.getPanel(panelId);
      if (existing) {
        existing.api.setActive();
      } else {
        dockviewApi.addPanel({ id: panelId, component, title, params });
      }
    };

    if (path === '/internal/dashboard') {
      dockviewApi.getPanel('dashboard')?.api.setActive();
    } else if (path === '/internal/cases') {
      focusOrAdd('cases', 'allCases', 'All Cases');
    } else {
      const caseMatch = path.match(/^\/internal\/cases\/([^/]+)$/);
      if (caseMatch) {
        const caseId = caseMatch[1];
        focusOrAdd(`case-${caseId}`, 'caseDetail', caseId, { caseId });
        return;
      }
      const taskMatch = path.match(/^\/internal\/tasks\/([^/]+)$/);
      if (taskMatch) {
        const taskId = taskMatch[1];
        focusOrAdd(`task-${taskId}`, 'taskDetail', taskId, { taskId });
      }
    }
  }, [dockviewApi, location.pathname]);

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <DockviewApiContext.Provider value={dockviewApi}>
      <div className="flex flex-col h-screen bg-bg-base overflow-hidden">

        {/* ── Row 1: top bar ── */}
        <header className="flex-shrink-0 h-14 bg-bg-surface border-b border-border-default flex items-center justify-between px-6 z-10">
          <div className="flex items-center gap-5">
            <button className="text-text-muted hover:text-text-primary transition-colors">
              <IconMenu2 size={20} />
            </button>
            <div className="flex items-center gap-2">
              <IconBuildingBank size={20} className="text-primary flex-shrink-0" />
              <span className="text-sm font-bold text-text-primary whitespace-nowrap">ClearPath Onboarding Portal</span>
            </div>
            
          </div>
          <div className="flex items-center gap-2">
            <NotificationDropdown />
            <UserMenu />
          </div>
        </header>

        {/* ── Dockview content area ── */}
        <div className="flex-1 overflow-hidden">
          <DockviewReact
            components={PANEL_COMPONENTS}
            tabComponents={TAB_COMPONENTS}
            onReady={onReady}
            className="dockview-theme-dark h-full w-full"
            getTabContextMenuItems={({ panel }) => {
              // Dashboard cannot be closed — remove close option from right-click menu
              if (panel.id === 'dashboard') return [];
              return [
                { type: 'item', id: 'close', label: 'Close Tab', action: () => panel.api.close() },
              ];
            }}
          />
        </div>

      </div>
    </DockviewApiContext.Provider>
  );
}
