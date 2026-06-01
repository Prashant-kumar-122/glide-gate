# GlideGate — Production Readiness Implementation Plan

## Context for the implementing session

This plan was produced after a full audit of the GlideGate codebase against the BRD and production best practices. The app is an AI-powered wealth management onboarding platform (FastAPI backend, React/TypeScript frontend, PostgreSQL). All issues below were verified by reading the source code directly.

The project root is `c:\Users\Wissen\Projects\glide-gate`.  
Backend: `backend/` (FastAPI, SQLAlchemy async, python-socketio)  
Frontend: `frontend/` (React 18, Vite, Zustand, TanStack Query)  
DB seeds: `db/seeds/`

Work through phases in order — later phases depend on earlier ones. Within each phase, tasks are independent and can be parallelised. Mark each task done as you complete it.

---

## Phase 1 — Critical (must fix before any production traffic)

### 1.1 Add database indexes on all FK columns

**Problem:** Every FK column across all models has `index=False` (the SQLAlchemy default). PostgreSQL does not auto-index FK columns, so every join is a sequential scan.

**Files to edit:**
- `backend/app/models/cases.py` — `OnboardingCase.client_id`, `OnboardingCase.assigned_advisor_id`; `CaseProduct.case_id`, `CaseProduct.product_id`; `CaseProductStep.case_product_id`
- `backend/app/models/documents.py` — `Document.case_id`, `Document.client_id`, `Document.parent_doc_id`
- `backend/app/models/agents.py` — `AgentTask.case_id`, `AgentTask.client_id`; `EventLog.case_id`; `MCPToolCall.task_id`
- `backend/app/models/kyc_reviews.py` — `KYCCheck.case_id`, `KYCCheck.client_id`; `HumanReview.case_id`, `HumanReview.client_id`
- `backend/app/models/communications.py` — all FK columns (ConversationMessage, Notification, CaseSummary, CollaborationRoom, CollaborationComment)
- `backend/app/models/questionnaire.py` — `OnboardingAnswer.case_id`; `OnboardingQuestionSession.case_id`
- `backend/app/models/accounts.py` — `ClientAccount.client_id`

**What to do:** Add `index=True` to every `mapped_column(ForeignKey(...))` call. Also add `index=True` to high-query columns: `Document.status`, `Document.category`, `OnboardingCase.status`, `OnboardingCase.current_stage`, `AgentTask.status`.

Example pattern:
```python
# Before
case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False)
# After
case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False, index=True)
```

---

### 1.2 Generate the initial Alembic migration

**Problem:** `backend/alembic/versions/` is empty. The schema is managed by raw seed scripts with no migration history. There is no rollback path.

**What to do:**
1. Read `backend/alembic/env.py` to confirm it imports `Base` and all models (it does — just verify).
2. Run from the `backend/` directory:
   ```
   alembic revision --autogenerate -m "initial_schema"
   alembic upgrade head
   ```
3. Commit the generated migration file.
4. Add a note in `README.md` (if one exists) that schema changes must go through `alembic revision --autogenerate`.

> After Phase 1.1 is done (indexes added), run this — the migration will capture both the tables and the indexes together.

---

### 1.3 Add file size limit on document uploads

**Problem:** `backend/app/api/routers/documents.py` line 264: `raw = await file.read()` reads the entire upload into memory with no size gate. A multi-GB upload will exhaust server RAM.

**File to edit:** `backend/app/api/routers/documents.py`

**What to do:**
1. Add to `backend/app/config.py`:
   ```python
   MAX_UPLOAD_SIZE_MB: int = 50
   ```
2. In `upload_document`, after `raw = await file.read()`, add:
   ```python
   max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
   if len(raw) > max_bytes:
       raise UnprocessableError(
           f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB"
       )
   ```

---

### 1.4 Add ownership check on document download

**Problem:** `backend/app/api/routers/documents.py` `download_document` endpoint (line 385) calls `get_current_user` but never checks whether the requesting user owns the document. A client who knows any document UUID can download another client's KYC documents.

**File to edit:** `backend/app/api/routers/documents.py`

