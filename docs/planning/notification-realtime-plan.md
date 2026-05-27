# Real-Time Notification Implementation Plan

## Context

The notification system is fully designed but entirely simulated:

- `NotificationAgent._dispatch()` only does `asyncio.sleep` and logs `is_simulated=True` — no real delivery
- The backend emits a `NOTIFICATION_SENT` WebSocket event that the frontend **never consumes**
- No frontend notification UI exists — no toasts, no bell, no inbox

This plan wires **real email delivery** (via Resend) and a **live in-app notification UI** (toast + bell + drawer).

---

## Part 1 — Backend: Real Email via Resend

### File: `backend/app/agents/notification/notification_agent.py`

**Step 1 — Add env-var reads at the top of the file:**

```python
import os

_EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
_RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
_FROM_EMAIL     = os.getenv("NOTIFICATION_FROM_EMAIL", "onboarding@glidegate.io")
_FROM_NAME      = os.getenv("NOTIFICATION_FROM_NAME", "GlideGate")
```

**Step 2 — Replace `_dispatch()` with a branching version:**

```python
async def _dispatch(self, rendered, task, priority_override=None):
    channel = rendered.get("channel", "in_app")
    is_simulated = True
    status = "SIMULATED_SENT"
    latency_ms = 0

    if channel == "email" and _EMAIL_ENABLED and _RESEND_API_KEY:
        status, latency_ms, is_simulated = await self._send_email(rendered, task)
    else:
        lo, hi = _DISPATCH_LATENCY_MS
        latency = random.uniform(lo / 1000, hi / 1000)
        await asyncio.sleep(latency)
        latency_ms = round(latency * 1000)

    record = {
        "notification_id": str(uuid4()),
        "case_id":         str(task.case_id),
        "client_id":       str(task.client_id),
        "template_id":     rendered.get("template_id"),
        "channel":         channel,
        "subject":         rendered.get("subject"),
        "body_preview":    (rendered.get("body") or "")[:120],
        "priority":        priority_override or str(task.priority),
        "status":          status,
        "latency_ms":      latency_ms,
        "dispatched_at":   datetime.utcnow().isoformat(),
        "is_simulated":    is_simulated,
    }
    self._dispatch_log.append(record)
    prefix = "[SIMULATED]" if is_simulated else "[SENT]"
    self.logger.debug(f"{prefix} template={record['template_id']} channel={channel} case={task.case_id}")
    return record
```

**Step 3 — Add `_send_email()` helper:**

```python
async def _send_email(self, rendered, task):
    """Returns (status, latency_ms, is_simulated)."""
    import time
    try:
        import resend
        resend.api_key = _RESEND_API_KEY
        recipient = task.payload.get("recipient_email") or task.payload.get("client_email", "")
        if not recipient:
            self.logger.warning(f"No recipient_email in payload for case={task.case_id}, simulating")
            return "SIMULATED_SENT", 0, True

        t0 = time.monotonic()
        resend.Emails.send({
            "from":    f"{_FROM_NAME} <{_FROM_EMAIL}>",
            "to":      [recipient],
            "subject": rendered.get("subject", ""),
            "text":    rendered.get("body", ""),
        })
        return "SENT", round((time.monotonic() - t0) * 1000), False
    except Exception as exc:
        self.logger.error(f"Email dispatch failed for case={task.case_id}: {exc}")
        return "FAILED", 0, False
```

> **Note:** Callers (orchestrator, product_onboarding agents) must include `recipient_email` in the TaskPacket payload when constructing SEND_NOTIFICATION tasks.

### Install dependency

```bash
pip install resend
# add to backend/requirements.txt
```

### File: `.env` / `.env.example`

```env
# ─── Email Notifications ──────────────────────────────────────────────────────
EMAIL_ENABLED=false                        # set true to send real emails
RESEND_API_KEY=re_...                      # get from resend.com (free tier)
NOTIFICATION_FROM_EMAIL=onboarding@glidegate.io
NOTIFICATION_FROM_NAME=GlideGate
```

### Templates that send real email (7 of 11)

| Template | Trigger |
|---|---|
| `onboarding_started` | Case initiation |
| `kyc_passed` | Successful identity verification |
| `kyc_failed` | Failed identity verification |
| `kyc_escalated` | HIGH/VERY_HIGH risk, sent to human review |
| `document_requested` | On-demand document requirement |
| `onboarding_complete` | All stages passed |
| `escalation_alert` | KYC threshold exceeded (CRITICAL priority) |

