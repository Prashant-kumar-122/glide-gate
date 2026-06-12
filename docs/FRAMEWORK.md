# CADF Framework Developer Reference

Detailed developer and architecture reference for the GlideGate / CADF (Client Agentic
Development Framework) project. Read this to understand how to extend the framework — add
agents, products, APIs, MCP tools, domain config, or migrations.

**Companion docs:** `docs/planning/cadf-framework-plan.md` (phase plan) ·
`docs/TRACEABILITY.md` (FR/ADR coverage) · `docs/UX_UI_STANDARDS.md` (frontend standards)

---

## 1. Project Layout

```
glide-gate/
├── backend/
│   ├── app/
│   │   ├── agents/              # LangGraph agent graphs (post Phase 0.5)
│   │   │   ├── base/            # BaseAgent, AgentEventBus, a2a_types
│   │   │   ├── orchestrator/    # OrchestratorAgent → OnboardingWorkflow (Phase 0.5)
│   │   │   ├── kyc_compliance/  # KYCComplianceAgent → LangGraph graph
│   │   │   ├── document_intelligence/
│   │   │   ├── product_onboarding/
│   │   │   ├── fraud_screening/ # NEW (Phase 4.6)
│   │   │   ├── collaboration/
│   │   │   ├── notification/
│   │   │   ├── sales_manager/
│   │   │   ├── contact_centre/
│   │   │   └── skills/          # 6 composable skills (dormant → active in Phase 6)
│   │   ├── api/routers/         # FastAPI routers (20+ endpoints)
│   │   ├── domain/              # DomainDefinition model (Phase 1)
│   │   ├── mcp/                 # MCPConnector ABC + MCPRegistry gateway
│   │   ├── models/              # SQLAlchemy models (25+ tables)
│   │   ├── services/            # Business logic services
│   │   ├── workflows/           # Temporal workflow definitions (Phase 0.5)
│   │   └── main.py              # FastAPI app + startup
│   ├── alembic/versions/        # 15+ DB migrations
│   └── tests/                   # unit / integration / e2e
├── frontend/
│   ├── src/
│   │   ├── features/            # 8 feature modules
│   │   ├── hooks/               # 21 custom hooks
│   │   ├── routes/              # 8 route files
│   │   └── store/               # 8 Zustand stores
│   └── public/docs/index.html   # In-app self-contained documentation site
├── db/schema/                   # Raw SQL schema files (reference)
├── configs/agents/              # Agent configuration JSON files
├── docs/
│   ├── planning/cadf-framework-plan.md  # Phase plan (single source of truth)
│   ├── FRAMEWORK.md             # This file
│   ├── TRACEABILITY.md          # Living FR/NFR → phase matrix
│   ├── UX_UI_STANDARDS.md       # Mandatory frontend design standards
│   └── specs/                   # BRD, Technical Architecture, ADRs
├── scripts/
│   ├── git-hooks/pre-commit     # Docs-gate hook (install with: make install-hooks)
│   └── ops/                     # Backup, restore, audit integrity scripts
└── Makefile                     # Common dev tasks
```

---

## 2. Maintenance Policy

**Rule:** no feature, agent, API, schema change, or significant decision is "done" until
the relevant docs are updated in the same commit. Docs are part of the Definition of Done.

See `docs/planning/cadf-framework-plan.md` §Documentation-as-Definition-of-Done for the full
checklist and per-change update rules.

Install the pre-commit docs-gate:
```bash
make install-hooks
```
Or manually:
```bash
cp scripts/git-hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

To enforce (block commit if no docs updated):
```bash
DOCS_GATE=block git commit -m "..."
```

---

## 3. Running the Project

### Prerequisites
- Docker + Docker Compose
- Python 3.12+ (for local backend dev)
- Node.js 20+ (for frontend dev)

### Start the full stack
```bash
docker compose up -d
```

### Start with observability overlay (Phase 13+)
```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

### Backend development
```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

### Frontend development
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### Run tests
```bash
make test          # backend pytest
make test-frontend # frontend type-check + jest
make e2e           # Playwright E2E (requires full stack running)
```

### Temporal Web UI (Phase 0.5+)
```
http://localhost:8233
```

---

## 4. Agent Architecture

### Agent model (post Phase 0.5)

Each agent is a **LangGraph `StateGraph`** compiled to a runnable. The state type is
`OnboardingStateDict` (TypedDict mirroring `OnboardingState`). Stage transitions are driven
by **Temporal Signals** on `OnboardingWorkflow`; per-request tasks (DIA, notifications, etc.)
run as short-lived `DirectTaskWorkflow` instances.

```
OnboardingWorkflow (Temporal root)
  │
  ├── customer_service_kickoff_activity  → CustomerService kickoff graph (WS emit + DB init)
  │   [multi-turn conversation via REST API → ConversationCoordinator → LLM stream]
  │   [on completion → advance_stage signal → workflow advances to KYC]
  │
  ├── kyc_compliance_activity            → KYC LangGraph graph (identity + risk + checkpoint)
  │
  ├── ProductOnboardingWorkflow (child) × N  → product_onboarding_activity
  │                                           → ProductOnboarding LangGraph graph
  │
  ├── sales_manager_kickoff_activity     → SalesManager kickoff graph
  ├── collaboration_kickoff_activity     → Collaboration graph
  ├── notification_activity              → Notification graph
  └── escalation_alert_activity         → Notification + ContactCentre graphs