**What to do:** After `doc = await _get_doc_or_404(document_id, db)` in `download_document`, add:
```python
if _user.get("role") == "client" and str(doc.client_id) != _user.get("sub"):
    raise NotFoundError("Document", str(document_id))
```
Apply the same pattern to `get_document` (the GET `/documents/{document_id}` endpoint).

---

### 1.5 Guard Demo Mode from running in production

**Problem:** `backend/app/api/dependencies/auth.py` line 43: when `DEMO_MODE=True`, unauthenticated requests are granted advisor-level access. If this flag is accidentally set in production, the entire API is public.

**File to edit:** `backend/app/main.py`

**What to do:** In `on_startup` (or the lifespan function after task 2.4), add:
```python
if settings.DEMO_MODE and settings.is_production:
    raise RuntimeError(
        "DEMO_MODE=True is not allowed in production. "
        "Set APP_ENV=development or set DEMO_MODE=False."
    )
```

---

## Phase 2 — Security (fix before public launch)

### 2.1 Move JWT from localStorage to sessionStorage

**Problem:** `frontend/src/store/authStore.ts` uses Zustand `persist` without specifying a `storage` — this defaults to `localStorage`. JWTs in localStorage are readable by any JavaScript on the page (XSS risk).

**File to edit:** `frontend/src/store/authStore.ts`

**What to do:** Change the persist configuration to use `sessionStorage`:
```typescript
import { persist, createJSONStorage } from 'zustand/middleware'

// In the persist options:
{
  name: 'gg_auth',
  storage: createJSONStorage(() => sessionStorage),
}
```
This means the token is cleared on browser close (acceptable for a B2B wealth management app). If "remember me" is needed later, that's a separate feature.

---

### 2.2 Add rate limiting on auth endpoints

**Problem:** `/auth/login` and `/auth/signup` have no rate limiting, making them open to brute-force and credential stuffing.

**Files to edit:** `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/api/routers/auth.py`

**What to do:**
1. Add to `pyproject.toml` dependencies: `slowapi = "^0.1.9"`
2. In `backend/app/main.py`, set up the limiter:
   ```python
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address
   from slowapi.errors import RateLimitExceeded

   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   ```
3. In `backend/app/api/routers/auth.py`, decorate the login and signup endpoints:
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   from fastapi import Request
   
   limiter = Limiter(key_func=get_remote_address)
   
   @router.post("/login", ...)
   @limiter.limit("10/minute")
   async def login(request: Request, body: LoginRequest, ...):
       ...
   
   @router.post("/signup", ...)
   @limiter.limit("5/minute")
   async def signup(request: Request, body: SignupRequest, ...):
       ...
   ```

---

### 2.3 Replace `python-jose` with `PyJWT`

**Problem:** `python-jose` (used in `backend/app/services/auth/auth_service.py` and `backend/app/api/dependencies/auth.py`) has unpatched CVEs and is effectively unmaintained.

**Files to edit:** `backend/pyproject.toml`, `backend/app/services/auth/auth_service.py`, `backend/app/api/dependencies/auth.py`

**What to do:**
1. In `pyproject.toml`: remove `python-jose = { version = "^3.3.0", extras = ["cryptography"] }`, add `PyJWT = { version = "^2.9.0", extras = ["crypto"] }`
2. In `auth_service.py`: replace `from jose import jwt` with `import jwt`; update `jwt.encode(payload, key, algorithm=alg)` — PyJWT returns a string directly (no `.decode()` needed).
3. In `auth.py` (dependencies): replace `from jose import JWTError, jwt` with `import jwt; from jwt.exceptions import InvalidTokenError`; replace `JWTError` catch with `InvalidTokenError`.
4. Run `poetry update` and verify login/signup still works.

---

### 2.4 Add security response headers

**Problem:** No `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`, or Content-Security-Policy headers.

**Files to edit:** `backend/pyproject.toml`, `backend/app/main.py`

**What to do:**
1. Add to `pyproject.toml`: `secure = "^0.3.0"` (the `secure` library for Starlette/FastAPI)
2. In `main.py`, add a middleware:
   ```python
   from secure import Secure
   secure_headers = Secure.with_default_headers()
   
   @app.middleware("http")
   async def set_secure_headers(request, call_next):
       response = await call_next(request)
       secure_headers.set_headers(response)
       return response
   ```
   Or manually add headers for more control:
   ```python
   @app.middleware("http")
   async def security_headers(request, call_next):
       response = await call_next(request)
       response.headers["X-Content-Type-Options"] = "nosniff"
       response.headers["X-Frame-Options"] = "DENY"
       response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
       if settings.is_production:
           response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
       return response
   ```

---

### 2.5 Add input length validation on auth and key endpoints

**Problem:** `SignupRequest` in `backend/app/api/routers/auth.py` accepts `email`, `first_name`, `last_name` with no max length. Overly long strings can cause DB/performance issues.

**File to edit:** `backend/app/api/routers/auth.py`

**What to do:**
```python
from pydantic import BaseModel, Field, field_validator

