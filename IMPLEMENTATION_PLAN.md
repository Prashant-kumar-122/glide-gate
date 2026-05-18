# GlideGate CADF — Implementation Plan

## Context

GlideGate is a wealth management client onboarding platform built as a hackathon submission. The BRD defines a multi-agent AI system (Client Agentic Development Framework — CADF) that reduces onboarding from 14–21 days to 2–3 days using 8 coordinated AI agents, A2A communication, MCP integrations, and a full onboarding workspace UI. The workspace at `./` contains only `GlideGate_BRD.docx` — no code exists yet.

**Outcome:** A runnable full-stack demo covering all 11 hackathon success criteria with a CHANGELOG-driven, stateless execution model where every step produces concrete, auditable artifacts.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12 + FastAPI + uvicorn |
| Backend validation | Pydantic v2 |
| ORM / DB | SQLAlchemy 2.0 (async) + Alembic migrations |
| WebSocket | python-socketio + FastAPI |
| File upload | python-multipart |
| Primary AI | anthropic Python SDK (`claude-sonnet-4-6`) with prompt caching |
| Fallback AI | openai Python SDK, google-generativeai, local OpenAI-compat endpoint |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| UI state | Zustand |
| Server state | TanStack Query (React Query v5) |
| Agent Canvas | @xyflow/react (React Flow) |
| Testing (backend) | pytest + pytest-asyncio + httpx |
| Testing (frontend) | Vitest |
| Package manager | Poetry (backend), npm (frontend) |

---

## Folder Structure

```
/glide-gate/
├── CHANGELOG_IMPLEMENTATION.md
├── backend/
│   ├── pyproject.toml              # Poetry deps
│   ├── alembic.ini
│   ├── alembic/versions/           # Migration files
│   ├── app/
│   │   ├── main.py                 # FastAPI app + socketio mount
│   │   ├── config.py               # Pydantic Settings (env vars)
│   │   ├── database.py             # SQLAlchemy async engine + session
│   │   ├── models/                 # SQLAlchemy ORM models (25 tables)
│   │   ├── agents/                 # Agent implementations (.py)
│   │   │   ├── base/
│   │   │   ├── orchestrator/
│   │   │   ├── customer_service/
│   │   │   ├── kyc_compliance/
│   │   │   ├── document_intelligence/
│   │   │   ├── product_onboarding/
│   │   │   ├── collaboration/
│   │   │   ├── contact_centre/
│   │   │   ├── notification/
│   │   │   └── skills/
│   │   ├── api/routers/            # FastAPI routers (.py)
│   │   ├── mcp/                    # MCP connector stubs (.py)
│   │   ├── services/               # Business logic (.py)
│   │   └── websocket/              # socketio events (.py)
│   └── tests/unit/, tests/integration/, tests/e2e/
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── src/
│       ├── routes/
│       ├── features/
│       ├── components/
│       ├── design-system/
│       ├── store/                  # Zustand stores
│       └── hooks/                  # TanStack Query hooks
├── db/schema/                      # 001–010 PostgreSQL DDL files
├── db/seeds/                       # Seed Python scripts
├── configs/agents/                 # Per-agent JSON configs
├── prompts/                        # Agent prompt .txt + validation .json
└── docs/                           # architecture.md, demo scripts, etc.
```

---

## Execution Model

This plan is executed via the CHANGELOG-first model defined in the BRD prompt:
- `CHANGELOG_IMPLEMENTATION.md` is the single source of truth
- Each step is atomic, produces concrete artifacts, cites a BRD section
- Steps execute strictly in order; a step is DONE only when all artifacts exist
- On every run: read changelog → find first non-DONE step → execute → update changelog

---

## Phase 1 — Foundation & Architecture

### STEP-01 — Repository Scaffold & Project Structure
**BRD:** Section 9.1, Section 13.3 | **Integration:** N/A | **Depends:** —

Create the full folder skeleton, `pyproject.toml` (Poetry), frontend `package.json`, `.gitignore`, `.env.example`, and seed the initial `CHANGELOG_IMPLEMENTATION.md`.

**Key files:**
- `backend/pyproject.toml` (Poetry — all Python deps declared)
- `frontend/package.json`
- `.env.example` (all env vars documented)
- `/CHANGELOG_IMPLEMENTATION.md` (initial state)
- All empty directories as per folder structure above

---

### STEP-02 — Backend Setup (FastAPI + SQLAlchemy + python-socketio)
**BRD:** Section 9.2, Section 10.2 NFRs | **Integration:** N/A | **Depends:** STEP-01

Initialize Python backend. Install all deps via Poetry. Configure FastAPI, python-socketio mount, SQLAlchemy async engine, Pydantic Settings. Set up logger and health-check endpoint.

**Key files:**
- `backend/app/main.py` — FastAPI app + socketio ASGI mount
- `backend/app/config.py` — Pydantic `Settings` (reads from .env)
- `backend/app/database.py` — async SQLAlchemy engine, `get_db` dependency
- `backend/app/api/routers/health.py` — GET /api/health

**Python deps (pyproject.toml):** `fastapi`, `uvicorn[standard]`, `python-socketio`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic[email]`, `pydantic-settings`, `anthropic`, `openai`, `google-generativeai`, `httpx`, `python-multipart`, `pillow`, `python-jose[cryptography]`, `loguru`

---

### STEP-03 — Frontend Setup (React 18 + Vite + Tailwind + Zustand + TanStack Query)
**BRD:** Section 9.1, Section 5.1 | **Integration:** N/A | **Depends:** STEP-01

Initialize React frontend. Install all deps. Scaffold App.tsx with routing to 5 placeholder pages. Wire Zustand store root and TanStack Query client provider.

**Key files:**
- `frontend/package.json`
- `frontend/vite.config.ts`, `frontend/tailwind.config.ts`
- `frontend/src/main.tsx` — React root with `QueryClientProvider` + `BrowserRouter`
- `frontend/src/App.tsx` — route definitions
- `frontend/src/store/index.ts` — Zustand store root (empty slices)
- `frontend/src/routes/` — 5 placeholder pages

**npm deps:** `react`, `react-dom`, `react-router-dom`, `@xyflow/react`, `zustand`, `@tanstack/react-query`, `socket.io-client`, `tailwindcss`, `lucide-react`, `axios`

---

## Phase 2 — Agent Design

### STEP-04 — Orchestrator Agent + A2A Framework
**BRD:** Section 6.1, Section 6.2, FR-03 | **Integration:** N/A | **Depends:** STEP-02

Implement `BaseAgent` abstract class, `a2a_types.py` (TaskPacket, TaskResponse, AgentID enum, OnboardingState Pydantic models), `AgentEventBus` (asyncio-based), and `OrchestratorAgent` with the workflow FSM (INTAKE → KYC → PARALLEL_PRODUCTS → REVIEW → COMPLETE | ESCALATED).

**Key files:**
- `backend/app/agents/base/base_agent.py`
- `backend/app/agents/base/a2a_types.py` ← **critical lingua franca for entire system**
- `backend/app/agents/base/agent_event_bus.py` (asyncio.Queue-based, Redis-ready stub)
- `backend/app/agents/orchestrator/orchestrator_agent.py` ← **central workflow controller**
- `backend/app/agents/orchestrator/workflow_state_machine.py`
- `configs/agents/orchestrator.config.json`

**Core Pydantic models in `a2a_types.py`:**
```python
class TaskPacket(BaseModel):
    id: UUID
    from_agent: AgentID
    to_agent: AgentID
    task_type: TaskType
    case_id: UUID
    client_id: UUID
    priority: Literal["LOW", "NORMAL", "HIGH", "CRITICAL"]
    payload: dict[str, Any]
    expected_schema: str
    created_at: datetime
    ttl: int  # seconds