DirectTaskWorkflow (short-lived, one per fire-and-forget task)
  └── dispatches to one of: NotificationAgent · DocumentIntelligenceAgent
      CollaborationAgent · ContactCentreAgent · SalesManagerAgent
      ProductOnboardingAgent · CustomerServiceAgent
      (registered in backend/app/agents/direct_task_activities.py)
```

### Agent inventory

| Agent | Location | Entry point | Key signals emitted |
|---|---|---|---|
| CustomerService | `agents/customer_service/graph.py` | `customer_service_kickoff_activity` (workflow) + `direct_customer_service_task` (DirectTask) | ADVANCE_STAGE (via ConversationCoordinator) |
| KYCCompliance | `agents/kyc_compliance/graph.py` | `kyc_compliance_activity` (workflow) | — (outcome written to state; workflow advances stage) |
| FraudScreening (Phase 4.6) | `agents/fraud_screening/graph.py` | TBD | FRAUD_FLAGGED, FRAUD_CLEARED |
| DocumentIntelligence | `agents/document_intelligence/graph.py` | `direct_document_task` (DirectTask) | — |
| ProductOnboarding | `agents/product_onboarding/graph.py` | `product_onboarding_activity` inside `ProductOnboardingWorkflow` (child) | — |
| Collaboration | `agents/collaboration/graph.py` | `collaboration_kickoff_activity` (workflow) | — |
| Notification | `agents/notification/graph.py` | `notification_activity` / `escalation_alert_activity` (workflow) | — |
| SalesManager | `agents/sales_manager/graph.py` | `sales_manager_kickoff_activity` (workflow) + `direct_sales_manager_task` (DirectTask) | — |
| ContactCentre | `agents/contact_centre/graph.py` | `contact_centre_summary_activity` (workflow) | — |

### Adding a new agent

1. Create `backend/app/agents/{name}/graph.py` — implement `build_{name}_graph() -> CompiledGraph`
2. Add a row to `domain_agent_roster` (`agent_id`, `agent_class`, `domain_id`)
3. Add rows to `domain_agent_capabilities` (subscribed task types, emitted task types,
   allowed handoffs)
4. For workflow-stage agents: add an `@activity.defn` function in `onboarding_workflow.py` and
   register it in `get_all_activities()`. For per-request agents: add a `direct_{name}_task`
   activity in `direct_task_activities.py` and add it to `_AGENT_ACTIVITY`.
5. No changes to `OnboardingWorkflow` routing or any existing agent.
6. Update `docs/FRAMEWORK.md` §Agent inventory and `docs/TRACEABILITY.md`

---

## 5. Data Model

### Key tables

| Table | Purpose | Phase added |
|---|---|---|
| `onboarding_cases` | Central case record | Initial |
| `clients` | Client profile | Initial |
| `products` | Product catalog (JSONB step_sequence, suitability_criteria) | Initial |
| `onboarding_questions` | Per-product questionnaire | Initial |
| `documents` | Uploaded documents (scope: SHARED_CORE/PRODUCT_SPECIFIC from Phase 4.5) | Initial + 4.5 |
| `kyc_checks` | KYC check results | Initial |
| `human_reviews` | Manual review records | Initial |
| `event_log` | Operational telemetry | Initial |
| `decision_log` | Immutable hash-chained compliance audit trail (Phase 2.5) | 2.5 |
| `product_activation` | Per-product activation state + adverse action (Phase 4.6) | 4.6 |
| `domain_*` (15 tables) | CADF domain model — stages, transitions, SLAs, personas, etc. | 1 |
| `case_sla_tracking` | SLA elapsed tracking per case/stage | 5 |

### DomainDefinition (Phase 1+)

`backend/app/domain/domain_definition.py` provides:

- **`DomainDefinition`** — Pydantic model holding the fully-loaded in-memory snapshot of one
  deployed domain: stages, FSM transitions, task routing, agent roster, capabilities, SLA specs,
  personas, permissions, product catalog, and display vocabulary.
- **`DomainDefinitionLoader`** — async loader that reads all 15 `domain_*` tables for a given
  `domain_code` and returns a validated `DomainDefinition`. Raises `DomainValidationError` on:
  - dangling transition targets or sources
  - no terminal stages / unreachable terminal
  - SLA row referencing an undefined stage
  - `warning_pct >= escalation_pct`
- **`SLASpec`** — validates `warning_pct < escalation_pct` at construction time (also enforced
  by `DB CHECK domain_stage_slas_pct_chk`).

Usage in an async service:
```python
from app.domain import DomainDefinitionLoader