class SignupRequest(BaseModel):
    email: str = Field(max_length=254)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(max_length=128)
```
Apply similar `Field(max_length=...)` constraints to `ProfileUpdateRequest` and to `LoginRequest.email`.

---

### 2.6 Fix `uploaded_by` to store user identity, not role

**Problem:** `backend/app/api/routers/documents.py` line 285: `uploaded_by=user.get("role", "unknown")` stores `"advisor"` or `"client"` — not who actually uploaded the document. The audit trail is missing user identity.

**File to edit:** `backend/app/api/routers/documents.py`

**What to do:** Change line 285 to:
```python
uploaded_by=user.get("sub"),  # stores the user UUID
```
If you want a human-readable name in the audit log, pass `user.get("name", user.get("sub"))` instead.

---

## Phase 3 — Backend Quality

### 3.1 Fix deprecated `datetime.utcnow()` across all models

**Problem:** `datetime.utcnow()` is deprecated in Python 3.12+ (returns a timezone-naive datetime). Used 68+ times across 9 model files.

**Files to edit:** All files in `backend/app/models/` that use `datetime.utcnow`.  
Affected: `accounts.py`, `admin_config.py`, `agents.py`, `cases.py`, `clients.py`, `communications.py`, `documents.py`, `kyc_reviews.py`, `questionnaire.py`

**What to do:** Global find-and-replace across all model files:
- `default=datetime.utcnow` → `default=lambda: datetime.now(timezone.utc)`
- `onupdate=datetime.utcnow` → `onupdate=lambda: datetime.now(timezone.utc)`
- Any inline `datetime.utcnow()` call → `datetime.now(timezone.utc)`

Make sure `from datetime import datetime, timezone` is imported (not just `from datetime import datetime`) in each file.

---

### 3.2 Migrate lifespan to the new FastAPI pattern

**Problem:** `backend/app/main.py` lines 63–89 use `@app.on_event("startup")` and `@app.on_event("shutdown")` which are deprecated since FastAPI 0.93.

**File to edit:** `backend/app/main.py`

**What to do:** Replace the two `on_event` functions with a single lifespan context manager:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # All startup logic here
    logger.info(f"GlideGate API starting — env={settings.APP_ENV} ...")
    from app.services.validation.prompt_override_store import load_from_db as load_prompt_overrides
    from app.services.llm.deterministic_controls_applier import load_from_db as load_llm_config
    from app.services.compliance.checkpoint_rule_repository import load_from_db as load_checkpoint_rules
    await load_prompt_overrides()
    await load_llm_config()
    await load_checkpoint_rules()
    if settings.DEMO_MODE and settings.is_production:
        raise RuntimeError("DEMO_MODE=True is not allowed in production.")
    await orchestration_service.start()
    yield
    # Shutdown logic here
    await orchestration_service.stop()
    logger.info("GlideGate API shutting down")

app = FastAPI(
    title="GlideGate CADF API",
    ...,
    lifespan=lifespan,
)
```
Remove the old `@app.on_event` functions entirely.

---

### 3.3 Fix fire-and-forget `asyncio.create_task` — use `BackgroundTasks`

