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
│   ├── alembic/versions/        # 18 DB migrations (0001–0018)
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
| FraudScreening | `agents/fraud_screening/graph.py` | `fraud_screening_activity` — runs **concurrently with KYC** via `asyncio.gather` in `_handle_kyc` | FRAUD_FLAGGED, FRAUD_CLEARED (decision_log, is_compliance_event=True) |
| DocumentIntelligence | `agents/document_intelligence/graph.py` | `direct_document_task` (DirectTask) | — |
| ProductOnboarding | `agents/product_onboarding/graph.py` | `product_onboarding_activity` inside `ProductOnboardingWorkflow` (child, one per product) | — (Phase 4: trace written as `product_onboarding[{product_code}]`; Phase 4.6: activation_gate terminal node writes PRODUCT_ACTIVATED/PRODUCT_DECLINED) |
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

### OnboardingState layout (Phase 2+)

`OnboardingState` (`a2a_types.py`) splits into a **generic typed core** and a domain-specific
**extension bag**:

| Layer | Fields | Access pattern |
|---|---|---|
| Typed core | `case_id`, `client_id`, `stage`, `selected_products`, `product_tracks`, `priority_tier`, `client_data`, `documents_*`, `version`, timestamps | Direct attributes (`state.stage`, `state.priority_tier`) |
| Extension bag | `extra: dict[str, Any]` (JSONB-backed) | `WealthExtension.from_state(state).kyc_status` |

Wealth-specific fields (`kyc_status`, `kyc_risk_score`, `sales_review_id`,
`sales_review_decision`, `escalation_reason`, `human_review_id`) live in `extra`.

**Backward compatibility:** A `model_validator` on `OnboardingState` migrates old flat
`shared_context` rows (pre-Phase-2) into `extra` automatically on load — no data migration needed.

`OnboardingStateDict` (the LangGraph TypedDict) mirrors this: `extra: dict[str, Any]` replaces
the old top-level wealth fields. `_product_code` and `_product_track_status` **must** stay in the
typed core (Temporal payload codec strips undeclared keys).

### Temporal activity constraints (known gotchas)

These rules apply to every LangGraph node that runs inside a Temporal activity.

**1. Declare every `OnboardingStateDict` key you intend to use.**

Temporal's payload codec deserializes `OnboardingStateDict` using the class's declared fields.
Any key that is *not* declared in `OnboardingStateDict` (`a2a_types.py`) is silently stripped
when the dict is passed to a child workflow or activity. The symptom is `state.get("_key", "")`
returning `""` inside the node, which triggers early-return guards and produces no trace records.

Always add new internal routing keys (e.g., `_product_code`, `_product_track_status`) to
`OnboardingStateDict` before relying on them in any node.

As an extra safety net, `ProductOnboarding`'s `_onboard_product_node` also falls back to
extracting `product_code` from `activity.info().workflow_id` if the state key is missing.

**2. `await` trace persists — never `asyncio.create_task`.**

Inside a Temporal activity, `asyncio.create_task(self._persist_agent_task(...))` is
fire-and-forget. The task may not complete before Temporal marks the activity done, silently
dropping the trace record. `BaseAgent.timed_process` now `await`s `_persist_agent_task`
in both the success and error paths.

**3. Use a direct write when the packet payload may not be JSON-serializable.**

`_persist_agent_task` silently ignores `Exception`s. If the `TaskPacket.payload` contains
non-JSON-serializable fields (e.g., large nested `client_data`), the write is dropped.
For agents where this risk exists (currently `product_onboarding`), write a second `AgentTask`
row directly via `AsyncSessionLocal` with a minimal JSON-safe payload:

```python
async with AsyncSessionLocal() as db:
    db.add(AgentTask(
        ...,
        payload={"product_code": product_code},  # minimal, always serializable
        status=response.status,
    ))
    await db.commit()
```

This guarantees the node appears in the trace canvas regardless of serialization failures.

