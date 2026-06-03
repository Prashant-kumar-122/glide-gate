# Sales Manager Role — Institutional Case Creation

**Status: COMPLETE** (implemented 2026-06-03)

---

## Context

A new `sales_manager` role was introduced alongside `advisor`. Sales managers have full advisor-level access (case list, workflow tracker, documents, contact centre) plus a dedicated "Open New Account" entry point to create institutional cases on behalf of existing clients. The modal captures Legal Entity Name, institutional product selection, and an invited client (looked up by email with auto-fill). Once created the invited client can immediately see the case in their dashboard.

---

## What Was Built

### Backend

| File | Change |
|------|--------|
| `backend/alembic/versions/0010_add_sales_manager_role.py` | New migration — added `'sales_manager'` to `users.role` CHECK constraint. `down_revision` points to `0009_product_type_and_question`. |
| `backend/app/api/routers/auth.py` | Added `GET /auth/lookup-client?email=` endpoint. Returns `UserOut` if found with `role == "client"`. Returns `404 no_account_found` or `422 not_a_client` otherwise. |
| `backend/app/api/routers/cases.py` | Added `legal_entity_name: str \| None` to `InitiateCaseRequest`. Stored in `extra_metadata`; used as `case_name` when no explicit name supplied. Added `"sales_manager"` to all `require_role()` guards. |
| `backend/app/api/routers/clients.py` | Added `"sales_manager"` to `POST /clients` and `PATCH /clients/{id}` guards. |
| `backend/app/api/routers/reviews.py` | Added `"sales_manager"` to all review route guards. |
| `backend/app/api/routers/audit.py` | Added `"sales_manager"` to all audit route guards. |
| `backend/app/api/routers/collaboration.py` | Added `"sales_manager": "SalesManager"` to `_ROLE_MAP`. |
| `db/seeds/07_users.py` | Added `salesmanager@glide-gate.local / Sales123! / sales_manager` seed user (`SALES_MANAGER_USER_ID = b0000000-0003-...`). |

### Frontend

| File | Change |
|------|--------|
| `frontend/src/store/authStore.ts` | Added `'sales_manager'` to `AuthUser.role` union. |
| `frontend/src/lib/api.ts` | Added `'sales_manager'` to `UserOut.role` union. |
| `frontend/src/components/ProtectedRoute.tsx` | Added `sales_manager: '/'` to `DEFAULT_ROUTE`. |
| `frontend/src/App.tsx` | Added `sales_manager` to `ROLE_HOME`, `NAV_LINKS` (Advisor Workspace, Contact Centre), and route `allowedRoles` for `/`, `/contact-centre`, `/agent-trace`, `/profile`. |
| `frontend/src/design-system/tokens.ts` | Added `SalesManager` to `TeamRole`, `ROLE_COLORS` (indigo palette), and `ROLE_LABEL` (`"Sales Mgr"`). |
| `frontend/src/hooks/useDocuments.ts` | Added `useLookupClient` hook (`GET /auth/lookup-client`). Expanded `useInitiateCase` body type to accept `client_id`, `legal_entity_name`, `metadata`. |
| `frontend/src/features/advisor/InstitutionalCaseModal.tsx` | **New file.** "Open New Account" modal with: Legal Entity Name field, institutional product grid (2-col toggle cards), debounced client email lookup (400ms) with auto-fill first/last name, warning states for unknown/non-client emails, "Open account" submit button. |
| `frontend/src/features/advisor/CaseListTable.tsx` | Added "Open New Account" button (indigo, visible only to `sales_manager`). Opens `InstitutionalCaseModal`. On success calls `openCaseTab(caseId, clientId, legalEntityName)` so the tab label shows the entity name immediately. |

---

## Post-Implementation Fixes

- **Alembic multiple heads** — `0010` initially pointed at `b8acf771a6d9` (same parent as `0009`). Fixed by updating `down_revision` to `"0009_product_type_and_question"`. Migration then ran cleanly.
- **Tab label showing case ID** — `openCaseTab` was called with `caseId` as the label. Fixed by passing `legalEntityName` through `onCreated(caseId, clientId, label)` so the tab title is correct immediately on creation.
- **Button/modal copy** — renamed "New Institutional Case" → **"Open New Account"**, modal title and action button updated to match.

---

## Credentials

| Role | Email | Password |
|------|-------|----------|
| Sales Manager | `salesmanager@glide-gate.local` | `Sales123!` |
| Client (for invite testing) | `aarav.mehta@demo.glide-gate.local` | `Client123!` |

---

## Verification

1. Log in as `salesmanager@glide-gate.local` → lands on `/` (advisor workspace).
2. "Open New Account" button visible in the case list toolbar; not visible when logged in as advisor.
3. Open modal → products grid shows institutional products; typing a valid client email auto-fills first/last name with green confirmation; invalid email shows amber warning; non-client email shows "not registered as a client" warning.
4. Submit → tab opens with Legal Entity Name as title (not the UUID).
5. Log in as `aarav.mehta@demo.glide-gate.local` → new institutional case card appears in `/client` dashboard.