**Problem:** `backend/app/api/routers/documents.py` lines 341–377 use bare `asyncio.create_task()` for validation and percentage updates. These tasks have no lifecycle management and are silently dropped on process restart.

**File to edit:** `backend/app/api/routers/documents.py`

**What to do:** FastAPI provides `BackgroundTasks` for exactly this use case. Replace `asyncio.create_task` with FastAPI's `BackgroundTasks`:

```python
from fastapi import BackgroundTasks

@router.post("/documents/{document_id}/validate", ...)
async def trigger_validation(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("Advisor", "Admin")),
) -> ValidateAcceptedOut:
    doc = await _get_doc_or_404(document_id, db)
    if doc.status == "RECEIVED":
        doc.status = "UNDER_REVIEW"
        await db.commit()
    background_tasks.add_task(run_validate_in_background, document_id)
    return ValidateAcceptedOut(...)
```

Apply the same pattern to `_update_case_percentage_for_docs` and `_trigger_kyc_if_all_docs_approved` in `update_document_status`.

> Note: `BackgroundTasks` is still in-process. For true durability across restarts, the longer-term solution is ARQ (Redis-backed async job queue), but BackgroundTasks is the correct FastAPI pattern and eliminates the untracked task problem.

---

## Phase 4 — Frontend Quality

### 4.1 Add React Error Boundaries

**Problem:** No `ErrorBoundary` component exists anywhere in the frontend. Any unhandled render-time exception crashes the entire app to a blank screen.

**Files to create/edit:** Create `frontend/src/components/ErrorBoundary.tsx`, then wrap all top-level route pages in `frontend/src/App.tsx`.

**What to do:**

Create `frontend/src/components/ErrorBoundary.tsx`:
```tsx
import { Component, ErrorInfo, ReactNode } from 'react'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean; error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Something went wrong</h2>
            <p className="mt-1 text-sm text-gray-500">{this.state.error?.message}</p>
            <button onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
```

In `frontend/src/App.tsx`, wrap each route's element:
```tsx
import ErrorBoundary from '@/components/ErrorBoundary'

// In each Route:
element={
  <ProtectedRoute allowedRoles={['advisor']}>
    <ErrorBoundary>
      <AdvisorWorkspace />
    </ErrorBoundary>
  </ProtectedRoute>
}
```

---

### 4.2 Move `@tanstack/react-query-devtools` to devDependencies

**Problem:** `frontend/package.json` lists `@tanstack/react-query-devtools` in `dependencies`, so it's bundled into the production build.

**Files to edit:** `frontend/package.json`, `frontend/src/main.tsx` (or wherever `ReactQueryDevtools` is rendered).

**What to do:**
1. Move the package from `dependencies` to `devDependencies` in `package.json`.
2. Conditionally render devtools only in development:
   ```tsx
   {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
   ```
3. Run `npm install` to update `package-lock.json`.

---

### 4.3 Add route-level code splitting with React.lazy

**Problem:** All 8 route components in `frontend/src/App.tsx` are eagerly imported, loading all code upfront regardless of the user's role.

**File to edit:** `frontend/src/App.tsx`

**What to do:** Replace direct imports with lazy imports:
```tsx
import { lazy, Suspense } from 'react'

const AdvisorWorkspace = lazy(() => import('@/routes/AdvisorWorkspace'))
const ClientPortal = lazy(() => import('@/routes/ClientPortal'))
const ContactCentre = lazy(() => import('@/routes/ContactCentre'))
const AgentTrace = lazy(() => import('@/routes/AgentTrace'))
const AdminConfig = lazy(() => import('@/routes/AdminConfig'))
// Keep Login/Signup eager — they're the landing pages

// Wrap the <Routes> block in Suspense:
<Suspense fallback={<div className="flex min-h-screen items-center justify-center">
  <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
</div>}>
  <Routes>
    ...
  </Routes>
</Suspense>
```

---

## Phase 5 — DevOps

### 5.1 Add Docker and docker-compose

**Problem:** No `Dockerfile` or `docker-compose.yml` exists. Every environment requires manual setup.

