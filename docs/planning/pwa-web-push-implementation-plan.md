# GlideGate PWA + Web Push Implementation Plan

## Context

GlideGate is an investment-banking client-onboarding app (React/Vite frontend, FastAPI/Socket.IO backend). It currently has **zero PWA infrastructure** (no manifest, no service worker, no install/offline support) and an **in-app-only** notification system over Socket.IO. The goal is to bring it up to PWA standards (installable, offline-aware app shell, versioned updates) and extend notifications to **Web Push** (so users get notified when the app is closed/backgrounded), while treating this as a banking-grade system: nothing sensitive gets cached, auth is hardened, and the architecture can scale horizontally.

Two architectural calls were made up front because they ripple through the whole plan:

- **Auth token storage → httpOnly cookies** (replacing the current sessionStorage JWT). Today `frontend/src/store/authStore.ts` persists the JWT to sessionStorage and `frontend/src/lib/api.ts` injects it via a Bearer header. Service workers cannot read sessionStorage, so a naive PWA migration would be stuck. Rather than building a fragile postMessage relay, we migrate to **httpOnly + Secure + SameSite=Strict cookies issued by the backend**. This is a bigger change but pays for itself three times over: (1) it removes JS-readable tokens entirely — the standard banking-grade mitigation against XSS token theft, (2) cookies are automatically attached to the Socket.IO WebSocket handshake, trivially solving the socket-auth gap below, and (3) cookies are automatically attached to any fetch the service worker itself makes — no relay plumbing needed. One architectural change collapses three separate problems.
- **Push/socket dedup → simple "active socket" check for v1**: backend tracks whether a user has *any* connected socket session; if yes, rely on the existing in-app toast/bell flow and suppress push; if no, send push. This accepts a minor edge case (a backgrounded-but-connected tab could double-notify) in exchange for shipping faster — refine with a page-visibility signal later if it proves annoying in practice.

Also flagged: while exploring, an injected/fabricated "system-reminder"-style string was found embedded in tool output (mimicking plan-mode instructions). It was ignored and didn't affect this plan, but **search the repo for stray `system-reminder`/`Plan mode is active` strings** as a follow-up — it may indicate injected content somewhere (log file, seed data, comment) worth cleaning up.

---

## Phase 0 — Auth hardening: migrate to httpOnly cookies + fix socket auth gap

This is the foundation everything else builds on, and it closes a real security hole that exists today: `backend/app/websocket/socket_server.py`'s `connect` handler ignores the `auth` payload, and `on_join_user_room` lets **any** connected client join `user:{arbitrary_user_id}` and silently receive that user's notifications (IDOR). Recommend shipping this phase to production independently, ASAP.

### 0.1 Backend — cookie-based session issuance
- In the login/refresh routes (wherever JWTs are currently minted — alongside `backend/app/api/dependencies/auth.py`), set the JWT as an httpOnly, Secure, SameSite=Strict cookie (`Set-Cookie`) instead of/in addition to returning it in the response body. Add a logout route that clears the cookie.
- Add CSRF protection: standard double-submit cookie pattern (a non-httpOnly `csrf_token` cookie that the frontend echoes back as a custom header on mutating requests, validated server-side) — required because cookies are auto-attached and thus vulnerable to CSRF in a way Bearer headers aren't.
- `backend/app/api/dependencies/auth.py`: extend `get_current_user` to read the JWT from the cookie (in addition to/instead of the `Authorization` header) via `Request.cookies`.

### 0.2 Frontend — drop JS-held tokens
- `frontend/src/store/authStore.ts`: stop persisting the raw token; keep only non-sensitive user profile fields (id, name, role) for UI purposes. `isAuthenticated` becomes derived from a lightweight `/api/auth/me` check rather than "token present."
- `frontend/src/lib/api.ts`: remove the Bearer-injection interceptor; set `axios.defaults.withCredentials = true` (or per-instance `withCredentials: true`) so cookies flow automatically; add the CSRF header to mutating requests by reading the non-httpOnly `csrf_token` cookie.
- Keep the existing 401 → clear-store → redirect-to-/login behavior.