### Known tech debt — Phase 0.5 asyncio cleanup (still pending)

The LangGraph migration preserved the old `BaseAgent` subclass bodies intact. The `process()`
methods in `kyc_compliance_agent.py` and `orchestrator_agent.py` contain `asyncio.create_task`
calls that were valid under the old asyncio substrate but are now **unreachable** from any Temporal
workflow or activity (the LangGraph graphs call internal helpers directly, bypassing `process()`).

These paths also reference flat `OnboardingState` attributes that no longer exist after Phase 2
(e.g., `self._states[case_id].escalation_reason = reason` in `orchestrator_agent.py:412`) —
safe only because the code paths are unreachable.

**Still outstanding:** audit and remove the dead `asyncio.create_task` call sites in:
- `agents/kyc_compliance/kyc_compliance_agent.py` lines 204–213
- `agents/orchestrator/orchestrator_agent.py` lines 283, 353, 444

Verify `services/conversation/conversation_coordinator.py` and
`services/orchestration/journey_resumption_service.py` have been migrated to Temporal Signals
before deleting. Do not delete the agent classes — the LangGraph graphs still instantiate them
for helper methods (`_simulate_*`, `_persist_*`).

Full detail in `docs/planning/cadf-framework-plan.md` §Phase 0.5 Known debt.

---

## 5. Data Model

### Key tables

| Table | Purpose | Phase added |
|---|---|---|
| `onboarding_cases` | Central case record (`priority_tier` added Phase 2) | Initial + 2 |
| `clients` | Client profile | Initial |
| `products` | Product catalog (JSONB step_sequence, suitability_criteria) | Initial |
| `onboarding_questions` | Per-product questionnaire | Initial |
| `documents` | Uploaded documents (scope: SHARED_CORE/PRODUCT_SPECIFIC from Phase 4.5) | Initial + 4.5 |
| `kyc_checks` | KYC check results | Initial |
| `human_reviews` | Manual review records | Initial |
| `event_log` | Operational telemetry | Initial |
| `decision_log` | Immutable hash-chained compliance audit trail (Phase 2.5) | 2.5 |
| `product_activation` | Per-product activation state machine (PENDING→CRITERIA_MET→ACTIVATED\|DECLINED) + ECOA adverse-action fields (Phase 4.6) | 4.6 |
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

### Product Pipeline Config (Phase 4+)

`domain_product_pipelines` and `domain_products.suitability_criteria` are the canonical sources
for per-product step sequences and suitability thresholds.  Hardcoded Python dicts
(`_PRODUCT_STEPS`, `_PRODUCT_MIN_RISK`, etc.) remain as fallbacks for environments where the DB
has not been migrated yet.

**ProductOnboardingAgent load order:**

1. `_load_pipeline_from_db(product_code)` — queries `domain_product_pipelines` ordered by
   `step_order`; returns `[{step_id, step_config}]` or `None` if no rows exist.
2. On `None`: falls back to `_PRODUCT_STEPS.get(product_code, _DEFAULT_STEPS)`.
3. `_load_suitability_criteria_from_db(product_code)` — queries
   `domain_products.suitability_criteria` JSONB; returns the dict or `None`.
4. On `None`: calls `SuitabilityAssessor.assess()` (hardcoded constants).
5. On success: calls `SuitabilityAssessor.assess_with_criteria(product_code, client_data, criteria)`.

**`step_config` JSONB schema:**

```json
{
  "min_ms": 200,
  "max_ms": 600
}
```

**`suitability_criteria` JSONB schema:**

```json
{
  "min_risk_level": 1,
  "min_age": 18,
  "min_income": 0.0,
  "ideal_horizons": ["short_term", "medium_term", "long_term"],
  "is_retirement_account": false,
  "scoring_weights": {"risk": 0.40, "income": 0.30, "age": 0.20, "horizon": 0.10},
  "risk_capacity_map": {...},
  "objective_to_risk": {...},
  "objective_to_horizon": {...},
  "income_range_to_float": {...}
}
```