**What to create:**

`backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app
RUN pip install poetry==1.8.4
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction

COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:socket_app", "--host", "0.0.0.0", "--port", "8000"]
```

`docker-compose.yml` (project root):
```yaml
version: "3.9"
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: glide_gate
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file: .env
    ports: ["8000:8000"]
    depends_on:
      db:
        condition: service_healthy
    volumes: ["./uploads:/app/uploads"]

  frontend:
    image: node:20-alpine
    working_dir: /app
    command: sh -c "npm install && npm run dev -- --host"
    ports: ["5173:5173"]
    volumes: ["./frontend:/app", "/app/node_modules"]
    environment:
      - VITE_API_URL=http://localhost:8000

volumes:
  pgdata:
```

---

### 5.2 Add production environment validation

**Problem:** There's no validation that ensures production-required settings (non-default SECRET_KEY, S3 storage, etc.) are set before the app starts.

**File to edit:** `backend/app/config.py`

**What to do:** Add a `@model_validator` to the `Settings` class:
```python
from pydantic import model_validator

@model_validator(mode="after")
def validate_production_settings(self) -> "Settings":
    if self.APP_ENV == "production":
        if self.SECRET_KEY == "change-me-in-production-use-openssl-rand-hex-32":
            raise ValueError("SECRET_KEY must be changed in production")
        if self.DOCUMENT_STORAGE_BACKEND == "local":
            raise ValueError("DOCUMENT_STORAGE_BACKEND must be 's3' in production")
        if not self.AWS_ACCESS_KEY_ID:
            raise ValueError("AWS_ACCESS_KEY_ID must be set in production")
    return self
```

---

## Phase 6 — BRD Gap Fixes (from BRD alignment review)

### 6.1 Add product-specific questionnaire sections

**Problem:** BRD Section 15.3 requires three conditional question rules that are missing from `db/seeds/03_questionnaire.py`:
1. Cash Account Suitability section — shown only when `selected_products` includes `cash_management_account`
2. Retirement Account Details section — shown only when `selected_products` includes `retirement_account`
3. `source_of_wealth` question — triggered when `annual_income > 250000`

**File to edit:** `db/seeds/03_questionnaire.py`

**What to do:** Add the following sections after the existing financial_information section.

**Cash Account Suitability** (show_if: `selected_products` contains `cash_management_account`):
- `cash_primary_use` — "What is the primary use for this Cash Management Account?" (select: Daily transactions, Emergency fund, Business operations, Investment sweep, Other)
- `cash_expected_monthly_volume` — "What is your expected monthly transaction volume?" (select: Under £5,000, £5,000–£25,000, £25,000–£100,000, Over £100,000)
- `cash_overdraft_facility` — "Do you require an overdraft facility?" (yes_no)

**Retirement Account Details** (show_if: `selected_products` contains `retirement_account`):
- `retirement_target_age` — "At what age do you plan to start drawing from this account?" (number)
- `retirement_contribution_frequency` — "How frequently do you plan to make contributions?" (select: Monthly, Quarterly, Annually, Lump sum only)
- `retirement_existing_pensions` — "Do you have existing pension or retirement accounts?" (yes_no)
- `retirement_employer_contributions` — "Will your employer be making contributions?" (yes_no)

**Source of Wealth** (show_if: `annual_income > 250000`):
- `source_of_wealth` — "Please describe the source of your wealth" (text, required)
- `source_of_wealth_documents` — "Please list the documents you can provide to verify your source of wealth" (text)

The `show_if` structure for product-based visibility:
```python
"show_if": {"field": "selected_products", "operator": "contains", "value": "cash_management_account"}
```
For the income threshold:
```python
"show_if": {"field": "annual_income", "operator": "gt", "value": 250000}
```

After adding questions to the seed, verify that `backend/app/api/routers/cases.py` evaluates `show_if` rules at runtime when serving questions to the wizard (check the questionnaire serving logic — it should already handle `eq`, `in` operators; add `contains` and `gt` if missing).

---

### 6.2 Add pulsing indicator on document row for new uploads