The 3 in-app templates (`document_approved`, `document_needs_revision`, `product_track_update`) are delivered via the frontend toast/drawer only.

---

## Part 2 — Frontend: Notification Store

### New file: `frontend/src/store/notificationStore.ts`

```ts
import { create } from 'zustand'

export interface NotificationRecord {
  id: string
  templateId: string
  channel: 'email' | 'sms' | 'in_app'
  subject: string
  bodyPreview: string
  priority: string
  receivedAt: string
  read: boolean
}

interface NotificationStore {
  notifications: NotificationRecord[]
  appendNotification: (n: NotificationRecord) => void
  markAllRead: () => void
}

export const useNotificationStore = create<NotificationStore>((set) => ({
  notifications: [],
  appendNotification: (n) =>
    set((s) =>
      s.notifications.some((x) => x.id === n.id)
        ? s
        : { notifications: [n, ...s.notifications] },
    ),
  markAllRead: () =>
    set((s) => ({ notifications: s.notifications.map((n) => ({ ...n, read: true })) })),
}))

export const useUnreadCount = () =>
  useNotificationStore((s) => s.notifications.filter((n) => !n.read).length)
```

---

## Part 3 — Frontend: Toast on `NOTIFICATION_SENT`

### Update: `frontend/src/features/agent-trace/useAgentTraceSocket.ts`

Add to the `EV` constant:
```ts
NOTIFICATION_SENT: 'notification_sent',
```

Add import:
```ts
import { useNotificationStore } from '@/store/notificationStore'
import type { NotificationRecord } from '@/store/notificationStore'
```

Add inside `useEffect`:
```ts
const appendNotification = useNotificationStore.getState().appendNotification

function onNotificationSent(data: {
  notification_id?: string
  template_id?: string
  channel?: string
  subject?: string
  body_preview?: string
  priority?: string
}) {
  const record: NotificationRecord = {
    id:          data.notification_id ?? `${Date.now()}`,
    templateId:  data.template_id ?? '',
    channel:     (data.channel ?? 'in_app') as NotificationRecord['channel'],
    subject:     data.subject ?? 'New notification',
    bodyPreview: data.body_preview ?? '',
    priority:    data.priority ?? 'NORMAL',
    receivedAt:  new Date().toISOString(),
    read:        false,
  }
  appendNotification(record)
}

socket.on(EV.NOTIFICATION_SENT, onNotificationSent)
// inside cleanup:
socket.off(EV.NOTIFICATION_SENT, onNotificationSent)
```

### New file: `frontend/src/features/notifications/NotificationToast.tsx`

```tsx
import { useEffect, useState } from 'react'
import { Mail, Bell, X } from 'lucide-react'
import { useNotificationStore } from '@/store/notificationStore'
import type { NotificationRecord } from '@/store/notificationStore'

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  HIGH:     'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  NORMAL:   'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  LOW:      'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
}

export function NotificationToast() {
  const notifications = useNotificationStore((s) => s.notifications)
  const [visible, setVisible] = useState<NotificationRecord | null>(null)

  useEffect(() => {
    const latest = notifications[0]
    if (!latest) return
    setVisible(latest)
    const t = setTimeout(() => setVisible(null), 4000)
    return () => clearTimeout(t)
  }, [notifications[0]?.id])

  if (!visible) return null

  const Icon = visible.channel === 'email' ? Mail : Bell

  return (
    <div className="fixed bottom-5 right-5 z-50 flex w-80 items-start gap-3 rounded-xl border border-gray-200 bg-white p-3.5 shadow-lg dark:border-gray-700 dark:bg-gray-800">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50 dark:bg-blue-950">
        <Icon className="h-4 w-4 text-blue-500" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-xs font-semibold text-gray-800 dark:text-gray-100">
            {visible.subject}
          </p>
          <span className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold ${PRIORITY_COLORS[visible.priority] ?? PRIORITY_COLORS.NORMAL}`}>
            {visible.priority}
          </span>
        </div>
        {visible.bodyPreview && (
          <p className="mt-0.5 truncate text-[10px] text-gray-500 dark:text-gray-400">
            {visible.bodyPreview}
          </p>
        )}
      </div>
      <button onClick={() => setVisible(null)} className="shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
