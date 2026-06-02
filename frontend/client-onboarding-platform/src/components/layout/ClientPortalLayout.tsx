import { useState, useRef, useEffect } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import {
  IconBuildingBank,
  IconPlus,
  IconLogout,
  IconBell,
  IconCheck,
  IconChevronDown,
  IconChevronRight,
  IconMenu2,
} from '@tabler/icons-react';
import { useAuth } from '../../store/AuthContext';
import { useNotifications } from '../../store/NotificationContext';
import { initials, timeAgo } from '../../utils/formatters';

// ─── Breadcrumb builder ───────────────────────────────────────────────────────

interface Crumb { label: string; to?: string }

const FORM_BREADCRUMB_LABELS: Record<string, string> = {
  cdd:               'Customer Due Diligence (CDD)',
  tax:               'Tax Form',
  'controller-person': 'Controller Person Form',
  ssi:               'SSI Form',
};

function useClientBreadcrumbs(): Crumb[] {
  const { pathname } = useLocation();

  if (pathname === '/client/dashboard')
    return [{ label: 'Home', to: '/client/dashboard' }];

  if (pathname === '/client/onboarding/new')
    return [{ label: 'Home', to: '/client/dashboard' }, { label: 'Open New Account' }];

  if (pathname === '/client/onboarding/add-product')
    return [{ label: 'Home', to: '/client/dashboard' }, { label: 'Add Product' }];

  const appMatch = pathname.match(/^\/client\/applications\/([^/]+)$/);
  if (appMatch)
    return [
      { label: 'Home', to: '/client/dashboard' },
      { label: 'IB Application' },
      { label: appMatch[1] },
    ];

  const formMatch = pathname.match(/^\/client\/forms\/([^/]+)\/([^/]+)$/);
  if (formMatch)
    return [
      { label: 'Home', to: '/client/dashboard' },
      { label: 'IB Application' },
      { label: formMatch[1], to: `/client/applications/${formMatch[1]}` },
      { label: FORM_BREADCRUMB_LABELS[formMatch[2]] ?? formMatch[2] },
    ];

  return [{ label: 'Home', to: '/client/dashboard' }];
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

export default function ClientPortalLayout() {
  const breadcrumbs = useClientBreadcrumbs();

  return (
    <div className="flex flex-col h-screen bg-bg-base overflow-hidden">

      {/* ── Row 1: main top bar ── */}
      <header className="flex-shrink-0 h-14 bg-bg-surface border-b border-border-default flex items-center justify-between px-6 z-10">
        {/* Left: hamburger + logo + nav */}
        <div className="flex items-center gap-5">
          <button className="text-text-muted hover:text-text-primary transition-colors">
            <IconMenu2 size={20} />
          </button>
          <div className="flex items-center gap-2">
            <IconBuildingBank size={20} className="text-primary flex-shrink-0" />
            <span className="text-sm font-bold text-text-primary whitespace-nowrap">ClearPath Client Portal</span>
          </div>
          <nav className="hidden sm:flex items-center gap-1">
            {[
              { label: 'Open New Account', to: '/client/onboarding/new', icon: IconPlus },
            ].map(({ label, to, icon: Icon }) => (
              <NavLink
                key={label}
                to={to}
                className={({ isActive }) =>
                  ['flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                    isActive ? 'bg-primary-subtle text-primary' : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary',
                  ].join(' ')
                }
              >
                <Icon size={14} /> {label}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Right: notification + user */}
        <div className="flex items-center gap-2">
          <NotificationDropdown />
          <UserMenu />
        </div>
      </header>

      {/* ── Row 2: sub-header with company + breadcrumb ── */}
      <div className="flex-shrink-0 h-11 bg-bg-surface border-b border-border-default flex items-center gap-4 px-6">
        <span className="text-sm font-bold text-text-primary whitespace-nowrap">AIB Investments Pvt. Ltd.</span>
        <nav className="flex items-center gap-1.5 text-xs">
          {breadcrumbs.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {i > 0 && <IconChevronRight size={11} className="text-text-muted" />}
              {crumb.to ? (
                <NavLink to={crumb.to} className="text-primary hover:underline">{crumb.label}</NavLink>
              ) : (
                <span className="text-text-secondary">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      </div>

      {/* ── Main content ── */}
      <main className="flex-1 overflow-y-auto bg-bg-base">
        <Outlet />
      </main>
    </div>
  );
}