Any key absent in the criteria dict falls back to the module-level constants in
`suitability_assessor.py`, so a minimal criteria dict (product-specific thresholds only)
also works correctly.

**Capability entry validation (Phase 4):**

`_onboard_product_node` in `graph.py` calls `_validate_agent_entry(task_type)` before dispatching
to `ProductOnboardingAgent`.  This is a *soft* check — it logs a warning if the task type is not
in `domain_agent_capabilities.subscribed_task_types` for the `product_onboarding` agent, but does
not block execution.  Intent: surface misconfiguration without breaking existing workflows.

**Trace naming (Phase 4):**

The `AgentTask` trace record and socket events use `product_onboarding[{product_code}]` as the
`to_agent` value so each parallel product track is individually identifiable in the trace canvas
and in the Temporal Web UI (child workflow IDs: `onboarding-{case_id}-product-{product_code}`).

**To add a new product:** insert rows into `domain_products` and `domain_product_pipelines`
for the domain.  No Python code changes required.

### StageDispatcher (Phase 3+)

`backend/app/services/orchestration/stage_dispatcher.py`

Replaces the hardcoded if/elif stage-routing chain that previously lived in
`orchestrator_agent.py`.  Given a `stage_code` and the domain routing data, the dispatcher
returns the Temporal activity name to invoke — driven by `domain_task_routing` rows.

**Construction — two paths:**

```python
from app.services.orchestration.stage_dispatcher import StageDispatcher

# In workflow code (inside OnboardingWorkflow.run()):
#   domain_dict is the raw dict returned by load_domain_definition_activity — no SQLAlchemy import
dispatcher = StageDispatcher.from_domain_dict(domain_dict)

# In test / non-workflow code (passes a DomainDefinition Pydantic model):
dispatcher = StageDispatcher.from_domain_def(domain_def)

dispatch = dispatcher.resolve("KYC", state)
# dispatch.activity_name == "kyc_compliance_activity"
# dispatch.action_spec.task_type == "run_kyc_check"
# dispatch.action_spec.priority == "HIGH"

fn = _ACTIVITY_LOOKUP[dispatch.activity_name]
result = await workflow.execute_activity(fn, state, ...)
```

**Why two constructors?**  `StageDispatcher` works internally with plain dicts to avoid importing
`domain_definition.py` (which imports SQLAlchemy) inside the Temporal workflow sandbox.
`SandboxedWorkflowRunner` re-imports the workflow module in a restricted environment; SQLAlchemy
is not in the passthrough list. `from_domain_dict` accepts the raw `model_dump()` output from
`load_domain_definition_activity`, keeping the workflow sandbox clean.

**Temporal sandbox passthrough** — importing `stage_dispatcher` from `app.services.orchestration`
triggers `__init__.py` → `journey_resumption_service` → `app.database` → `app.config` →
`Settings()` → `pydantic_settings` → `Path.expanduser()` (restricted).  The worker adds
`"app.services.orchestration"` to `SandboxRestrictions.default.with_passthrough_modules(...)` so
the sandbox reuses the outer process's already-loaded module cache instead of re-importing.

**`_TASK_TYPE_TO_ACTIVITY_NAME` registry** maps `task_type` values from `domain_task_routing`
rows to `@activity.defn` name strings.  To add a new task type (e.g. in Phase 6), add one entry —
no workflow code changes required.

**`SLAHook`** — Phase 3 no-op stub superseded by `_start_sla_timer()` in Phase 5.  Class is kept
for import compatibility only; all live call sites have been replaced.

**`load_domain_definition_activity`** — Temporal activity that loads `DomainDefinition` from DB
once at workflow start and returns a JSON-serializable dict.  On Temporal replay the stored
history result is returned (no DB re-query), preserving determinism.

### SLAMonitorService (Phase 5+)

`backend/app/services/sla/sla_monitor_service.py`