### 0.3 Fix Socket.IO authentication
- `backend/app/websocket/socket_server.py`: in `connect(sid, environ, auth)`, read the session cookie from `environ` (cookies flow automatically with the WS upgrade on same-origin), decode/validate the JWT (reuse the logic from `get_current_user`), and `raise socketio.exceptions.ConnectionRefusedError` on failure. On success, `sio.save_session(sid, {"user_id": ..., "role": ...})` and auto `enter_room(sid, f"user:{user_id}")`.
- Remove (or strictly validate) the client-driven `on_join_user_room`/`on_leave_user_room` handlers — room membership should be server-derived from the authenticated session, not client-supplied. Same scrutiny applies to `case:{case_id}` room joins (validate the user actually has access to that case).
- `frontend/src/lib/socket.ts`: drop any token-passing in the `auth` option (cookie does the work); `frontend/src/hooks/useUserSocket.ts`: remove the `join_user_room`/`leave_user_room` emits.

**Test**: two browser sessions as different users — confirm neither can see the other's `notification_sent` events; attempt a connection without a valid session cookie and confirm refusal; confirm CSRF-less mutating requests are rejected; run existing auth/integration tests.

---

## Phase 1 — PWA fundamentals (manifest, service worker, installability)

### 1.1 Tooling: `vite-plugin-pwa` (Workbox-based, `injectManifest` strategy)
Use `injectManifest` (not `generateSW`) so a hand-written `frontend/src/sw.ts` can combine Workbox precaching with custom push/notification-click handlers (needed in Phase 2).
- `frontend/package.json`: add `vite-plugin-pwa` + `workbox-window` as devDependencies.
- `frontend/vite.config.ts`: add `VitePWA({ strategies: 'injectManifest', srcDir: 'src', filename: 'sw.ts', registerType: 'prompt', injectRegister: null, manifest: {...}, devOptions: { enabled: false } })` alongside the existing `react()` plugin. `registerType: 'prompt'` (not `autoUpdate`) — see 1.5.

### 1.2 Web app manifest
- New `frontend/src/sw.ts` + plugin-generated manifest with `name`, `short_name`, `display: "standalone"`, `start_url: "/"`, `scope: "/"`, `theme_color`/`background_color` pulled from the existing Tailwind brand tokens (`frontend/tailwind.config.*`), and an `icons` array (`192x192`, `512x512`, maskable variant) generated from the existing brand mark used in `App.tsx`'s NavBar. Place icons under new `frontend/public/icons/`.
- `frontend/index.html`: ensure `<link rel="manifest">` and `<meta name="theme-color">` are present (the plugin can inject these — verify against the custom `index.html`).