```

---

## Part 4 — Frontend: Notification Bell + Drawer

### New file: `frontend/src/features/notifications/NotificationBell.tsx`

```tsx
import { useState } from 'react'
import { Bell } from 'lucide-react'
import { useUnreadCount, useNotificationStore } from '@/store/notificationStore'
import { NotificationDrawer } from './NotificationDrawer'

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const unread = useUnreadCount()
  const markAllRead = useNotificationStore((s) => s.markAllRead)

  function toggle() {
    setOpen((o) => !o)
    if (!open) markAllRead()
  }

  return (
    <>
      <button
        onClick={toggle}
        className="relative mr-2 rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-700 hover:text-white"
        aria-label="Notifications"
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>
      {open && <NotificationDrawer onClose={() => setOpen(false)} />}
    </>
  )
}
```

### New file: `frontend/src/features/notifications/NotificationDrawer.tsx`

```tsx
import { X, Mail, Bell } from 'lucide-react'
import { useNotificationStore } from '@/store/notificationStore'

const CHANNEL_ICON = {
  email:  Mail,
  sms:    Bell,
  in_app: Bell,
}

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
  HIGH:     'bg-amber-100 text-amber-700',
  NORMAL:   'bg-blue-100 text-blue-700',
  LOW:      'bg-gray-100 text-gray-600',
}

function fmtTime(ts: string) {
  try { return new Date(ts).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) }
  catch { return ts }
}

export function NotificationDrawer({ onClose }: { onClose: () => void }) {
  const notifications = useNotificationStore((s) => s.notifications)
  const markAllRead   = useNotificationStore((s) => s.markAllRead)

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-12 z-50 flex h-[calc(100vh-48px)] w-80 flex-col border-l border-gray-200 bg-white shadow-2xl dark:border-gray-700 dark:bg-gray-900">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-700">
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">
            Notifications
            {notifications.length > 0 && (
              <span className="ml-1.5 text-xs text-gray-400">({notifications.length})</span>
            )}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={markAllRead}
              className="text-[10px] text-blue-500 hover:underline"
            >
              Mark all read
            </button>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="flex h-full items-center justify-center px-6 text-center">
              <p className="text-xs text-gray-400">No notifications yet.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-50 dark:divide-gray-800">
              {notifications.map((n) => {
                const Icon = CHANNEL_ICON[n.channel] ?? Bell
                return (
                  <li key={n.id} className={`flex items-start gap-3 px-4 py-3 ${!n.read ? 'bg-blue-50/40 dark:bg-blue-950/20' : ''}`}>
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
                      <Icon className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <p className="truncate text-xs font-medium text-gray-800 dark:text-gray-100">{n.subject}</p>
                        <span className={`shrink-0 rounded px-1 py-0.5 text-[9px] font-bold ${PRIORITY_COLORS[n.priority] ?? PRIORITY_COLORS.NORMAL}`}>
                          {n.priority}
                        </span>
                      </div>
                      {n.bodyPreview && (
                        <p className="mt-0.5 truncate text-[10px] text-gray-500 dark:text-gray-400">{n.bodyPreview}</p>
                      )}
                      <p className="mt-0.5 text-[9px] text-gray-300 dark:text-gray-600">{fmtTime(n.receivedAt)}</p>
                    </div>
                    {!n.read && <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />}
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </>
  )
}
```

---

## Part 5 — Mount in Global NavBar

### File: `frontend/src/App.tsx`

**Add import:**
```ts
import { NotificationBell } from '@/features/notifications/NotificationBell'
import { NotificationToast } from '@/features/notifications/NotificationToast'
```

**Inside `NavBar()` — place bell between the `flex-1` spacer and the theme toggle:**
```tsx
<div className="flex-1" />

{isAuthenticated && <NotificationBell />}   {/* ← add this line */}

{/* Theme toggle */}
<button onClick={toggleTheme} ...>
```

**Inside `App()` return — mount toast once outside routes:**
```tsx
<div className="flex min-h-screen flex-col bg-gray-50 dark:bg-gray-950">
  <NavBar />
  <main className="flex flex-1 flex-col">
    <Routes>...</Routes>
  </main>
  <NotificationToast />   {/* ← add this line */}
</div>
```

---

## Verification

| Step | Expected result |
|---|---|
| Set `EMAIL_ENABLED=true` + valid `RESEND_API_KEY`, trigger onboarding | Real email arrives in inbox with correct subject |
| Check `notifications` DB table | `is_simulated=false`, `status=SENT`, `sent_at` populated |
| Watch `NOTIFICATION_SENT` socket event fire | Toast pops bottom-right for 4s |
| Click bell icon | Drawer opens; lists all notifications with channel icons |
| Unread count badge | Red badge on bell shows count, clears on open |
| Escalation flow | `[URGENT] Compliance Escalation` email delivered at CRITICAL priority |
| Set `EMAIL_ENABLED=false` | Simulation mode resumes, no errors |