Handles all DB operations for SLA clock tracking.  The Temporal workflow calls it only via
Temporal activities (never directly), so all writes are durable and crash-safe.

**Key responsibilities:**

- `resolve_sla(db, domain_code, stage_code, priority_tier, product_code)` — resolves the
  best-matching `domain_stage_slas` row using a 4-step priority chain (most-specific → least):
  `(stage + tier + product)` → `(stage + tier)` → `(stage + product)` → `(stage)`.
  Returns `None` if no row exists or the row has `is_enabled=False`.

- `start_tracking(db, case_id, stage_code, sla_spec, ...)` — writes a `case_sla_tracking` row
  at stage entry.  `started_at` is set to `now()`.

- `pause_tracking / resume_tracking` — clock-pause support for human-review stages.
  `resume_tracking` accumulates `paused_duration_seconds` and returns `elapsed_active_seconds`
  so `_watch_sla` can restart with the correct remaining time.

- `record_warning_sent / record_breach_triggered` — idempotent: returns `False` if the
  timestamp is already set, so double-fires have no effect.

- `get_net_elapsed_seconds` — subtracts accumulated pause time (including any in-progress pause)
  from total elapsed.

**SLA Temporal activities (in `onboarding_workflow.py`):**

| Activity | Purpose |
|---|---|
| `start_sla_tracking_activity` | Resolve SLA config + write `case_sla_tracking` row; returns config dict or None |
| `pause_sla_tracking_activity` | Record `paused_at` (human-review stages) |
| `resume_sla_tracking_activity` | Accumulate pause; return `elapsed_active_seconds` |
| `send_sla_warning_activity` | Write `SLA_WARNING` to `decision_log`; log warning |
| `trigger_sla_breach_activity` | Write `SLA_BREACH` (`is_regulatory_breach=True`); escalate case to ESCALATED |

**`_watch_sla(case_id, stage_code, sla_config, elapsed_seconds=0.0)`** — async Temporal coroutine
started as `asyncio.create_task()` inside each stage handler.  Cancelled via `finally` block when
the stage exits.  `elapsed_seconds > 0` is used when restarting after a clock-pause.

**Clock pausing (REVIEW, SALES_REVIEW):** if `sla_config["pause_on_human_review"]` is `True`,
the stage handler cancels the SLA task, calls `pause_sla_tracking_activity`, waits for the
human signal, then calls `resume_sla_tracking_activity` and restarts `_watch_sla` with the
remaining active time.

**`is_regulatory_breach=True`** is set on `decision_log` entries written by
`trigger_sla_breach_activity` — required for BSA 5-year WORM retention.

### DecisionLogService (Phase 2.5+)

`backend/app/services/audit/decision_log_service.py`

Every agent decision and compliance event must call `DecisionLogService.append()`. This is the
tamper-evident compliance trail — distinct from `EventLog` (operational telemetry).

```python
from app.services.audit.decision_log_service import decision_log_service, DecisionLogEntry

await decision_log_service.append(DecisionLogEntry(
    agent_id="kyc_compliance",
    event_type="KYC_PASSED",
    payload={"case_id": str(case_id), "risk_band": "LOW"},
    case_id=case_id,
    client_id=client_id,
    is_compliance_event=True,
))
```

**Chain structure:** `payload_hash = SHA-256(canonical JSON)`;
`chain_hash = SHA-256(prev_chain_hash + payload_hash)`. Genesis `prev_hash = '0' * 64`.

**WORM:** `DecisionLogService` has no `update()` or `delete()`. In production, revoke
`UPDATE`/`DELETE` on `decision_log` from the app DB role (see migration `0016_decision_log.py`).

**Verify integrity:** `GET /audit/verify` — returns `{valid, total, broken_at_seq}`.

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
| audit | `/audit` | `GET /audit/logs` (EventLog), `GET /audit/verify` (chain integrity), `GET /cases/{id}/audit` (decision log), `GET /audit/export` (BSA CSV/JSON) |
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