class TaskResponse(BaseModel):
    task_id: UUID
    from_agent: AgentID
    status: Literal["SUCCESS", "PARTIAL", "FAILED", "ESCALATED"]
    result: dict[str, Any]
    errors: list[str] | None
    duration_ms: int
```

---

### STEP-05 — Customer Service Agent
**BRD:** Section 6.1, Section 8.1 stages 1–2, FR-02, FR-12 | **Integration:** N/A | **Depends:** STEP-04

Implements conversational front door with `ConversationMemory`, `DataCollectionOrchestrator`, and `IntentClassifier`. Uses Anthropic Python SDK with streaming. Drives dynamic questionnaire sequencing.

**Key files:**
- `backend/app/agents/customer_service/customer_service_agent.py`
- `backend/app/agents/customer_service/conversation_memory.py`
- `backend/app/agents/customer_service/data_collection_orchestrator.py`
- `backend/app/agents/customer_service/intent_classifier.py`
- `configs/agents/customer_service.config.json`

---

### STEP-06 — KYC & Compliance Agent
**BRD:** Section 6.1, FR-04, FR-13, FR-14, FR-15 | **Integration:** SIMULATED | **Depends:** STEP-04, STEP-05

Implements `RiskScorer` (weighted: identity × 0.4 + AML × 0.4 + profile × 0.2), `EvidencePacketBuilder`, `CheckpointRuleEngine`. Invokes simulated Identity Verification MCP tool (built in STEP-16).

**Key files:**
- `backend/app/agents/kyc_compliance/kyc_compliance_agent.py`
- `backend/app/agents/kyc_compliance/risk_scorer.py`
- `backend/app/agents/kyc_compliance/evidence_packet_builder.py`
- `backend/app/agents/kyc_compliance/checkpoint_rule_engine.py`
- `configs/agents/kyc_compliance.config.json`

---

### STEP-07 — Document Intelligence Agent
**BRD:** Section 6.1, FR-06, FR-08, FR-09, Section 5.1.10–5.1.11 | **Integration:** SIMULATED | **Depends:** STEP-04, STEP-05

Implements simulated OCR extraction, `AICompletenessValidator` (Anthropic SDK call with editable prompts → pass/warn/fail findings), `VersionDiffDetector` (difflib-based → added/modified/removed/unchanged), and `DocumentClassifier`.

**Key files:**
- `backend/app/agents/document_intelligence/document_intelligence_agent.py`
- `backend/app/agents/document_intelligence/ocr_extractor.py`
- `backend/app/agents/document_intelligence/ai_completeness_validator.py`
- `backend/app/agents/document_intelligence/version_diff_detector.py`
- `backend/app/agents/document_intelligence/document_classifier.py`
- `configs/agents/document_intelligence.config.json`

---

### STEP-08 — Product Onboarding, Collaboration, Contact Centre & Notification Agents
**BRD:** Section 6.1, FR-05, Section 7.3–7.4, Section 8.1 stages 5–8 | **Integration:** SIMULATED | **Depends:** STEP-04–07

Four remaining agents. `ProductOnboardingAgent` is parameterised by `product_code` and runs in parallel (one per product). `CollaborationAgent`, `ContactCentreAgent` (AI call summaries), `NotificationAgent` (simulated dispatch).

**Key files:**
- `backend/app/agents/product_onboarding/product_onboarding_agent.py`, `suitability_assessor.py`
- `backend/app/agents/collaboration/collaboration_agent.py`
- `backend/app/agents/contact_centre/contact_centre_agent.py`, `status_summariser.py`
- `backend/app/agents/notification/notification_agent.py`, `notification_templates.py`
- `configs/agents/` — 4 config JSON files

---

## Phase 2.5 — Database Design & Schema (PostgreSQL)

### STEP-09 — Core Tables DDL (10 Tables)
**BRD:** Section 15.2.1 | **Integration:** N/A | **Depends:** STEP-01

PostgreSQL DDL for `clients`, `client_profiles`, `client_addresses`, `onboarding_cases`, `products`, `case_products`, `case_product_steps`, `documents` (6-state lifecycle), `kyc_checks`, `human_reviews`. All use UUID PKs, JSONB flexible columns, FK constraints, `created_at`/`updated_at`, lookup indexes.

**Document status ENUM:** `NOT_REQUESTED → REQUESTED → RECEIVED → UNDER_REVIEW → NEEDS_REVISION → APPROVED`

**Key files:**
- `db/schema/001_clients.sql`
- `db/schema/002_onboarding_cases.sql`
- `db/schema/003_documents.sql`
- `db/schema/004_kyc_human_reviews.sql`

---

### STEP-10 — Agent/Event Tables DDL (4 Tables)
**BRD:** Section 15.2.2, FR-03, FR-14 | **Integration:** N/A | **Depends:** STEP-09

DDL for `agents`, `agent_tasks`, `event_logs` (append-only, no `updated_at`), `mcp_tool_calls` (with `is_simulated BOOLEAN DEFAULT TRUE`).

**Key files:**
- `db/schema/005_agents.sql`
- `db/schema/006_agent_tasks.sql`
- `db/schema/007_event_logs.sql`
- `db/schema/008_mcp_tool_calls.sql`

---

### STEP-11 — Communication/Summary & Questionnaire Tables DDL (11 Tables)
**BRD:** Section 15.2.3–15.2.4, Section 15.3 | **Integration:** N/A | **Depends:** STEP-09, STEP-10

DDL for `notifications`, `case_summaries`, `onboarding_questionnaires`, `onboarding_questions` (with `show_if JSONB`), `onboarding_question_rules`, `onboarding_answers`, `onboarding_question_sessions` (enables paused journey resumption).

**Key files:**
- `db/schema/009_communications.sql`
- `db/schema/010_questionnaire.sql`

---

### STEP-12 — SQLAlchemy Models, Alembic Migration & Seed Data
**BRD:** Section 15.2.5, Section 15.3 | **Integration:** N/A | **Depends:** STEP-09–11

SQLAlchemy 2.0 ORM models mirroring all 25 tables (mapped dataclasses style). Alembic initial migration generated from models. Seed scripts (Python): 2 products, 8 agents, all 12 questionnaire sections with `show_if` conditional rules, client Aarav Mehta, a sample 2-product onboarding case, event logs covering the full journey.

**Conditional show_if rules:**
- Cash Account suitability: `{ "field": "selected_products", "operator": "contains", "value": "cash_account" }`
- Retirement Account questions: `{ "field": "selected_products", "operator": "contains", "value": "retirement_account" }`
- Source of wealth: `{ "field": "annual_income", "operator": "gt", "value": 250000 }`

**Key files:**
- `backend/app/models/` — one `.py` per model group (clients.py, cases.py, documents.py, agents.py, questionnaire.py, etc.)
- `backend/app/models/__init__.py` — imports all models for Alembic autodiscovery
- `backend/alembic/versions/0001_initial.py` ← **authoritative DB migration**
- `db/seeds/01_products.py`
- `db/seeds/02_agents.py`
- `db/seeds/03_questionnaire.py`
- `db/seeds/04_client_aarav_mehta.py`
- `db/seeds/05_sample_case.py`
- `db/seeds/06_sample_events.py`
- `db/seeds/seed.py` (master runner)

---

## Phase 3 — Backend & Integration

### STEP-13 — Context Store Service & Shared OnboardingState
**BRD:** FR-12, Paused Journey Resumption | **Integration:** N/A | **Depends:** STEP-04, STEP-12

In-memory + DB-backed shared state bus. `ContextStoreService` exposes async `get()`, `update()`, `lock()`, `snapshot()`, `restore()`. Uses optimistic locking (`version` field) to prevent parallel agent write conflicts. Persists to `onboarding_cases.shared_context` JSONB on every mutation.

**Key files:**
- `backend/app/services/context_store/context_store_service.py` ← **shared state bus for all agents**
- `backend/app/services/context_store/onboarding_state_schema.py` (Pydantic models)
- `backend/app/services/context_store/state_repository.py` (SQLAlchemy async queries)

---

### STEP-14 — REST API Layer (FastAPI Routers)
**BRD:** Section 9.1, FR-01, FR-05, FR-07 | **Integration:** N/A | **Depends:** STEP-02, STEP-12, STEP-13

All FastAPI routers with Pydantic request/response models and role-based dependency guards (Advisor / Client / ComplianceOfficer / CCRep / Admin).

**Key files:**
- `backend/app/api/routers/clients.py` — POST, GET, PATCH
- `backend/app/api/routers/cases.py` — initiate, get state, summary, resume
- `backend/app/api/routers/documents.py` — upload (`UploadFile`), status, validate, diff
- `backend/app/api/routers/conversations.py` — SSE streaming chat (`StreamingResponse`)
- `backend/app/api/routers/reviews.py` — pending queue, decide
- `backend/app/api/routers/agents.py` — trace data, status
- `backend/app/api/routers/audit.py` — paginated log + CSV `StreamingResponse`
- `backend/app/api/routers/admin/llm_config.py`, `validation_prompts.py`
- `backend/app/api/dependencies/auth.py` — JWT verify dependency
- `backend/app/api/dependencies/role_guard.py`
- `backend/app/api/error_handlers.py`

---

### STEP-15 — WebSocket Layer (python-socketio)
**BRD:** FR-11, Section 5.1.9, FR-13 | **Integration:** N/A | **Depends:** STEP-02, STEP-04, STEP-13

python-socketio server mounted on FastAPI ASGI app. Rooms per `case_id`. Typed event constants. Singleton `SocketEmitter` used by agents and services.

**Typed events:** `AGENT_MESSAGE`, `TASK_ASSIGNED`, `TASK_COMPLETE`, `DOCUMENT_STATUS_CHANGED`, `DOCUMENT_UPLOADED`, `KYC_RESULT`, `ESCALATION_TRIGGERED`, `REVIEW_DECIDED`, `PRODUCT_TRACK_UPDATE`, `NOTIFICATION_SENT`, `CASE_STAGE_CHANGED`, `PROGRESS_UPDATE`

**Key files:**
- `backend/app/websocket/socket_server.py` — socketio AsyncServer, room management
- `backend/app/websocket/socket_events.py` — event name constants
- `backend/app/websocket/socket_emitter.py` — singleton helper for agents/services

---

### STEP-16 — MCP Connectors (Simulated)
**BRD:** Section 5.3, Section 6.3, FR-04, FR-06, Section 13.1, Hackathon Criterion #2 | **Integration:** SIMULATED | **Depends:** STEP-10, STEP-12, STEP-13

`MCPRegistry` for tool discovery/invocation. Two simulated connectors: Identity Verification (tools: `verify_identity`, `check_sanctions`, `score_aml_risk`) and Document Management (tools: `upload_document`, `retrieve_document`, `get_document_status`, `extract_ocr`). Realistic Pydantic response schemas with 100–800ms randomised latency (`asyncio.sleep`). All invocations logged to `mcp_tool_calls` with `is_simulated = True`.

**Key files:**
- `backend/app/mcp/mcp_connector.py` — abstract base + registry
- `backend/app/mcp/mcp_logger.py`
- `backend/app/mcp/connectors/identity_verification/connector.py` + `simulator.py`
- `backend/app/mcp/connectors/document_management/connector.py` + `simulator.py`

---

### STEP-17 — Agent Orchestration Service (Wire All 8 Agents)
**BRD:** Section 8.1, FR-03, FR-12 | **Integration:** N/A | **Depends:** STEP-04–08, STEP-13, STEP-15, STEP-16

Singleton `AgentOrchestrationService` that initialises all agents, wires event bus, exposes `start_onboarding(case_id, client_id, selected_products)` and `resume_onboarding(case_id)` as async methods. `ParallelProductLauncher` uses `asyncio.gather` to spawn independent `ProductOnboardingAgent` tasks per product.

**Key files:**
- `backend/app/services/orchestration/agent_orchestration_service.py`
- `backend/app/services/orchestration/parallel_product_launcher.py`
- `backend/app/services/orchestration/agent_registry.py`

---

### STEP-18 — Document Upload & Storage Service
**BRD:** FR-06, FR-07, FR-09, Section 5.1.7–5.1.8 | **Integration:** SIMULATED (local disk) | **Depends:** STEP-09, STEP-13, STEP-15, STEP-16

FastAPI `UploadFile` + Pillow image pre-processing. Triggers Document Intelligence Agent OCR/classification immediately (via `asyncio.create_task`). Handles version tracking (`parent_doc_id`, incremented `version`). Emits `DOCUMENT_UPLOADED` with badge-count payload.

**Key files:**
- `backend/app/services/document/document_upload_service.py`
- `backend/app/services/document/document_storage_adapter.py` (local disk, S3-compat stub)
- `backend/app/services/document/document_version_manager.py`
- `backend/app/services/document/document_status_service.py`

---

## Phase 3.5 — Auth (Backend)

### STEP-18A — Auth System (Backend)
**BRD:** Section 9.1, FR-01, Section 10.2 (role-based access control) | **Integration:** N/A | **Depends:** STEP-12, STEP-14

Implement a full authentication system: `users` table (separate from `clients`), bcrypt password hashing via `passlib`, JWT token issuance via `python-jose`, signup/login/profile REST endpoints, and user seed data. Upgrades the existing demo-mode `auth.py` stub to real JWT validation with lowercase role normalisation.

**Users table columns:** `id` (UUID PK), `email` (unique), `first_name`, `last_name`, `password_hash`, `role` (`client` | `advisor` | `admin`, default `client`), `is_active`, `created_at`, `updated_at`

**Pydantic schemas:**
```python
class SignupRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str          # min 8 chars, at least 1 digit
    confirm_password: str  # must equal password

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ProfileUpdateRequest(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = None
    confirm_password: str | None = None  # required when password is set

class UserOut(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
```

**REST endpoints (`/auth` prefix):**

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/signup` | No | Create account (role=client), return JWT |
| `POST` | `/auth/login` | No | Validate credentials, return JWT |
| `GET` | `/auth/me` | Yes | Fetch current user profile |
| `PATCH` | `/auth/me` | Yes | Update email / name / password |

**JWT claims:** `sub` (user UUID), `email`, `role` (lowercase), `name` (full name), `exp`

**Auth dependency update:** `get_current_user` in `auth.py` already decodes JWT; update `DEMO_USER["role"]` from `"Advisor"` → `"advisor"` to match lowercase convention used throughout.

**Seed users (`db/seeds/07_users.py`):**

| Name | Email | Password | Role |
|---|---|---|---|
| Admin User | admin@glide-gate.local | Admin123! | admin |
| Demo Advisor | advisor@glide-gate.local | Advisor123! | advisor |
| Aarav Mehta | aarav.mehta@demo.glide-gate.local | Client123! | client |

**Key files:**
- `db/schema/011_users.sql` — DDL (UUID PK, unique email, role CHECK constraint)
- `backend/alembic/versions/0002_users.py` — migration (follows `0001_initial`; `down_revision = "0001_initial"`)
- `backend/app/models/users.py` — `User` SQLAlchemy ORM model
- `backend/app/models/__init__.py` — add `User` import
- `backend/app/services/auth/auth_service.py` — `hash_password`, `verify_password`, `create_access_token`, `signup`, `login`, `get_profile`, `update_profile`; module-level `auth_service` singleton
- `backend/app/services/auth/__init__.py` — re-exports `auth_service`
- `backend/app/api/routers/auth.py` — 4 endpoints + Pydantic schemas
- `backend/app/api/dependencies/auth.py` — update `DEMO_USER["role"]` → `"advisor"` (lowercase)
- `backend/app/main.py` — register `auth.router` with `_prefix`
- `db/seeds/07_users.py` — 3 seed users with bcrypt-hashed passwords
- `db/seeds/seed.py` — add `07_users.py` to `SEED_FILES` list
- `backend/pyproject.toml` — `passlib[bcrypt]` already present; no change needed

---

## Phase 4 — Frontend / UI

### STEP-19 — Design System & Shared UI Components
**BRD:** Section 5.1.15, Section 5.1.3, Section 5.1.16 | **Integration:** N/A | **Depends:** STEP-03

Colour tokens for 6 document statuses and 4 team roles. Component library with Zustand-connected components where appropriate.

**Key files:**
- `frontend/src/design-system/tokens.ts`
- `frontend/src/components/StatusBadge.tsx`
- `frontend/src/components/RoleBadge.tsx`
- `frontend/src/components/ProgressBar.tsx`
- `frontend/src/components/DocumentRow.tsx`
- `frontend/src/components/CategoryCard.tsx`
- `frontend/src/components/CommentThread.tsx`
- `frontend/src/components/VisibilityToggle.tsx`
- `frontend/src/components/ConfirmationModal.tsx`
- `frontend/src/components/UploadButton.tsx`

---

### STEP-20 — Advisor Workspace View (All 16 Features)
**BRD:** Section 5.1 (all 16 features), Section 5.2.1, FR-07–10 | **Integration:** N/A | **Depends:** STEP-14, STEP-15, STEP-19

Left-rail multi-client nav with per-client progress bars and upload badge counts (Zustand `workspaceStore`). Main panel: 6 CategoryCards. Right drawer: document viewer, comment thread, status editor, AI validation panel (pass/warn/fail), version diff panel. All server data via TanStack Query; real-time updates via socket.io.

**State split:**
- **Zustand `workspaceStore`**: selected client, drawer open/closed state, active document, upload badge counts, socket connection status
- **TanStack Query**: `useDocuments(caseId)`, `useValidationResult(docId)`, `useDiffResult(docId)`, `useCaseProgress(caseId)`

**Key files:**
- `frontend/src/routes/AdvisorWorkspace.tsx`
- `frontend/src/store/workspaceStore.ts` (Zustand)
- `frontend/src/features/advisor/ClientRailNav.tsx`
- `frontend/src/features/advisor/DocumentWorkspacePanel.tsx`
- `frontend/src/features/advisor/DocumentDetailDrawer.tsx`
- `frontend/src/features/advisor/AIValidationPanel.tsx`
- `frontend/src/features/advisor/VersionDiffPanel.tsx`
- `frontend/src/features/advisor/StatusEditor.tsx`
- `frontend/src/features/advisor/ParallelProductTracks.tsx`
- `frontend/src/hooks/useDocuments.ts` (TanStack Query)
- `frontend/src/hooks/useWorkspaceSocket.ts`

---

### STEP-21 — Client Portal View
**BRD:** Section 5.1.6–5.1.7, Section 5.2.2, FR-02 | **Integration:** N/A | **Depends:** STEP-14, STEP-15, STEP-19

Streaming conversational chat interface (SSE), document category view with per-document chat threads, upload with predefined tags, client-side progress bar.

**State split:**
- **Zustand `chatStore`**: messages[], typingIndicator, sessionId
- **TanStack Query**: `useClientDocuments(caseId)`, `useClientProgress(caseId)`

**Key files:**
- `frontend/src/routes/ClientPortal.tsx`
- `frontend/src/store/chatStore.ts` (Zustand)
- `frontend/src/features/client/ConversationalChat.tsx`
- `frontend/src/features/client/ClientDocumentHub.tsx`
- `frontend/src/features/client/DocumentUploadCard.tsx`
- `frontend/src/features/client/ClientProgressBar.tsx`
- `frontend/src/hooks/useClientChat.ts` (TanStack Query mutation + SSE)
- `frontend/src/hooks/useClientDocuments.ts`

---

### STEP-22 — Contact Centre Dashboard
**BRD:** Section 7.3, FR-05, Hackathon Criterion #6 | **Integration:** N/A | **Depends:** STEP-14, STEP-15, STEP-19

Searchable client table with real-time status. Per-client panel: stage, product track progress bars, AI call summary, recommended next actions, action buttons.

**State split:**
- **Zustand `ccStore`**: selectedClientId, filterText, socketStatus
- **TanStack Query**: `useAllCases()`, `useClientDetail(caseId)`, `useCallSummary(caseId)`

**Key files:**
- `frontend/src/routes/ContactCentre.tsx`
- `frontend/src/store/ccStore.ts` (Zustand)
- `frontend/src/features/contact-centre/ClientStatusTable.tsx`
- `frontend/src/features/contact-centre/ClientDetailPanel.tsx`
- `frontend/src/features/contact-centre/CallSummaryCard.tsx`
- `frontend/src/features/contact-centre/CCActionBar.tsx`
- `frontend/src/features/contact-centre/ProductTrackSummary.tsx`
- `frontend/src/hooks/useAllCases.ts`, `useCallSummary.ts`

---

### STEP-23 — Agent Trace Canvas & Admin Config View
**BRD:** FR-11, Section 5.1.12–5.1.14, Hackathon Criterion #10 | **Integration:** N/A | **Depends:** STEP-14, STEP-15, STEP-19

React Flow canvas with 8 agent nodes. Animated edges for in-flight A2A messages. Node colour encodes state. Admin Config: LLM provider selector, deterministic controls (temperature, top-p, seed, freq penalty, presence penalty, retry, cache TTL), per-category/document editable validation prompts.

**State split:**
- **Zustand `traceStore`**: nodeStates{}, edgeQueue[], messageLog[], selectedAgent
- **TanStack Query**: `useAgentTrace(caseId)`, `useLLMConfig()`, `useValidationPrompts()`

**Key files:**
- `frontend/src/routes/AgentTrace.tsx`, `frontend/src/routes/AdminConfig.tsx`
- `frontend/src/store/traceStore.ts` (Zustand)
- `frontend/src/features/agent-trace/AgentTraceCanvas.tsx`
- `frontend/src/features/agent-trace/AgentNode.tsx`
- `frontend/src/features/agent-trace/MessageLog.tsx`
- `frontend/src/features/agent-trace/AgentDetailPopover.tsx`
- `frontend/src/features/admin/LLMProviderConfig.tsx`
- `frontend/src/features/admin/DeterministicControls.tsx`
- `frontend/src/features/admin/ValidationPromptEditor.tsx`
- `frontend/src/features/admin/CheckpointRulesEditor.tsx`
- `frontend/src/hooks/useLLMConfig.ts`, `useValidationPrompts.ts`, `useAgentTrace.ts`

---

## Phase 4.5 — Auth (Frontend)

### STEP-23A — Auth UI (Frontend)
**BRD:** Section 5.1, Section 5.2 (role-based views), FR-01 | **Integration:** N/A | **Depends:** STEP-18A, STEP-19, STEP-03

Implement the full frontend authentication layer: Login and Signup pages, profile view/edit, navbar user menu with dropdown, Zustand `authStore` (persisted to `localStorage`), role-based route guards, and filtered nav link visibility.

**Role → default route mapping:**

| Role | Default Route | Visible Nav Links |
|---|---|---|
| `client` | `/client` | *(none — Client Portal has its own layout)* |
| `advisor` | `/` | Advisor Workspace, Contact Centre, Agent Trace |
| `admin` | `/admin` | Admin Config, Agent Trace |

**Route protection matrix:**

| Path | Component | Allowed Roles |
|---|---|---|
| `/login` | `Login` | Public (redirects if already authenticated) |
| `/signup` | `Signup` | Public (redirects if already authenticated) |
| `/profile` | `Profile` | `client`, `advisor`, `admin` |
| `/` | `AdvisorWorkspace` | `advisor` |
| `/client` | `ClientPortal` | `client` |
| `/contact-centre` | `ContactCentre` | `advisor` |
| `/agent-trace` | `AgentTrace` | `advisor`, `admin` |
| `/admin` | `AdminConfig` | `admin` |

**`authStore` shape (Zustand + `persist` middleware → `localStorage` key `gg_auth`):**
```typescript
interface AuthUser {
  id: string
  email: string
  firstName: string
  lastName: string
  role: 'client' | 'advisor' | 'admin'
}
interface AuthState {
  token: string | null
  user: AuthUser | null
  isAuthenticated: boolean   // derived: token !== null
  setAuth: (token: string, user: AuthUser) => void
  clearAuth: () => void      // clears store + localStorage
}
```

**Axios interceptors in `api.ts`:**
- Request: attach `Authorization: Bearer <token>` from `authStore`
- Response: on 401 → `clearAuth()` + redirect to `/login`

**`ProtectedRoute` component:** checks `isAuthenticated`; if false → redirect to `/login`; if role not in `allowedRoles` → redirect to role's default route.

**Profile editing:** only `client` role gets editable fields; `advisor` and `admin` see read-only view. `ConfirmationModal` shown before saving password changes.

**Key files:**
- `frontend/src/store/authStore.ts` — Zustand store with `persist`
- `frontend/src/store/index.ts` — add `useAuthStore` re-export
- `frontend/src/lib/api.ts` — add `UserOut`, `TokenResponse` interfaces; add request/response interceptors
- `frontend/src/hooks/useAuth.ts` — `useSignup()`, `useLogin()`, `useProfile()`, `useUpdateProfile()` (TanStack Query)
- `frontend/src/components/ProtectedRoute.tsx` — role-guard wrapper
- `frontend/src/features/auth/LoginForm.tsx` — email + password fields, `useLogin` mutation
- `frontend/src/features/auth/SignupForm.tsx` — first/last name + email + password + confirm, `useSignup` mutation
- `frontend/src/features/auth/ProfileCard.tsx` — read-only view + edit mode (client only), `useUpdateProfile` mutation
- `frontend/src/features/auth/UserMenu.tsx` — right-side NavBar dropdown (full name → View Profile / Sign Out)
- `frontend/src/routes/Login.tsx` — branding + `LoginForm` + link to Signup
- `frontend/src/routes/Signup.tsx` — `SignupForm` + link to Login
- `frontend/src/routes/Profile.tsx` — `ProfileCard` page at `/profile`
- `frontend/src/App.tsx` — replace open routes with `ProtectedRoute`-wrapped routes; filter nav links by role; add `<UserMenu />` to NavBar right side

---

### STEP-23B — Phase 4 API Contract & Type-Shape Remediation
**Date:** 2026-05-15 | **BRD:** Section 9.1, FR-07, FR-08, FR-09, FR-11 | **Depends:** STEP-14, STEP-18, STEP-20–23A

Resolved all frontend↔backend type mismatches identified in the Phase 4 comprehensive audit. Fixed one hard crash (`TypeError` in `AgentDetailPopover`), four 4xx API failures (`PATCH /documents/{id}`, `POST /message` 422, `POST /message` 401, `GET /call-summary` 404), and six silent data failures (blank document names, 0% progress, empty product tracks, undefined diff fields, blank agent status). Backend: `documents.py` (PATCH route + computed fields), `cases.py` (CaseProgressOut full shape + ProductTrackOut enrichment), `agents.py` (AgentTraceOut agents array + AgentOut status), `conversations.py` (call-summary stub). Frontend: `useClientChat.ts` (body field, auth header, SSE parser).

---

## Phase 5 — AI / LLM Capabilities

### STEP-24 — LLM Provider Abstraction Layer
**BRD:** Section 5.1.12, FR-08 | **Integration:** REAL (Anthropic primary) | **Depends:** STEP-02, STEP-05–08

Abstract `LLMProvider` base class with concrete implementations for Anthropic (prompt caching, `claude-sonnet-4-6`), OpenAI, Google Gemini, and local models (OpenAI-compat via `httpx`). `LLMFallbackChain` for automatic provider failover. `DeterministicControlsApplier` applies all 5 control parameters.

**Key files:**
- `backend/app/services/llm/llm_provider.py` ← **LLM interface for all agents**
- `backend/app/services/llm/providers/anthropic_provider.py` (prompt caching headers)
- `backend/app/services/llm/providers/openai_provider.py`
- `backend/app/services/llm/providers/google_provider.py`
- `backend/app/services/llm/providers/local_model_provider.py` (httpx OpenAI-compat)
- `backend/app/services/llm/llm_provider_factory.py`
- `backend/app/services/llm/llm_fallback_chain.py`
- `backend/app/services/llm/deterministic_controls_applier.py`

---

### STEP-25 — Agent Prompt Library
**BRD:** Section 6.4, Section 6.1, FR-08 | **Integration:** N/A | **Depends:** STEP-24, STEP-05–08

Versioned prompt files for each agent (system + task-specific). Default validation prompts for all 6 document categories as JSON with `goal` and `factors[]`.

**Key files:**
- `prompts/orchestrator/system.txt`
- `prompts/customer_service/system.txt`, `data_collection.txt`
- `prompts/kyc_compliance/system.txt`, `risk_assessment.txt`
- `prompts/document_intelligence/system.txt`, `completeness_validation.txt`
- `prompts/product_onboarding/cash_account.txt`, `retirement_account.txt`
- `prompts/contact_centre/call_summary.txt`
- `prompts/validation_defaults/identity.json`, `financial.json`, `legal.json`, `insurance.json`, `compliance.json`, `entity.json`

---

### STEP-26 — Skills Framework (6 Shared Skills)
**BRD:** Section 6.4, Hackathon Criterion #7 (min 3 skills) | **Integration:** N/A | **Depends:** STEP-24, STEP-25, STEP-04–08

6 composable async skill classes registered on agent instances. Every invocation logged to `event_logs` with skill name and invoking agent.

**Key files:**
- `backend/app/agents/skills/base_skill.py`
- `backend/app/agents/skills/information_extraction_skill.py`
- `backend/app/agents/skills/decision_reasoning_skill.py`
- `backend/app/agents/skills/status_summarisation_skill.py`
- `backend/app/agents/skills/clarification_skill.py`
- `backend/app/agents/skills/escalation_skill.py`
- `backend/app/agents/skills/product_suitability_skill.py`

---

### STEP-27 — Streaming Conversational Interface (SSE Backend)
**BRD:** FR-02, Section 9.1, NFR < 3s | **Integration:** REAL (Anthropic streaming) | **Depends:** STEP-14, STEP-24, STEP-05, STEP-13

FastAPI `StreamingResponse` for `/cases/{case_id}/message`. `ConversationCoordinator` updates memory, calls CSA, checks data collection completion, triggers orchestrator stage advance via asyncio.

**Key files:**
- `backend/app/api/routers/conversations.py` (updated for `StreamingResponse`)
- `backend/app/services/conversation/streaming_response_service.py`
- `backend/app/services/conversation/conversation_coordinator.py`
- `backend/app/services/conversation/session_manager.py`

---

### STEP-28 — AI Validation & Version Diff (End-to-End Wire)
**BRD:** FR-08, FR-09, Section 5.1.10–5.1.11, Hackathon Criteria #8, #9 | **Integration:** REAL (LLM) | **Depends:** STEP-07, STEP-14, STEP-15, STEP-24, STEP-25, STEP-18

Wire full validation flow: API trigger → load editable prompt from DB → apply deterministic controls → Anthropic call → parse `FindingResult[]` → persist to `documents.validation_result` → emit socket event → frontend display. Wire diff: resubmission → `VersionDiffDetector` (Python `difflib`) → persist to `documents.diff_result` → render in `VersionDiffPanel`.

**Key files:**
- `backend/app/services/validation/validation_orchestrator.py`
- `backend/app/services/validation/validation_prompt_repository.py`

---

## Phase 6 — Compliance & Audit

### STEP-29 — Human-in-the-Loop Review Workflow
**BRD:** FR-13, Hackathon Criteria #5, #11 | **Integration:** N/A | **Depends:** STEP-06, STEP-09, STEP-13, STEP-14, STEP-15, STEP-26

When KYC scores above threshold: write `human_reviews` record → pause workflow FSM → emit `ESCALATION_TRIGGERED` → persist evidence packet. `POST /reviews/{review_id}/decide` (Approve / Reject / Request More Info) resumes or terminates workflow.

**Key files:**
- `backend/app/services/compliance/human_review_service.py`
- `backend/app/services/compliance/evidence_packet_assembler.py`
- `frontend/src/features/compliance-review/EscalationQueue.tsx`
- `frontend/src/features/compliance-review/EvidencePacketPanel.tsx`
- `frontend/src/features/compliance-review/ReviewActionBar.tsx`
- `frontend/src/hooks/usePendingReviews.ts` (TanStack Query)

---

### STEP-30 — Configurable Checkpoint Rules (FR-15)
**BRD:** FR-15, Section 10.2 | **Integration:** N/A | **Depends:** STEP-06, STEP-12, STEP-14, STEP-29

`CheckpointRuleRepository` for DB-persisted rules. Admin UI `CheckpointRulesEditor` with TanStack Query mutations for add/edit/delete across 4 dimensions: `product_type`, `risk_level`, `account_value_band`, `jurisdiction`.

**Key files:**
- `backend/app/services/compliance/checkpoint_rule_repository.py`
- `frontend/src/features/admin/CheckpointRulesEditor.tsx` (already listed in STEP-23)

---

### STEP-31 — Append-Only Audit Event Log
**BRD:** FR-14, Section 10.2 (100% of decisions logged) | **Integration:** N/A | **Depends:** STEP-10, STEP-12, STEP-14

`AuditLogService` wraps all writes to `event_logs` (no update/delete enforced at service layer). Wired into every agent decision, human review, status change, and MCP call. Query endpoint with filters; CSV `StreamingResponse`.

**Key files:**
- `backend/app/services/audit/audit_log_service.py`
- `backend/app/services/audit/audit_event_types.py` (full StrEnum)
- `backend/app/api/routers/audit.py`

---

### STEP-32 — Compliance Decision Logging & Evidence Packet Persistence
**BRD:** FR-14, Section 10.2, Hackathon Criterion #11 | **Integration:** N/A | **Depends:** STEP-29, STEP-31

`ComplianceDecisionLogger` writes `COMPLIANCE_DECISION` audit events for both automated (KYC agent) and human reviewer decisions. Evidence packet stored in `human_reviews.evidence_packet`. `GET /reviews/{review_id}/evidence` retrieval endpoint.

**Key files:**
- `backend/app/services/compliance/compliance_decision_logger.py`
- `backend/app/api/routers/reviews.py` (updated)

---

### STEP-33 — Paused Journey Resumption
**BRD:** FR-12, Paused Journey Resumption Appendix | **Integration:** N/A | **Depends:** STEP-13, STEP-17, STEP-31

`JourneyResumptionService.resume_case(case_id)`: loads persisted `shared_context`, restores to `ContextStoreService`, determines current FSM stage, re-spawns appropriate agents via `asyncio.create_task`, logs `JOURNEY_RESUMED` audit event. Each `ProductOnboardingAgent` resumes from `case_product_steps` record.

**Key files:**
- `backend/app/services/orchestration/journey_resumption_service.py`

---

### STEP-33A — Conversational Interface Enhancements & Dynamic Progress Bar
**BRD:** Section 5.2.2, FR-02 | **Integration:** N/A | **Depends:** STEP-21, STEP-27

Post-STEP-27 enhancements to the full conversational onboarding stack. `DataCollectionOrchestrator` upgraded from hardcoded fields to DB-backed question loading (`load_questions_from_db`) with hardcoded fallback; supports `validation_rules` per field and per-case `question_id` maps for DB upserts. `ConversationCoordinator` gains `handle_greeting()` (fresh-session SSE greeting), DB answer persistence (`onboarding_answers` upsert + `onboarding_question_sessions` tracker), `{type:"options"}` SSE events for choice fields rendered as clickable chips, and `{type:"progress","questionnaire_pct":<0–100>}` SSE events after every reply. `StreamingResponseService.stream_reply()` gains a `fallback_text` parameter for word-by-word LLM-unavailable fallback. Questionnaire expanded from 30 → 45 questions across 11 sections. Frontend: `OptionChips` component in `ConversationalChat`; `useGreeting` hook; `pendingOptions` + `questionnairePct` state in `chatStore`; `ClientProgressBar` replaced static stage lookup with three-phase dynamic progress (INTAKE 0–60% per question answered, KYC 70%, PARALLEL_PRODUCTS 70–100% per approved document).

**Key files:**
- `backend/app/agents/customer_service/data_collection_orchestrator.py`
- `backend/app/api/routers/conversations.py` (`GET /{case_id}/greet`)
- `backend/app/services/conversation/conversation_coordinator.py`
- `backend/app/services/conversation/session_manager.py`
- `backend/app/services/conversation/streaming_response_service.py`
- `db/seeds/03_questionnaire.py` (45 questions, 11 sections)
- `frontend/src/features/client/ConversationalChat.tsx`
- `frontend/src/features/client/ClientProgressBar.tsx`
- `frontend/src/hooks/useClientChat.ts`
- `frontend/src/routes/ClientPortal.tsx`
- `frontend/src/store/chatStore.ts`

---

## Phase 7 — Demo & Visualization

### STEP-34 — Demo Scenarios, Fixtures & DemoModeService
**BRD:** Section 13.1, Section 11.2 (all 11 criteria) | **Integration:** N/A | **Depends:** STEP-12, STEP-17, STEP-29

Two demo paths tied to all 11 hackathon criteria. `DemoModeService` returns pre-canned LLM responses for reliable demo execution (BRD Risk #5 mitigation). Demo fixtures: KYC high-risk scenario, pre-scripted conversation turns, pre-canned validation findings.

**Key files:**
- `docs/demo_scenario_a.md` — Happy path: Aarav Mehta, 2 products, no escalation
- `docs/demo_scenario_b.md` — Escalation path: HIGH_RISK KYC → human review → resume
- `backend/app/services/demo/demo_mode_service.py`
- `backend/app/services/demo/fixtures/kyc_high_risk.json`
- `backend/app/services/demo/fixtures/conversation_turns.json`
- `backend/app/services/demo/fixtures/validation_findings.json`

---

### STEP-35 — Agent Trace Canvas: Live Animation & Real-Time Log
**BRD:** FR-11, Hackathon Criterion #10 | **Integration:** N/A | **Depends:** STEP-15, STEP-23, STEP-17

Complete React Flow canvas with live animations driven by socket.io events. `AGENT_MESSAGE` events animate edges (2s visible → fade). Node colour state machine: IDLE (grey) → ACTIVE (blue) → ESCALATED (amber) → COMPLETE (green). All state in Zustand `traceStore`.

**Key files:**
- `frontend/src/features/agent-trace/AgentTraceCanvas.tsx` (completed)
- `frontend/src/features/agent-trace/useAgentTraceSocket.ts` (updates Zustand traceStore)
- `frontend/src/features/agent-trace/agentPositions.ts`

---

### STEP-36 — Parallel Product Track Visualization
**BRD:** FR-01, Section 7.1, Hackathon Criterion #3 | **Integration:** N/A | **Depends:** STEP-20, STEP-22, STEP-35

Two-column independent progress bars per product track in Advisor Workspace and Contact Centre views. Real-time updates via `PRODUCT_TRACK_UPDATE` socket events updating Zustand `workspaceStore`. Both `ProductOnboardingAgent` instances visible as separate nodes on the Agent Trace canvas.

**Key files:**
- `frontend/src/features/advisor/ParallelProductTracks.tsx` (already listed in STEP-20)
- `frontend/src/features/contact-centre/ProductTrackSummary.tsx` (already listed in STEP-22)

---

### STEP-36A — Agent Event Bus: Persist Agent Tasks to DB (Fix Agent Trace Canvas)
**BRD:** FR-11, Hackathon Criterion #10 | **Integration:** N/A | **Depends:** STEP-35, STEP-36

**Root cause:** `AgentEventBus.dispatch_loop()` processed `TaskPacket` objects entirely in-memory. The `agent_tasks` table (created in `0001_initial`) was never written to, so `GET /api/agents/trace/{case_id}` returned zero tasks and the Agent Trace Canvas showed no agent activity.

**In-memory audit (full inventory):**

| Component | File | What lives in memory | Needs DB fix? |
|---|---|---|---|
| **AgentTask records** | `agents/base/agent_event_bus.py` | Task dispatch/completion never persisted | **YES — P0, this step** |
| `ConversationMemory._store` | `agents/customer_service/conversation_memory.py` | Rolling 40-msg buffer | No — backed by `conversation_messages` table |
| `SessionManager._sessions` | `services/conversation/session_manager.py` | Active session objects | No — reconstructable from DB |
| `ContextStoreService._cache` | `services/context_store/context_store_service.py` | `OnboardingState` per case | No — backed by `onboarding_cases.shared_context` JSONB |
| `DataCollectionOrchestrator._collected` | `agents/customer_service/data_collection_orchestrator.py` | In-flight answers | No — persisted to `onboarding_answers` |
| `AgentEventBus._queues/_agents` | `agents/base/agent_event_bus.py` | In-flight `TaskPacket` objects | No — ephemeral by design |
| `prompt_override_store._prompt_overrides` | `services/validation/prompt_override_store.py` | Admin LLM prompt overrides | P2 — separate concern, not fixed here |

**Fix (single file):** `backend/app/agents/base/agent_event_bus.py`
- Add `_save_task_in_progress(packet, started_at)`: inserts `AgentTask` row with `status="IN_PROGRESS"` on task dequeue.
- Add `_update_task_completed(task_id, response)`: updates row with final `status`, `result`, `errors`, `duration_ms`, `completed_at`.
- Update `dispatch_loop()`: call both helpers; synthesise a `TaskResponse(status="FAILED")` on unhandled exceptions rather than silently discarding.
- Both helpers swallow DB exceptions with `logger.warning` so a DB error never crashes the dispatch loop.

**Key files:**
- `backend/app/agents/base/agent_event_bus.py` — only file changed; no migrations needed

---

## Phase 8 — Testing & Refinement

### STEP-37 — Unit Tests (Agents, Services, Skills)
**BRD:** Section 10.2 NFRs, Section 9.2 | **Integration:** N/A (mocked) | **Depends:** STEP-04–08, STEP-13, STEP-16

pytest + pytest-asyncio unit tests for: OrchestratorAgent FSM transitions, `RiskScorer` score bands, `CheckpointRuleEngine` all 4 dimensions, questionnaire `show_if` rule evaluation for all 3 conditional rules, MCP simulator Pydantic response schemas.

**Key files:**
- `backend/tests/unit/agents/test_orchestrator.py`
- `backend/tests/unit/agents/test_kyc_compliance.py`
- `backend/tests/unit/agents/test_document_intelligence.py`
- `backend/tests/unit/services/test_context_store.py`
- `backend/tests/unit/services/test_questionnaire.py`
- `backend/tests/unit/mcp/test_connectors.py`
- `backend/pyproject.toml` (pytest config section)

---

### STEP-38 — Integration Tests (API + Database)
**BRD:** Section 10.2 NFRs, audit trail completeness | **Integration:** N/A (test DB) | **Depends:** STEP-14, STEP-17, STEP-29, STEP-31, STEP-33, STEP-37

pytest integration tests using `httpx.AsyncClient` against a real PostgreSQL test schema: case initiation API flow, document upload → OCR → status → audit chain (100% coverage), human review escalation → decide → resume, questionnaire session save/restore.

**Key files:**
- `backend/tests/integration/api/test_case_initiation.py`
- `backend/tests/integration/api/test_document_lifecycle.py`
- `backend/tests/integration/api/test_human_review.py`
- `backend/tests/integration/db/test_audit_completeness.py`
- `backend/tests/integration/db/test_questionnaire_session.py`
- `backend/tests/conftest.py` — async DB setup, `httpx.AsyncClient` fixture

---

### STEP-39 — End-to-End Demo Rehearsal & NFR Validation
**BRD:** Section 10.2 NFRs, Section 12 Risk #5 | **Integration:** Demo mode + Anthropic streaming | **Depends:** STEP-34, STEP-37, STEP-38

Run both demo scenarios end-to-end. Timing harness measures all 4 NFR targets. Fix anything exceeding targets. Record fallback demo video. Validate all 11 hackathon success criteria.

**NFR targets:** conversation turn < 3s, agent task < 30s, document status update < 2s, AI validation < 15s

**Key files:**
- `backend/tests/e2e/test_scenario_a.py` — happy path, 11 DB checkpoints
- `backend/tests/e2e/test_scenario_b.py` — escalation path, evidence packet assertions
- `docs/nfr_baseline.md` — measured latencies

---

### STEP-40 — Final Polish, CHANGELOG Completion & Submission Readiness
**BRD:** Section 11.2 (all 11 criteria), Section 2 | **Integration:** N/A | **Depends:** All prior steps

Complete `CHANGELOG_IMPLEMENTATION.md` for all 40 steps. Final Mermaid diagrams in `architecture-overview.md`. Root `README.md` with quick-start (`poetry install`, `alembic upgrade head`, `python db/seeds/seed.py`, `uvicorn`, `npm run dev`), env var reference, demo links. Verify all 16 workspace features, agent trace canvas, evidence packet, and parallel tracks are functional.

**Key files:**
- `README.md`
- `CHANGELOG_IMPLEMENTATION.md` (fully completed)
- `docs/architecture_overview.md` (4 Mermaid diagrams)
- `docs/hackathon_success_criteria.md` (checklist with "how demonstrated" column)
- `.env.example` (updated with all 40-step env vars)

---

## Integration Mode Summary

| Integration | Mode |
|---|---|
| Identity Verification Service | SIMULATED (MCP) |
| Document Management System | SIMULATED (MCP) |
| Email / SMS dispatch | SIMULATED |
| Account creation (Product system) | SIMULATED |
| Core Banking / Custody | OUT OF SCOPE |
| Live CRM | OUT OF SCOPE |
| Anthropic API | REAL |
| OpenAI API | REAL (fallback) |
| Google Gemini API | REAL (optional) |
| Local Models (Llama/Mistral/Qwen) | REAL if endpoint set |

---

## Critical Files (Must Exist Before Dependents Can Start)

| File | Why Critical |
|---|---|
| `backend/app/agents/base/a2a_types.py` | Lingua franca for all agent communication |
| `backend/app/agents/orchestrator/orchestrator_agent.py` | Central workflow controller |
| `backend/alembic/versions/0001_initial.py` | Authoritative DB migration for all 25 tables |
| `backend/app/services/context_store/context_store_service.py` | Shared state bus enabling paused resumption |
| `backend/app/services/llm/llm_provider.py` | LLM interface underpinning all AI capabilities |

---

## Verification (End-to-End)

1. `cd backend && poetry install && alembic upgrade head && python db/seeds/seed.py` — 25 tables created, Aarav Mehta seeded
2. `uvicorn app.main:app --reload` (backend on :8000) + `cd frontend && npm run dev` (frontend on :5173)
3. Open Advisor Workspace → create new case for Aarav Mehta → select both products
4. Open Client Portal → complete conversational onboarding in < 5 minutes (Criterion #4)
5. Upload a document → verify AI validation fires (Criterion #8)
6. Resubmit document → verify version diff renders (Criterion #9)
7. Trigger KYC high-risk scenario → verify evidence packet generated (Criterion #11)
8. Approve in human review UI → verify workflow resumes (Criterion #5)
9. Open Agent Trace Canvas → verify animated edges during active onboarding (Criterion #10)
10. Open Contact Centre → verify AI call summary visible (Criterion #6)
11. `cd backend && pytest tests/` — all pass
12. Confirm all 4 NFR latency targets met in `docs/nfr_baseline.md`