async with AsyncSessionLocal() as session:
    loader = DomainDefinitionLoader(session)
    domain = await loader.load("wealth_management")
    # domain.stages, domain.transitions, domain.task_routing, ...
```

### Adding a migration

```bash
cd backend
poetry run alembic revision --autogenerate -m "describe_the_change"
# Review the generated file in alembic/versions/
poetry run alembic upgrade head
```

Update `docs/FRAMEWORK.md` §Data Model for any structural change.

---

## 6. API Endpoints

### Current routers

| Router | Prefix | Key endpoints |
|---|---|---|
| cases | `/cases` | CRUD, stage workflow, product selection |
| conversations | `/conversations` | Chat, call summary |
| documents | `/documents` | Upload, validate, versioning |
| reviews | `/reviews` | KYC/compliance review workflow |
| sales_reviews | `/sales-reviews` | Sales manager approval |
| clients | `/clients` | Client profile CRUD |
| audit | `/audit` | Audit log queries, `/verify`, `/export` (Phase 2.5) |
| domain_config | `/api/config/domain` | Domain vocabulary (Phase 10) |
| admin/* | `/admin/` | Admin portal CRUD (Phase 9) |

### Adding an endpoint

1. Create or extend a router in `backend/app/api/routers/`
2. Register in `main.py` `app.include_router()`
3. Add `require_permission("scope")` guard from the Phase 7 catalog
4. Write an integration test in `backend/tests/integration/api/`
5. Update `docs/FRAMEWORK.md` §API Endpoints and README if user-facing

---

## 7. Skills Framework

Skills are composable LLM-capability building blocks. Each skill wraps `_execute(**kwargs)` with
timing and `EventLog` persistence. Singletons live in `agents/skills/__init__.py`.

| Skill | Class | Purpose |
|---|---|---|
| information_extraction | `InformationExtractionSkill` | Extract structured data from unstructured text |
| decision_reasoning | `DecisionReasoningSkill` | Provide reasoning chains for decisions |
| status_summarisation | `StatusSummarisationSkill` | Summarise case/call status |
| clarification | `ClarificationSkill` | Generate clarification questions |
| escalation | `EscalationSkill` | Determine escalation triggers |
| product_suitability | `ProductSuitabilitySkill` | Assess product suitability |

After Phase 6, agents call skills via `domain_agent_skills` bindings — no hardcoded skill
references in agent code.

### Adding a skill

1. Create `backend/app/agents/skills/{name}_skill.py` extending `BaseSkill`
2. Add singleton to `agents/skills/__init__.py`
3. Add `domain_agent_skills` rows binding the skill to agents that should use it
4. Update `docs/FRAMEWORK.md` §Skills

---

## 8. MCP Gateway

The MCP gateway (`mcp/mcp_connector.py`) is the sole egress for external integration calls
(ADR-007). After Phase 6, no agent calls external services directly.

### Registered connectors

| Connector | `connector_name` | Tools |
|---|---|---|
| Identity Verification | `identity_verification` | `verify_identity`, `screen_ofac` |
| Document Management | `document_management` | `store_document`, `retrieve_document` |
| Credit Bureau (Phase 4.6) | `credit_bureau` | `pull_credit_report`, `assess_affordability` |
| OPA Policy (Phase 4.6) | `opa_policy` | `evaluate_activation` |

### Adding an MCP connector

1. Create `backend/app/mcp/connectors/{name}_connector.py` extending `MCPConnector`
2. Register in `main.py` `mcp_registry.register(YourConnector())`
3. Add `domain_agent_tool_grants` rows for each agent that needs access
4. Update `docs/FRAMEWORK.md` §MCP Gateway and Tech Architecture Appendix B

---

## 9. Adding a Product Line

To add a new product (e.g., "term_deposit"):

1. **Via admin portal (Phases 9+):** preferred — zero code changes
   - Create product in `/admin/products` with `step_sequence` JSONB
   - Define `suitability_criteria` JSONB
   - Assign `shared_core_types` (document types collected once for all products)
   - Define `activation_criteria` JSONB (evaluated by OPA gate)
   - Compose per-product agent pipeline in the pipeline editor
   - Assign questions via the questionnaire editor

2. **Via seed script (pre-Phase 9):**
   - Insert row into `domain_products`
   - Insert rows into `domain_product_pipelines` (step sequence)
   - Insert rows into `onboarding_questions` with `product_id` FK
   - Run `alembic upgrade head` if schema change needed

Update `docs/TRACEABILITY.md` — which FR rows does this product serve?

---

## 10. Domain Configuration Model

The `DomainDefinition` (loaded by `DomainDefinitionLoader`) is the runtime representation of
all `domain_*` table rows for one domain. It is:
- Validated on load (dangling edges, SLA misconfiguration, wiring errors all fail fast)
- Passed to `StageDispatcher` (Phase 3) and agent workers at startup
- Re-loaded on admin portal "Activate" action (new cases get new config; in-flight cases pin to
  their starting version)

Tables loaded: `domain_stages`, `domain_transitions`, `domain_task_routing`,
`domain_agent_roster`, `domain_agent_capabilities`, `domain_product_pipelines`,
`domain_agent_prompts`, `domain_agent_skills`, `domain_agent_tool_grants`, `domain_stage_slas`,
`domain_personas`, `domain_permissions`, `domain_products`, `domain_display_config`

---

## 11. Authentication & Authorization

### Current (pre-Phase 7)
- JWT + bcrypt via `python-jose` (`services/auth/auth_service.py`)
- `require_role("advisor", "compliance")` guards in routers
- `users.role` DB CHECK enum (wealth-specific)

### After Phase 7
- `require_permission("scope")` guards (e.g., `require_permission("review:approve")`)
- `domain_personas` rows define valid roles per domain
- `domain_permissions` rows map persona → permission scope
- Permission catalog (15 fixed scopes) documented in `docs/specs/permission-model-security-review.md`

### Keycloak OIDC (planned — not in current CADF phases)
The reference project implements full Keycloak OIDC + RBAC. This is not in the current phase
plan but can be added as a Phase 7+ sub-task when Keycloak is introduced to docker-compose.

---

## 12. Frontend Feature Structure

### Feature modules

| Module | Route | Personas |
|---|---|---|
| `features/admin/` | `/admin` | admin |
| `features/advisor/` | `/advisor` | advisor |
| `features/agent-trace/` | `/trace` | advisor, admin |
| `features/auth/` | `/login`, `/signup` | all |
| `features/client/` | `/portal` | client |
| `features/compliance-review/` | embedded in advisor | compliance |
| `features/contact-centre/` | `/contact` | contact_centre |
| `features/notifications/` | overlay | all |

### After Phase 10: `useDomainConfig()` hook

All stage labels, persona colors, nav links, and document scope labels are served from
`GET /api/config/domain` and consumed via `useDomainConfig()`. Hardcoded vocab constants
(`STAGE_LABELS`, `ROLE_COLORS`, etc.) are replaced. Static wealth-domain fallback provided
during rollout.

### Adding a frontend screen

1. Create component in the relevant `features/` directory
2. Add route in `App.tsx` with `ProtectedRoute` and `require_permission` check
3. Must comply with `docs/UX_UI_STANDARDS.md` §Checklist
4. Add Playwright E2E test in `frontend/e2e/`
5. Update `docs/FRAMEWORK.md` §Frontend and FRD if applicable

---

## 13. Environment Variables

See `.env.example` for all required variables. Key groups:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL async URL |
| `PRIMARY_LLM_PROVIDER` | `anthropic` \| `openai` \| `google` \| `local` |
| `ANTHROPIC_API_KEY` | Required if `PRIMARY_LLM_PROVIDER=anthropic` |
| `TEMPORAL_HOST` | Temporal gRPC address (default: `localhost:7233`) |
| `TEMPORAL_NAMESPACE` | Temporal namespace (default: `default`) |
| `SOCKETIO_CORS_ORIGINS` | JSON array of allowed WebSocket origins |
| `AUTH_COOKIE_NAME` | Session cookie name |
| `SECRET_KEY` | JWT signing secret |
| `VAPID_PUBLIC_KEY` | Web Push VAPID key (push notifications) |
| `DOCS_GATE` | `warn` (default) or `block` — pre-commit docs enforcement |

---

## 14. Observability (Phase 13+)

After Phase 13, every Temporal Activity and LangGraph node emits OTel spans.

- **Traces:** Tempo (`http://localhost:3200`)
- **Metrics:** Prometheus (`http://localhost:9090`) + Grafana dashboards (`http://localhost:3000`)
- **Logs:** Loki (via Docker log driver)
- **Key metrics:** `onboarding_cases_active`, `stage_transition_duration_seconds`,
  `llm_call_duration_seconds`, `mcp_tool_call_total`, `sla_breach_total`

Start observability stack: `docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d`

---

## 15. CI/CD (Phase 13+)

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Trigger | Jobs |
|---|---|---|
| `ci.yml` | Push / PR | Python tests, frontend build + type-check, Docker build, Semgrep SAST, Trivy scan |
| `release.yml` | Tag push | SBOM generation, image signing (cosign) |

Run locally: `make test` (unit) · `make e2e` (full stack E2E)