**Problem:** BRD FR-07 requires "a pulsing indicator on the affected document row" when a client uploads. The upload badge count in the left-rail nav is implemented, but `DocumentRow.tsx` has no per-row pulse for new uploads.

**Files to edit:** `frontend/src/components/DocumentRow.tsx`, `frontend/src/features/advisor/DocumentWorkspacePanel.tsx`, `frontend/src/store/workspaceStore.ts`, `frontend/src/hooks/useWorkspaceSocket.ts`

**What to do:**
1. In `workspaceStore.ts`, add a `newDocumentIds: Set<string>` set alongside `uploadBadgeCounts`:
   ```typescript
   newDocumentIds: new Set<string>(),
   addNewDocumentId: (id: string) => set((s) => ({ newDocumentIds: new Set([...s.newDocumentIds, id]) })),
   clearNewDocumentId: (id: string) => set((s) => { const next = new Set(s.newDocumentIds); next.delete(id); return { newDocumentIds: next } }),
   ```
2. In `useWorkspaceSocket.ts`, when a document upload event is received, call `addNewDocumentId(documentId)` in addition to `incrementBadge`.
3. In `DocumentRow.tsx`, accept an `isNew?: boolean` prop and add `animate-pulse ring-2 ring-blue-400` classes when `isNew` is true.
4. In `DocumentWorkspacePanel.tsx`, pass `isNew={newDocumentIds.has(doc.id)}` to each `DocumentRow`. Clear the indicator when the advisor opens/clicks the document row.

---

### 6.3 Add selectable tag lists for client document uploads

**Problem:** BRD FR-07 requires category-specific predefined tag lists that clients select when uploading (e.g., Passport, National ID, Utility Bill for Identity). Currently only hint text is shown.

**Files to edit:** `frontend/src/features/client/DocumentUploadCard.tsx`, `frontend/src/features/client/ClientDocumentHub.tsx`

**What to do:** Define tag options per category and render them as selectable chips:

```typescript
const CATEGORY_TAGS: Record<string, string[]> = {
  identity: ['Passport', 'National ID', 'Driving Licence', 'Birth Certificate'],
  financial: ['Bank Statement', 'Tax Return', 'W-9', 'K-1', 'Investment Statement'],
  legal: ['Trust Deed', 'Power of Attorney', 'Articles of Incorporation', 'Partnership Agreement'],
  insurance: ['Life Insurance Policy', 'Annuity Statement', 'Beneficiary Designation'],
  compliance: ['Suitability Questionnaire', 'Risk Disclosure', 'AML Declaration'],
  entity: ['Certificate of Incorporation', 'Shareholder Register', 'Corporate Resolution'],
}
```

In the upload form, render chips for the relevant category and wire the selected tag into the `tags` form field that is already sent to the upload API.

---

## Testing Checklist

After completing each phase, verify:

- [ ] Phase 1: Run `alembic upgrade head` cleanly on a fresh DB. Query `documents WHERE case_id = ?` and confirm index usage with `EXPLAIN ANALYZE`. Upload a 51 MB file and confirm it's rejected. Confirm demo mode raises on startup when `APP_ENV=production`.
- [ ] Phase 2: Verify login with a bad token returns 401. Hit `/auth/login` 11 times in a minute and confirm 429 response. Confirm JWT library works end-to-end. Check response headers include `X-Content-Type-Options`.
- [ ] Phase 3: Run `python -c "from app.main import app"` and confirm no deprecation warnings. Confirm validation background tasks complete after the HTTP response returns.
- [ ] Phase 4: Trigger a render error in `AdvisorWorkspace` and confirm the error boundary catches it. Check devtools bundle is absent in production build (`npm run build && grep -r "ReactQueryDevtools" dist/`).
- [ ] Phase 5: `docker compose up` starts all services cleanly. `alembic upgrade head` runs inside the container.
- [ ] Phase 6: Create a case with `retirement_account` product selected and confirm Retirement Account Details questions appear. Create a case with `annual_income = 300000` and confirm `source_of_wealth` question appears.

---

*Generated from production readiness audit — May 2026*