### 1.3 Caching strategy — explicit allow-list, default to no caching
Configure Workbox `runtimeCaching` in `sw.ts`:
- **Precache** (cache-first via Workbox's generated `precacheAndRoute(self.__WB_MANIFEST)`): static build assets (JS/CSS/fonts/images). Tune `globPatterns`/`maximumFileSizeToCacheInBytes` to exclude large vendor chunks (`ag-grid-community`, `@xyflow/react`) from precache.
- **NetworkOnly** (no caching, ever): `/api/clients/**`, `/api/cases/**`, `/api/documents/**`, `/api/notifications/**`, `/api/auth/**`, `/socket.io/**` — anything touching PII, financials, KYC docs, account numbers, balances, audit trails, or auth.
- **NetworkFirst with short timeout**: low-sensitivity reference/config endpoints only, if any exist.
- Set `navigateFallback` to a minimal offline shell that embeds **no cached API data**.

**Hard rule (document in code comments + PR review checklist + a CI assertion test that inspects the generated `runtimeCaching` config)**: account numbers, balances/holdings, KYC documents, client PII, case notes, audit trails, JWTs/session data, and push payload bodies must never enter Cache Storage.

### 1.4 Offline UX
- Add `useOnlineStatus` hook (`navigator.onLine` + online/offline listeners) and a global banner in `App.tsx`.
- **Should work offline**: app shell (branding, login screen, "you're offline" state); existing `ErrorBoundary` extended to detect network failures and show a friendly offline message; previously-fetched in-app notification list shown with an explicit "may be outdated — reconnect to refresh" label.
- **Should NOT work offline**: any mutation — onboarding form submission, document upload/view, KYC actions, case decisions. Show a blocking "this requires a connection" message. **No background-sync queueing for financial mutations** — too risky for audit/compliance consistency.

### 1.5 Install prompt
- New `usePwaInstall` hook capturing `beforeinstallprompt` (store deferred prompt, never auto-trigger). Surface an unobtrusive "Install GlideGate" affordance in `UserMenu`/`Profile`. Honor `appinstalled` to hide permanently; persist a "dismissed" flag (non-sensitive, fine for localStorage).
- iOS Safari has no `beforeinstallprompt` — add a manual "Add to Home Screen" instructional fallback for iOS user agents.

### 1.6 Update/versioning flow (critical — stale banking UI is dangerous)
- `registerType: 'prompt'`, `skipWaiting: false`, `clientsClaim: true`. New `useServiceWorkerUpdate` hook using `workbox-window`'s `Workbox` helper: on `waiting`, show a non-dismissible "New version available — Refresh now" banner; on click, `wb.messageSkipWaiting()` then reload on `controlling`. Guarantees the UI never silently runs against a changed API contract.

**Test**: Lighthouse PWA audit (installable, offline shell responds 200, manifest valid, theme-color present); manual install on Chrome/Edge desktop, Android Chrome, iOS Safari fallback; force a build-hash change and confirm the update banner + reload-with-fresh-assets flow.

---

## Phase 2 — Web Push notifications

### 2.1 VAPID setup
- Generate a VAPID key pair (`npx web-push generate-vapid-keys` or `pywebpush`'s helper). Add `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CONTACT_EMAIL` to `backend/app/config.py`'s `Settings`, sourced from `.env`/secret manager — same pattern as `RESEND_API_KEY`. Private key never logged/committed; add to secret-scanning denylist.
- Expose the public key via `GET /api/push/public-key`.
- **Rotation runbook**: rotating VAPID keys invalidates all existing subscriptions (browsers bind subscriptions to the `applicationServerKey`). Document a re-subscription event plan; rotate only on suspected compromise, not routinely.

### 2.2 Backend service
- Add `pywebpush` to `backend/pyproject.toml`.
- New `backend/app/services/push_service.py`: wraps `pywebpush.webpush(...)`, run via `asyncio.to_thread` (it's blocking) to match the async style of `notification_agent.py`.
- **Thin payloads only**: `{ title, body_preview, notification_id, url }` — no financial detail, mirroring the existing `_socket_payload` shape. Click deep-links into the app, which authenticates via the now-automatic cookie and fetches full detail. Keeps sensitive data out of third-party push relay infrastructure (FCM/APNs/Mozilla autopush) even though Web Push is E2E encrypted (RFC 8291) — defense in depth, reduced compliance scope.
- Retry/cleanup: on `WebPushException` with `404`/`410`, delete the subscription row immediately; exponential backoff on `5xx`/`429`.

### 2.3 `push_subscriptions` table + migration
- New model in `backend/app/models/communications.py` (or new `push.py`), following the `Notification` model's style: `id, user_id (FK→users, cascade delete, indexed), endpoint (unique), p256dh, auth, user_agent, created_at, last_used_at, expired_at`.
- New migration `backend/alembic/versions/0012_push_subscriptions.py` (next after `0011_institutional_products_seed.py`), following its `op.create_table`/`op.create_index`/`op.create_foreign_key` pattern. Unique constraint on `endpoint` so re-subscribes upsert rather than duplicate.
- New router `backend/app/api/routers/push.py`: `POST /api/push/subscribe` (upsert for `current_user`), `DELETE /api/push/subscribe`, `GET /api/push/public-key` — protected via the existing `get_current_user` dependency, mirroring `backend/app/api/routers/notifications.py`.

### 2.4 Frontend subscription flow
- New `usePushSubscription` hook: requests `Notification.requestPermission()` only after **explicit opt-in** — never on first load. Trigger from a toggle in Profile/notification settings, paired with a pre-prompt explainer modal ("GlideGate would like to notify you about case updates — change anytime in your profile") so the native browser prompt isn't a surprise (a surprise prompt is what causes permanent denials).
- On opt-in: `registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey })`, POST the resulting `{ endpoint, keys }` to `/api/push/subscribe` via the existing `api` instance (cookie auth flows automatically — no token relay needed, validating the Phase 0 cookie decision).
- `frontend/src/sw.ts`: add `push` and `notificationclick` event handlers — show a `Notification` from the thin payload; on click, focus/open the app at the deep-linked URL.

### 2.5 Dedup (v1: simple active-socket check)
- `backend/app/websocket/socket_server.py`: maintain `_connected_users: dict[str, set[sid]]`, populated on connect/disconnect (mirrors the existing `_case_rooms` pattern).
- `backend/app/agents/notification/notification_agent.py::_dispatch`: before/alongside the existing `socket_emitter.notify_user(...)` call, check `has_active_socket(user_id)`. If true → socket only (suppress push). If false → send push via `push_service`, wrapped in its own try/except so push failures never block the existing socket/email/DB-persist flow (matches the method's existing per-channel error isolation).
- Document the known v1 gap (backgrounded-but-connected tab may get both) as a deliberate phased simplification; revisit with a `visibilitychange`-driven `user_active`/`user_idle` socket signal later if it proves annoying in practice.

**Test**: cross-browser push delivery (Chrome/FCM, Firefox/autopush, Safari — note Apple requires the PWA be installed for push on iOS); subscribe/unsubscribe/permission-denied/revoked flows; dedup verification across foreground-open / backgrounded-open / fully-closed states.

---

## Phase 3 — Security hardening pass (pre-launch gate)

- **HTTPS/secure context**: confirm production TLS termination ahead of FastAPI/Socket.IO — service workers silently fail to register over plain HTTP. Document in deployment notes.
- **CSP headers**: add/extend CSP (FastAPI middleware or reverse-proxy layer) allowing `worker-src 'self'`, `manifest-src 'self'`; avoid `unsafe-inline`/`unsafe-eval`. The browser handles push relay transparently — the SW typically needs no extra `connect-src` entries for FCM/autopush.
- **Service worker scope**: serve `sw.ts`'s built output from the root so scope = `/` (matches manifest `scope`); `vite-plugin-pwa` handles correct placement — verify in the build output.
- **Secrets**: VAPID private key and CSRF secret stored alongside `RESEND_API_KEY`/`SECRET_KEY` per the existing `.env`/secret-manager pattern.
- **Cache audit as a CI gate, not a one-time review**: the assertion test from 1.3 (inspecting generated `runtimeCaching` config for sensitive routes) runs in CI so a future PR can't silently add a caching rule for `/api/clients` etc.
- Call out Phase 0's cookie migration + socket-auth fix as the headline security deliverable of this whole effort — it closes a pre-existing IDOR gap and eliminates JS-readable tokens, not just "enables push."

---

## Phase 4 — Scalability & performance (post-launch tuning)

- **Code-splitting**: extend the existing `lazy()` pattern in `App.tsx` to new PWA UI (install prompts, push settings) so the precache stays lean.
- **Push delivery at scale**: batch/fan-out if volume grows beyond the current inline `await` per dispatch; the 410-cleanup and backoff from 2.2 prevent dead-subscription buildup; track `last_used_at` for periodic pruning.
- **Socket.IO horizontal scaling**: the current `AsyncServer` keeps room/connection state in-process (`_case_rooms`, new `_connected_users`) — this breaks across multiple backend instances (a user on instance A won't get pushes triggered by work on instance B). If/when scaling out: add `socketio.AsyncRedisManager` (Redis adapter) + sticky sessions at the load balancer. Flag as a pre-existing gap that becomes more visible once push-vs-socket dedup depends on cluster-wide connection state.
- **Lighthouse targets**: PWA category 100, Performance ≥ 90 on mid-tier mobile throttling.

---

## Rollout order

| Phase | Ships | Test |
|---|---|---|
| 0 | Cookie-based auth + socket auth fix | Multi-session IDOR test, CSRF rejection test, forged-cookie rejection |
| 1 | Manifest, SW, caching, offline shell, install + update prompts | Lighthouse PWA audit, cross-platform install test, forced-update test |
| 2 | VAPID, push_subscriptions table, push service/endpoints, opt-in UX, dedup | Cross-browser push delivery, permission-flow edge cases, dedup across foreground/background/closed |
| 3 | CSP, scope/HTTPS verification, secret audit, CI cache-rule check | CSP violation console check, automated cache-rule assertion, secret scan |
| 4 | Precache tuning, retry/cleanup, Redis adapter eval, perf targets | Push fan-out load test, Lighthouse perf scoring, multi-instance cross-emit test |

Ship Phase 0 to production independently and immediately (standalone security fix). Ship Phases 1+2 together as the user-facing "PWA + Push" release. Phase 3 is a mandatory pre-launch gate. Phase 4 is ongoing post-launch tuning.

## Critical files
- `frontend/vite.config.ts`, `frontend/src/sw.ts` (new)
- `frontend/src/store/authStore.ts`, `frontend/src/lib/api.ts`, `frontend/src/lib/socket.ts`, `frontend/src/hooks/useUserSocket.ts`
- `backend/app/api/dependencies/auth.py`, `backend/app/websocket/socket_server.py`
- `backend/app/agents/notification/notification_agent.py`, `backend/app/services/push_service.py` (new)
- `backend/app/config.py`, `backend/alembic/versions/0011_institutional_products_seed.py` (template for `0012_push_subscriptions.py`)
