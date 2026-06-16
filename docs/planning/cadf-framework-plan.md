# CADF — Client Agentic Development Framework
## Conversion Plan: GlideGate → Generic Admin-Configurable Onboarding Framework

## Phase Status Tracker

> **Read this first every session.** Find the first unchecked phase — that is where to start.
> When a phase is fully verified and committed, change `[ ]` to `[x]` and commit this file.
> `[~]` means the phase was explicitly skipped by the team — do not implement it; treat it as done for sequencing purposes.

- [x] **Phase 0** — Audit & wire dead orchestrator config
- [x] **Phase 0.5** — Migrate orchestration to Temporal + LangGraph (ADR-001 / ADR-004)
- [x] **Phase 1** — Design the DB-backed DomainDefinition model
- [x] **Phase 2** — Split OnboardingState into typed core + extension bag
- [x] **Phase 2.5** — Hash-chain audit log (FR-AU-01 / BSA compliance)
- [x] **Phase 3** — Replace if/elif stage routing with config-driven StageDispatcher
- [x] **Phase 4** — Make products, questions, and per-product agent pipelines config-driven
- [~] **Phase 4.5** — Shared-core document taxonomy (FR-DM-01/02/03) ⚠️ SKIPPED — implementation was reverted; do not implement, proceed directly to Phase 4.6
- [x] **Phase 4.6** — First-to-complete activation gate (FR-GL-01/02/03)
- [ ] **Phase 5** — Configurable SLA enforcement with feature flags and per-stage parameters
- [ ] **Phase 6** — Wire Skills & MCP into live agent execution, made domain-configurable
- [ ] **Phase 7** — Replace hardcoded personas/roles with configurable persona + permission model
- [ ] **Phase 8** — Loosen DB CHECK constraints; make domain reference rows authoritative
- [ ] **Phase 9** — Build the Admin Portal
- [ ] **Phase 10** — Serve frontend vocabulary from the domain API
- [ ] **Phase 11** — Stand up Retail/Deposit through the admin portal (acceptance proof)
- [ ] **Phase 12** — Extract the framework/domain package boundary
- [ ] **Phase 13** — Observability, IaC & Operations (NFR-03 / NFR-10)

---

## How to use this document (read first in every session)

This is the single source of truth for all team members and Claude sessions executing this plan.
Each phase is designed to be started cold in a new Claude session with no prior context. To begin
a session:

1. Read this document top-to-bottom — it contains all verified ground truth and design decisions.
2. Find the first unchecked `[ ]` phase in the tracker above — that is the current phase.
3. Run the **Session start checklist** for that phase.
4. Implement using the phase description.
5. Run the **Verification** steps.
6. Commit using the provided template, then mark the phase `[x]` in the tracker above and commit
   this file too.

The `CLAUDE.md` at the project root intentionally contains only a pointer here — all context
lives in this file.

---

## Background & Context

GlideGate ("CADF — Client Agentic Development Framework") was built as a wealth-management
client-onboarding platform: a custom asyncio-based multi-agent backend (FastAPI/Python, ~6,880
lines of agent code) plus a React/TypeScript frontend, backed by PostgreSQL. The spec docs in
`docs/specs/` (BRD, Technical Architecture, ADRs) describe the target architecture
(Temporal, LangGraph, MCP Gateway, OPA, "Criteria & Wiring Designer" UI) — much of which already
exists in skeletal/dormant form in the real code, just not wired up or made configurable.

**New requirement:** generalize this into a reusable framework for *different onboarding domains*
(Retail/Deposit, Loans, Mortgage, etc. — already named in the Technical Architecture roadmap),
where new domains, their workflows, personas/roles, agent prompts/skills/MCP tool-access,
products and their onboarding questions, per-product agent pipeline composition, per-stage SLA
windows with priority-tier overrides and per-product feature flags can all be configured
**through an admin portal** — not by an engineer editing code or redeploying.

---

## Strategy (decided — do not re-litigate)

- **ADR-compliant stack.** Adopt Temporal (ADR-001) and LangGraph (ADR-004) as the orchestration
  and agent-execution substrate. Phase 0.5 migrates the existing asyncio/BaseAgent code to this
  stack. JVM/Spring Boot core (ADR-004) is deferred — Python-first until a business case requires
  polyglot. ADR-009 formalizes these decisions.
- **Config-driven, DB-backed, admin-authored.** Keep and generalize the existing working
  substrate (Skills framework, MCP gateway abstraction, existing `Product.step_sequence`/
  `suitability_criteria` JSONB columns, `OnboardingQuestion.product_id` FK, and
  `OnboardingCase.sla_deadline` field + escalation flow). Do not rewrite business logic.
- **Finish wiring what already exists.** Most abstractions (Skills, MCP gateway,
  product JSONB columns, SLA deadline field) are already built but dormant/bypassed. The plan is
  mostly "activate + generalize", not "build from scratch".
- **Explicit over implicit.** Keep the FSM, product pipelines, and SLA schedules as editable,
  visualizable graphs in the admin portal.
- **Single-tenant per deployment.** No runtime domain-switching. Prove genericity by standing up
  Retail/Deposit as a separate deployment configured entirely through the admin portal.
- **Extensibility contract.** New stages inserted via `domain_stages`/`domain_transitions` rows.
  New agents declare entry/exit contracts via `domain_agent_capabilities` rows. Existing agents
  are never modified when new stages or agents are added.
- **Criteria-driven activation (ADR-002).** No premature product activation — OPA gate validates
  that all required checks pass before a product transitions to ACTIVATED. First product to
  satisfy its criteria activates independently; others continue in parallel.
- **MCP gateway as sole egress (ADR-007).** After Phase 6, no agent may call external integrations
  directly. All tool calls go through `MCPRegistry.invoke()` with grant-checking.
- **Hash-chained audit trail (FR-AU-01).** Every agent decision and compliance event appends to
  an append-only, hash-chained `decision_log` table. Tamper detection is a compliance requirement,
  not a nice-to-have.

---

## Verified Ground Truth (read before any phase — accurate as of 2026-06-09)

### FSM / routing / state
- `a2a_types.py`: `AgentID` (9-value StrEnum), `TaskType` (20+ value StrEnum), `OnboardingStage`
  (7-value StrEnum), `OnboardingState` (Pydantic — mixes generic fields `case_id`/`stage`/
  `selected_products`/`version` with wealth-specific `kyc_status`/`kyc_risk_score`/
  `sales_review_decision`/`escalation_reason`/`human_review_id`).
- `workflow_state_machine.py:22-51`: FSM transitions hardcoded as `_TRANSITIONS` Python dict.
  `is_human_pending()` identifies human-review stages (REVIEW, SALES_REVIEW) — used by SLA
  clock-pause logic.
- `orchestrator_agent.py:202-207,538-687`: stage routing hardcoded as `_resume_routing` dict +
  ~150-line if/elif chain.
- `configs/agents/orchestrator.config.json`: mirrors the FSM as JSON but code never reads it;
  stale — missing SALES_REVIEW (added by `sales-manager-role-plan.md`, completed 2026-06-03).
  This is the "dead config" Phase 0 fixes.

### Personas / roles
- `users.role` DB CHECK enum; `require_role(...)` guards scattered across `cases.py`,
  `clients.py`, `reviews.py`, `audit.py`, `collaboration.py`. Frontend hardcodes `TeamRole`,
  `ROLE_COLORS`, `ROLE_LABEL`, `NAV_LINKS`, `ROLE_HOME`. Adding `sales_manager` alone touched
  ~13 files — the key evidence personas must become admin-configurable data.

### Prompts / Skills / MCP (built but dormant)
- **Prompts**: hardcoded inline `_SYSTEM`/`_SYSTEM_PROMPT` constants per skill/agent. DB-backed
  override store exists (`services/validation/prompt_override_store.py`, loaded at
  `main.py:91-100`) but scoped to validation prompts only, not domain-scoped.
- **Skills**: full framework built — `agents/skills/base_skill.py` ABC + 6 concrete singletons
  in `agents/skills/__init__.py`. Zero `skill.invoke()` calls from any agent — registry built,
  dormant.
- **MCP**: full gateway — `mcp/mcp_connector.py` (`MCPConnector` ABC, `MCPRegistry`), 2
  registered connectors (Identity Verification, Document Management), `mcp_logger.py`
  (`is_simulated=True`). Agents bypass it via `_simulate_*` methods; comments say "STEP-16".

### Products / questions / agent composition
- `Product` model has `suitability_criteria` and `step_sequence` JSONB columns
  (`models/cases.py:59-80`, `db/schema/002_onboarding_cases.sql:35-51`). `OnboardingQuestion`
  has nullable `product_id` FK (`questionnaire.py:53`). Schema already anticipates per-product
  config. Code ignores it: `product_onboarding_agent.py:102-117` reads hardcoded `_PRODUCT_STEPS`
  dict; `suitability_assessor.py:18-79` hardcodes `_RISK_CAPACITY_MAP`, `_PRODUCT_MIN_*`,
  scoring weights.
- `_build_agents()` (`agent_orchestration_service.py:255-282`): hardcoded global list of 8 agent
  classes — no per-product roster concept.

### SLA / escalation
- `OnboardingCase.sla_deadline` field exists (`models/cases.py:37`) — dead field.
- Escalation path IS fully built: KYC → Orchestrator → ESCALATED stage + `SEND_ESCALATION_ALERT`
  → NotificationAgent (CRITICAL priority, socket.io broadcast). SLA breach will reuse this.
- `EventLog` (`models/agents.py:72-90`): `event_type`, `event_category`, `is_compliance_event`
  bool. No hash chaining yet.

### Schema / frontend
- DB CHECK constraints (`oc_status_chk`, `oc_stage_chk`, `product_type`) hardcode wealth vocab.
- `frontend/src/features/advisor/CaseListTable.tsx:14-34`: `STAGE_LABELS`/`STAGE_STYLES`/
  `ALL_STAGES` hardcoded; no domain-config API today.
- `ContextStoreService`: per-case `asyncio.Lock`, optimistic `version`-locking, DB snapshot
  persistence — clean, reusable blackboard as-is. After Phase 0.5 this becomes LangGraph State.

---

## Phase Dependency Map

```
Phase 0 → Phase 0.5 → Phase 1 → Phase 2 → Phase 2.5 → Phase 3 ────────────────────────┐
                                                          └── Phase 4 (parallel w/ 5) ──┤
                                                          |   └── Phase 4.5 ────────────┤
                                                          |   └── Phase 4.6 ────────────┤
                                                          └── Phase 5 (parallel w/ 4) ──┤
                                                                                         ↓
                     Phase 6 → Phase 7 → Phase 8 → Phase 9 → Phase 10 → Phase 11 → Phase 12 → Phase 13
```

Phases 4, 4.5, 4.6, and 5 all depend on Phase 3 but are independent of each other and can be
worked in parallel by different team members.

---

## Documentation-as-Definition-of-Done

See `docs/FRAMEWORK.md` for the full maintenance policy. Key rule: **no feature, agent, API
endpoint, schema change, or significant decision is "done" until the relevant docs are updated in
the same commit.** Install the pre-commit docs-gate: `make install-hooks`.

**What to update when:**

| When you… | Update |
|---|---|
| Implement or complete a phase | Mark phase `[x]` in tracker above; update `docs/TRACEABILITY.md` |
| Add/change an agent | `docs/FRAMEWORK.md` §Agents; `docs/TRACEABILITY.md` |
| Add/change a DB migration | `docs/FRAMEWORK.md` §Data Model |
| Add/change an API endpoint | `docs/FRAMEWORK.md` §API; README if user-facing |
| Add/change any UI screen | Must comply with `docs/UX_UI_STANDARDS.md` |
| Make a significant architectural decision | Add a new ADR; never silently change an existing one |
| Change build/run/test/config | `docs/FRAMEWORK.md` §Running; README; `.env.example` |

**Definition-of-Done checklist (before marking any phase `[x]`):**
- [ ] Code + tests updated and passing
- [ ] `docs/TRACEABILITY.md` status updated for affected FR/NFR rows
- [ ] `docs/FRAMEWORK.md` updated for new agents/APIs/config/schema
- [ ] New significant decision captured as a new ADR
- [ ] UI changes pass `docs/UX_UI_STANDARDS.md` §Checklist (tokens, dark/light, mobile, axe)

---

## TRACEABILITY (Living FR/NFR → Phase Map)

Full detail in `docs/TRACEABILITY.md`. Summary of coverage:

| BRD Req | Description | Phase | Status |
|---|---|---|---|
| FR-DM-01/02/03 | Shared-core document collect-once + reuse | Phase 4.5 | ⬜ |
| FR-WF-01/02 | Per-product configurable workflows | Phase 4 | ✅ |
| FR-OR-01/02/03/04/05 | Parallel multi-product orchestration | Phase 0.5, Phase 4 | ⬜ |
| FR-AG-01/02/03 | Autonomous agent progression + data collection | Phase 0.5 | ⬜ |
| FR-AG-05/06 | HITL escalation queues + authority limits | Phase 7, Phase 9 | ⬜ |
| FR-AG (fraud) | Fraud/anomaly screening agent | Phase 4.6 | ⬜ |
| FR-GL-01/02/03 | First-to-complete activation gate (OPA) | Phase 4.6 | ⬜ |
| FR-CP-01/02 | Client self-service portal + document upload | Phase 10 | ⬜ |
| FR-CP-06 | E-signature & consent capture | Phase 9 (deferred) | ⬜ |
| FR-AU-01 | Immutable hash-chained audit trail | Phase 2.5 | ⬜ |
| FR-AU-02 | Human override identity/reason captured | Phase 7 | ⬜ |
| FR-AU-03 | Audit export + reporting | Phase 2.5 | ⬜ |
| FR-AU-04 | Adverse-action records (ECOA) | Phase 4.6 | ⬜ |
| NFR-01 | Encryption + RBAC + least-privilege | Phase 7 | ⬜ |
| NFR-03 | 99.95% availability, RTO ≤ 15m, RPO ≈ 0 | Phase 13 | ⬜ |
| NFR-09 | WCAG 2.1 AA accessibility | Phase 10 | ⬜ |
| NFR-10 | OTel/Prometheus/Grafana/Loki/Tempo | Phase 13 | ⬜ |
| ADR-001 | Temporal self-hosted orchestration | Phase 0.5 | ⬜ |
| ADR-002 | Criteria-driven blackboard activation | Phase 3, Phase 4.6 | ⬜ |
| ADR-004 | LangGraph Python agents | Phase 0.5 | ⬜ |
| ADR-006 | OPA activation gate (strong consistency) | Phase 4.6 | ⬜ |
| ADR-007 | MCP gateway sole egress | Phase 6 | ⬜ |
| ADR-008 | Self-hosted/pluggable LLM | Phase 6 | 🟡 |

---

## Phase 0 — Audit & wire up the dead orchestrator config

### Session start checklist
- Run `git log --oneline -5` — should be on `main` with no prior CADF phase commits
- Read `configs/agents/orchestrator.config.json` (the dead config)
- Read `backend/app/agents/orchestrator/workflow_state_machine.py:1-60` (the live FSM)
- Read `backend/app/agents/orchestrator/orchestrator_agent.py:195-215` (resume routing dict)

### What to build
Correct `configs/agents/orchestrator.config.json` to exactly match `_TRANSITIONS` in
`workflow_state_machine.py` (add the missing SALES_REVIEW stage and its transition edges — added
by `sales-manager-role-plan.md`, 2026-06-03, never synced to JSON). Then make
`workflow_state_machine.py` load its transitions from the JSON file instead of the hardcoded
`_TRANSITIONS` dict, and `orchestrator_agent.py` load its `_resume_routing` from the same file.

**Why this matters:** closes a real drift bug AND proves "data drives the FSM" cheaply — same fix
shape used in Phase 3. Also needed before Phase 0.5 so the Temporal migration has a clean config
to read.

**Files modified:** `configs/agents/orchestrator.config.json`, `workflow_state_machine.py`,
`orchestrator_agent.py`

### Verification
Snapshot test: assert loaded transition graph equals today's `_TRANSITIONS` (graph equivalence,
not text comparison). Run existing pytest suite — must stay green.

### Session end — commit template
```
feat(cadf-phase-0): wire orchestrator FSM config as live source of truth

- Corrected orchestrator.config.json (added SALES_REVIEW stage + edges)
- workflow_state_machine.py now loads _TRANSITIONS from config, not hardcoded dict
- orchestrator_agent.py loads _resume_routing from same config
- Snapshot test asserts config == prior hardcoded dict
```
Then mark **Phase 0** as `[x]` in the Phase Status Tracker above and commit this file.

---

## Phase 0.5 — Migrate orchestration to Temporal + LangGraph (ADR-001 / ADR-004)

### Session start checklist
- Run `git log --oneline -5` — Phase 0 commit must be present
- Read `backend/app/services/orchestration/agent_orchestration_service.py` (the thing being replaced)
- Read `backend/app/agents/base/base_agent.py` + `agent_event_bus.py` (the asyncio substrate)
- Read `backend/app/agents/orchestrator/orchestrator_agent.py` (becomes a Temporal Workflow)
- Read `backend/app/agents/base/a2a_types.py` (types survive; execution model changes)
- Run `docker compose ps` — confirm stack is running; Temporal will be added

### What to build

This phase changes the **execution substrate** while preserving all agent reasoning logic. The
per-agent LLM calls, document handling, KYC logic, skills, and MCP calls are refactored into
LangGraph nodes — not rewritten.

#### 1. Add Temporal to docker-compose

Add `temporalio/auto-setup:latest` to `docker-compose.yml`:
```yaml
temporal:
  image: temporalio/auto-setup:latest
  ports: ["7233:7233", "8233:8233"]  # gRPC + Web UI
  environment:
    - DB=postgres12
    - POSTGRES_USER=${POSTGRES_USER}
    - POSTGRES_PWD=${POSTGRES_PASSWORD}
    - POSTGRES_SEEDS=db
  depends_on: [db]
```

#### 2. LangGraph agent graphs

Convert each `BaseAgent` subclass to a `langgraph.graph.StateGraph`. The pattern:

```python
# Before (asyncio BaseAgent):
class KYCComplianceAgent(BaseAgent):
    async def _handle_run_kyc(self, packet: TaskPacket) -> TaskResponse: ...

# After (LangGraph node):
from langgraph.graph import StateGraph, END
from app.agents.base.a2a_types import OnboardingState

def kyc_graph() -> StateGraph:
    graph = StateGraph(OnboardingState)
    graph.add_node("run_kyc", run_kyc_node)          # existing _handle_run_kyc logic
    graph.add_node("verify_identity", verify_identity_node)
    graph.add_node("signal_outcome", signal_outcome_node)
    graph.add_edge("run_kyc", "verify_identity")
    graph.add_conditional_edges("verify_identity", route_by_risk, {...})
    graph.set_entry_point("run_kyc")
    return graph.compile()
```

`OnboardingState` (from Phase 2's typed core) maps directly to LangGraph's `TypedDict` state.
Each node function receives and returns an `OnboardingState` partial — no more `TaskPacket`
passing between agents. Inter-agent "messages" become Temporal Signals.

#### 3. Temporal Workflow (Orchestrator)

```python
# backend/app/workflows/onboarding_workflow.py
from temporalio import workflow, activity
from app.domain.domain_definition import DomainDefinition

@workflow.defn
class OnboardingWorkflow:
    @workflow.run
    async def run(self, input: OnboardingWorkflowInput) -> OnboardingWorkflowResult:
        state = await workflow.execute_activity(
            initialize_case_activity, input, schedule_to_close_timeout=timedelta(seconds=30)
        )
        while not state.is_terminal():
            state = await self._dispatch_stage(state)
        return OnboardingWorkflowResult(final_stage=state.stage)

    async def _dispatch_stage(self, state):
        # Reads StageActionSpec from DomainDefinition (Phase 1/3 concept, now a Workflow step)
        ...
```

`AgentEventBus` asyncio queue → **Temporal Signal** for inter-agent messages (durable, survives
restarts). `ContextStoreService` blackboard → LangGraph `State` schema + Temporal side-effect DB
persistence (the existing `ContextStoreService.update_state()` logic becomes a Temporal Activity).

#### 4. Temporal worker registration

Replace `_build_agents()` in `agent_orchestration_service.py` with Temporal worker startup:

```python
from temporalio.client import Client
from temporalio.worker import Worker

async def start(self):
    self._temporal_client = await Client.connect("localhost:7233")
    self._worker = Worker(
        self._temporal_client,
        task_queue="onboarding",
        workflows=[OnboardingWorkflow],
        activities=get_all_activities(),  # one activity per old agent handler method
    )
    await self._worker.run()
```

#### 5. ADR-009 and ADR-010

Write `docs/specs/ADR-009_temporal_langgraph_adoption.md`:
- Decision: adopt self-hosted Temporal (ADR-001) and LangGraph (ADR-004)
- Rationale: durable execution, crash recovery, built-in retry/timeout, ADR conformance
- Python-first: JVM core deferred until polyglot adds value beyond Python capabilities
- Self-hosted (not Temporal Cloud): data residency + BSA compliance + cost

Write `docs/specs/ADR-010_single_tenant_deployment.md`:
- Decision: single-tenant per deployment; no runtime domain-switching
- Rationale: simpler security boundary; proven by Retail/Deposit parallel deployment in Phase 11

**Files (new):** `backend/app/workflows/onboarding_workflow.py`, all agent graphs under
`backend/app/agents/*/graph.py`, `docs/specs/ADR-009_*.md`, `docs/specs/ADR-010_*.md`

**Files (modified):** `agent_orchestration_service.py`, `docker-compose.yml`, `main.py`,
`a2a_types.py` (add LangGraph-compatible TypedDict state), `requirements.txt`/`pyproject.toml`

**Libraries to add:** `temporalio`, `langgraph`, `langchain-core`

### Verification
- `docker compose up temporal` starts without error; Temporal Web UI reachable at `:8233`
- Run an end-to-end onboarding case through the new Temporal workflow — same stage transitions,
  same final state as before migration
- Kill the worker mid-workflow, restart it — workflow resumes from the last checkpoint (this is
  the key Temporal durability proof that asyncio cannot provide)
- All existing pytest integration tests pass against the new substrate

### Session end — commit template
```
feat(cadf-phase-0.5): migrate orchestration to Temporal + LangGraph (ADR-001/ADR-004)

- Temporal self-hosted added to docker-compose
- OnboardingWorkflow: Temporal @workflow.defn replaces asyncio OrchestratorAgent
- All 9 BaseAgent subclasses converted to LangGraph StateGraph nodes
- AgentEventBus asyncio queue replaced by Temporal Signals
- ContextStoreService blackboard persistence wired as Temporal Activities
- ADR-009: Temporal + LangGraph adoption documented
- ADR-010: single-tenant deployment model documented
- Worker crash-recovery verified: workflow resumes from last checkpoint
```
Then mark **Phase 0.5** as `[x]` in the Phase Status Tracker above and commit this file.

### Known debt from Phase 0.5 (clean up before Phase 2)

The LangGraph migration left old `process()` method bodies in the pre-Temporal agent classes.
These paths are no longer reachable from Temporal workflows (the graphs call internal helpers
directly, not `process()`), but the classes still exist and their `process()` methods contain
`asyncio.create_task` calls that were correct under the old asyncio substrate:

| File | Dead asyncio.create_task call sites | Why unreachable |
|---|---|---|
| `agents/kyc_compliance/kyc_compliance_agent.py:204–213` | `_update_stage`, `_notify_kyc_outcome`, `compliance_decision_logger` | `_run_kyc_node` calls `_simulate_identity_verification` + `_persist_agent_task` directly; `process()` is never invoked from the graph |
| `agents/orchestrator/orchestrator_agent.py:283,353,444` | `_persist_case_stage`, `_route_to_stage` fire-and-forget | `OrchestratorAgent.process()` is not called by any Temporal workflow or activity |

**What to do in Phase 2:** Before restructuring `OnboardingState`, audit every call site of
`OrchestratorAgent` and `KYCComplianceAgent.process()` (check `journey_resumption_service.py`
and `conversation_coordinator.py`). If those call sites have been migrated to Temporal Signals,
delete the old `process()` method bodies and any `asyncio.create_task` calls within them.
Do not delete the classes — the LangGraph graphs still instantiate them for helper methods.

---

## Phase 1 — Design the DB-backed DomainDefinition model

### Session start checklist
- Run `git log --oneline -5` — Phase 0.5 commit must be present
- Read `backend/app/agents/base/a2a_types.py` (AgentID, TaskType, OnboardingStage enums to generalize)
- Read `backend/app/services/orchestration/agent_orchestration_service.py` (`_build_agents` replacement)
- Read `backend/app/domain/` — should not exist yet; you are creating it
- Read `db/schema/` to understand existing migration numbering

### What to build
Introduce the complete set of `domain_*` tables that the admin portal (Phase 9) will sit on
top of. This is the most consequential design phase — get the schema right before building on it.

**New tables:**

| Table | Purpose |
|---|---|
| `domains` | One row per deployed domain (`domain_id`, `domain_code`, `display_name`, `is_active`) |
| `domain_stages` | Stages for a domain (`domain_id`, `stage_code`, `display_name`, `is_terminal`, `is_human_pending`) |
| `domain_transitions` | Valid FSM edges (`domain_id`, `from_stage`, `to_stage`) |
| `domain_task_routing` | What the orchestrator emits on stage entry (`domain_id`, `stage_code`, `target_agent`, `task_type`, `priority`, `payload_template`, `notification_templates JSONB`) |
| `domain_agent_roster` | Which agent classes participate in a domain (`domain_id`, `agent_id`, `agent_class`) |
| `domain_agent_capabilities` | Entry + exit contracts per agent (`domain_id`, `agent_id`, `subscribed_task_types TEXT[]`, `emitted_task_types TEXT[]`, `allowed_handoff_targets TEXT[]`) |
| `domain_product_pipelines` | Step sequence executed by each product's agent instance (`domain_id`, `product_code`, `step_id`, `step_label`, `step_order`, `is_parallel bool`, `step_config JSONB`) |
| `domain_agent_prompts` | Per-agent system prompts, domain-scoped (`domain_id`, `agent_id`, `prompt_role`, `prompt_text`) |
| `domain_agent_skills` | Skill bindings per agent (`domain_id`, `agent_id`, `skill_id`, `bound_parameters JSONB`) |
| `domain_agent_tool_grants` | MCP tool least-privilege grants (`domain_id`, `agent_id`, `connector_id`, `tool_name`) |
| `domain_stage_slas` | SLA config — multi-axis key: `(domain_id, stage_code, priority_tier nullable, product_code nullable)`. Fields: `is_enabled bool default true`, `window_hours numeric`, `warning_pct int default 80`, `escalation_pct int default 100`, `warning_task_type`, `escalation_task_type`, `escalation_target_agent`, `pause_on_human_review bool`. CHECK: `warning_pct < escalation_pct` |
| `domain_personas` | Configurable roles (`domain_id`, `persona_code`, `display_label`, `color`, `default_route`, `nav_links JSONB`) |
| `domain_permissions` | Permission grants per persona (`domain_id`, `persona_code`, `permission_scope`) |
| `domain_products` | Product catalog (`domain_id`, `product_code`, generalizes existing `products` table) |
| `domain_display_config` | Stage/persona display metadata for the frontend (`domain_id`, `entity_type`, `entity_code`, `label`, `color`, `style JSONB`) |

**New code:**
- `backend/app/domain/domain_definition.py` — Pydantic model of a fully-loaded domain;
  `DomainDefinitionLoader.load(domain_id)` reads all tables and validates the in-memory
  contract (fail fast on: dangling transition edges, pipeline steps referencing undefined agents,
  SLA rows referencing undefined stages, `warning_pct >= escalation_pct`)
- Generalize `AgentID`/`TaskType`/`OnboardingStage` from fixed `StrEnum`s to plain validated
  strings checked against the loaded domain's vocabulary
- Seed script: migrate the corrected Phase-0 config into `domain_*` rows for the wealth domain

**Modified:** `a2a_types.py`, `agent_orchestration_service.py` (pass `DomainDefinition` to Temporal
worker construction rather than hardcoded list)

### Verification
Round-trip test: seed wealth-domain rows → load via `DomainDefinitionLoader` → assert result
matches the corrected Phase-0 config exactly. Contract validation must reject: orphan stage,
unreachable terminal, SLA row referencing undefined stage, `warning_pct >= escalation_pct`.
Existing pytest suite stays green.

### Session end — commit template
```
feat(cadf-phase-1): add DomainDefinition model, domain_* tables, and wealth seed rows

- domain_* migrations (stages, transitions, routing, roster, capabilities, pipelines,
  prompts, skills, tool_grants, slas, personas, permissions, products, display_config)
- DomainDefinitionLoader with Pydantic contract validation
- Wealth domain seed rows migrated from corrected Phase-0 config
- a2a_types.py: AgentID/TaskType/OnboardingStage generalized to validated strings
```
Mark **Phase 1** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 2 — Split OnboardingState into typed core + extension bag

### Session start checklist
- Run `git log --oneline -5` — Phase 1 commit must be present
- Read `backend/app/agents/base/a2a_types.py` (OnboardingState model — the thing being split)
- Read `backend/app/services/context_store/context_store_service.py` (blackboard)
- Grep `backend/app/agents/` for direct field accesses to `kyc_status`, `kyc_risk_score`,
  `sales_review_decision`, `escalation_reason`, `human_review_id`, `sales_review_id`

> **Phase 0.5 trace-fix guard:** `OnboardingStateDict` contains two internal Temporal routing
> keys — `_product_code: str` and `_product_track_status: str` — added by the Phase 0.5 trace
> fix. These are NOT wealth-domain extension fields. Keep them in the **typed core** of
> `OnboardingStateDict`; do NOT move them into the `extra` JSONB bag. Temporal's payload codec
> strips undeclared TypedDict keys — if these keys are removed or moved to `extra`, the
> `_onboard_product_node` will silently receive an empty `_product_code` and produce no trace.

### What to build
Restructure `OnboardingState` into:
- **Generic typed core**: `case_id`, `client_id`, `stage: str`, `selected_products`,
  `product_tracks`, `priority_tier: str` *(new — needed for SLA window selection in Phase 5)*,
  `version`, timestamps, `_product_code`, `_product_track_status` *(Temporal routing hints —
  keep in typed core, see guard note above)*
- **Extension bag**: `extra: dict[str, Any]` backed by existing `shared_context JSONB` column
- **Typed extension view helpers**: `WealthExtension.from_state(state)` — zero behavior change,
  just a typed accessor layer
- **LangGraph TypedDict alias**: `OnboardingStateDict = TypedDict(...)` mirroring the Pydantic
  model — used as LangGraph graph state type (Phase 0.5 nodes accept this type)

**Order of operations:**
1. Write characterization tests (request/response/state snapshots) *before* touching the model
2. Convert all grepped call sites to `state.extra["..."]` / typed accessors
3. Audit `orchestrator_agent.py` / Temporal workflow for in-place mutation bypassing
   `ContextStoreService.update_state()` — would silently break optimistic locking
4. Change the model

**Migration:** add `priority_tier varchar default 'standard'` to `onboarding_cases`

### Verification
Re-run characterization tests taken in step 1 — diff must be empty. Existing suite green.

### Session end — commit template
```
feat(cadf-phase-2): split OnboardingState into typed core + extension bag

- OnboardingState: generic core fields + extra JSONB bag
- WealthExtension typed accessor helpers
- OnboardingStateDict TypedDict for LangGraph graph state compatibility
- All wealth agents converted to typed accessors
- Characterization snapshot tests added
- Migration: priority_tier added to onboarding_cases
```
Mark **Phase 2** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 2.5 — Hash-chain audit log (FR-AU-01 / BSA compliance)

### Session start checklist
- Run `git log --oneline -5` — Phase 2 commit must be present
- Read `backend/app/models/agents.py:72-90` (EventLog — the existing event store)
- Read `backend/app/services/audit/audit_log_service.py` (current audit logging)
- Read `backend/app/api/routers/audit.py` (existing audit endpoints to extend)

### What to build

**Why this phase exists:** FR-AU-01 requires an immutable, tamper-evident, hash-chained decision
log. The current `EventLog` table is mutable and has no hash chain. BSA 5-year/WORM retention and
"explainability for every automated decision" (FR-AU-03) both depend on tamper-evidence.

#### 1. New `decision_log` table (append-only)

```sql
CREATE TABLE decision_log (
    seq          BIGSERIAL PRIMARY KEY,
    case_id      UUID REFERENCES onboarding_cases(id),
    client_id    UUID REFERENCES clients(id),
    agent_id     TEXT NOT NULL,
    event_type   TEXT NOT NULL,           -- mirrors AuditEventType
    payload      JSONB NOT NULL,          -- inputs + rationale + outputs
    payload_hash TEXT NOT NULL,           -- SHA-256 of payload
    prev_hash    TEXT NOT NULL,           -- SHA-256 of previous row's payload_hash (genesis = '0'*64)
    chain_hash   TEXT NOT NULL,           -- SHA-256(prev_hash || payload_hash)
    is_compliance_event BOOL DEFAULT FALSE,
    is_regulatory_breach BOOL DEFAULT FALSE,  -- set only on SLA breach / ECOA / BSA events
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
-- No UPDATE or DELETE grants on this table. WORM semantics enforced at app layer + DB role.
```

**No UPDATE/DELETE** — enforce at DB level by revoking those privileges from the app role.

#### 2. `DecisionLogService` (new)

```python
class DecisionLogService:
    async def append(self, entry: DecisionLogEntry) -> None:
        last = await self._get_last_hash()  # SELECT chain_hash ORDER BY seq DESC LIMIT 1
        payload_hash = sha256(entry.payload_json)
        chain_hash = sha256(last + payload_hash)
        await session.execute(INSERT INTO decision_log ...)
```

Every agent action and compliance event calls `DecisionLogService.append()` — this is the
authoritative audit trail. `EventLog` remains for operational telemetry.

#### 3. New API endpoints

- `GET /audit/verify` — walks the entire chain; returns `{valid: bool, total: int, broken_at_seq: int | null}`
- `GET /cases/{id}/audit` — paginated, exportable decision log for a case with chain hashes visible
- `GET /audit/export` — BSA-compliant CSV/JSON export (compliance officer use)

#### 4. Audit event types for new phases

Add to `audit_event_types.py`:
- `SLA_WARNING`, `SLA_BREACH` (used in Phase 5)
- `PRODUCT_ACTIVATED`, `PRODUCT_DECLINED` (used in Phase 4.6)
- `FRAUD_FLAGGED`, `FRAUD_CLEARED` (used in Phase 4.6)
- `DOCUMENT_SCOPE_ASSIGNED` (used in Phase 4.5)
- `CONFIG_CHANGE` (used in Phase 9 admin portal)

#### 5. `is_regulatory_breach` field on EventLog

Add `is_regulatory_breach bool default false` to `EventLog` (migration). Set on:
- SLA escalation-threshold breach (Phase 5)
- Adverse-action decline (Phase 4.6)
- BSA/FinCEN-reportable events

**Files (new):** migration for `decision_log`, `backend/app/services/audit/decision_log_service.py`
**Files (modified):** `audit_log_service.py`, `audit.py` (router), `audit_event_types.py`,
`models/agents.py` (`is_regulatory_breach` field)

### Verification
- Insert 10 decision log entries; `GET /audit/verify` returns `{valid: true, total: 10}`
- Manually corrupt a row's `chain_hash`; `GET /audit/verify` returns `{valid: false, broken_at_seq: N}`
- Attempt `UPDATE decision_log` as the app DB user — must be rejected (permission denied)
- Existing suite green

### Session end — commit template
```
feat(cadf-phase-2.5): hash-chain audit log for FR-AU-01 BSA compliance

- decision_log table: append-only, SHA-256 hash chain, WORM semantics
- DecisionLogService: append() with chain validation
- GET /audit/verify endpoint (tamper detection)
- GET /cases/{id}/audit + GET /audit/export endpoints
- EventLog.is_regulatory_breach field added
- New AuditEventType values: SLA_WARNING, SLA_BREACH, PRODUCT_ACTIVATED, etc.
- Integration test: chain valid, corrupt row → chain broken, UPDATE rejected
```
Mark **Phase 2.5** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 3 — Replace if/elif stage routing with a config-driven StageDispatcher ✅ Done

### As-built summary (2026-06-15)

`backend/app/services/orchestration/stage_dispatcher.py` (new) — replaces the hardcoded
~150-line if/elif chain in `orchestrator_agent.py` and the equivalent stage-dispatch logic in
`onboarding_workflow.py`.

**Key design decision (sandbox-safe raw dicts):** `StageDispatcher` intentionally works with
plain `dict` internally — not with `DomainDefinition` Pydantic objects — so that
`OnboardingWorkflow` can construct it from the raw dict returned by
`load_domain_definition_activity` without importing `domain_definition.py` (which imports
SQLAlchemy) inside the Temporal workflow sandbox.

```
StageDispatcher.from_domain_dict(data)  ← workflow code (no SQLAlchemy import)
StageDispatcher.from_domain_def(domain_def)  ← test / non-sandbox code
```

**Temporal sandbox passthrough issue (discovered during implementation):** importing
`stage_dispatcher` from `app.services.orchestration` triggers `__init__.py` →
`journey_resumption_service` → `app.database` → `app.config` → `Settings()` →
`pydantic_settings` → `Path.expanduser()`, which the sandbox restricts.  Fixed by adding
`"app.services.orchestration"` to `SandboxRestrictions.default.with_passthrough_modules(...)` in
`agent_orchestration_service.py`.  `stage_dispatcher.py` is pure deterministic Python — no I/O —
so passing the whole package through is safe.

**`_TASK_TYPE_TO_ACTIVITY_NAME` registry** — module-level dict mapping `task_type` values from
`domain_task_routing` to `@activity.defn` name strings.  Adding a new task type in a future phase
requires only one registry entry; no workflow routing code changes.

**`_ACTIVITY_LOOKUP`** — module-level dict in `onboarding_workflow.py` mapping activity name
strings to callable references.  Stage handlers use this to invoke the config-selected activity
with a hardcoded fallback if dispatch returns `None`.

**`SLAHook.on_stage_entered(case_id, stage_code, domain_def)`** — synchronous no-op stub called
at the top of every `_handle_*` method.  Phase 5 activates the real Temporal Timer; the stub is
safe to call when `case_sla_tracking` does not yet exist.

**`load_domain_definition_activity`** — Temporal activity that loads `DomainDefinition` from DB
once at workflow start and returns `model_dump()`.  On replay the stored history result is
returned; the DB is never re-queried — determinism preserved.

**`domain_code: str = "wealth_management"`** — added to `OnboardingWorkflowInput` (backward-
compatible default).

**21 snapshot tests** in `backend/tests/unit/services/test_stage_dispatcher.py` assert that
`StageDispatcher.resolve(stage_code)` returns the same activity name the old if/elif routing
produced for every wealth-domain stage.

### Files changed
- **New:** `backend/app/services/orchestration/stage_dispatcher.py`
- **New:** `backend/tests/unit/services/test_stage_dispatcher.py`
- **Modified:** `backend/app/workflows/onboarding_workflow.py` (StageDispatcher + SLAHook wired; `load_domain_definition_activity` added)
- **Modified:** `backend/app/agents/base/a2a_types.py` (`domain_code` field)
- **Modified:** `backend/app/services/orchestration/agent_orchestration_service.py` (sandbox passthrough)
- **Modified:** `docs/FRAMEWORK.md`, `docs/TRACEABILITY.md`, `docs/planning/cadf-framework-plan.md`

### Session start checklist (for reference — phase is complete)
- Run `git log --oneline -5` — Phase 2.5 commit must be present
- Read `backend/app/workflows/onboarding_workflow.py` (the Temporal workflow from Phase 0.5)
- Read `backend/app/domain/domain_definition.py` (the `DomainDefinition` model to source from)

---

## Phase 4 — Make products, questions, and per-product agent pipelines config-driven ✅ Done

### As-built summary (2026-06-15)

**Migration 0017** (`backend/alembic/versions/0017_product_pipeline_seed.py`) seeds
`domain_product_pipelines` for all 6 wealth products and populates
`domain_products.suitability_criteria` JSONB for all products.  `down_revision = "0016_decision_log"`.

**`step_config` shape** (per pipeline row): `{"min_ms": N, "max_ms": M}` — latency bounds
passed to `_execute_step()` for configurable simulation timing.

**`suitability_criteria` shape** (per product row): full threshold + lookup-map dict:
`min_risk_level`, `min_age`, `min_income`, `ideal_horizons`, `is_retirement_account`,
`scoring_weights`, `risk_capacity_map`, `objective_to_risk`, `objective_to_horizon`,
`income_range_to_float`.  Any missing key falls back to the module-level constant.

**`SuitabilityAssessor`** (`suitability_assessor.py`):
- Added `assess_with_criteria(product_code, client_data, criteria)` — DB-driven path
- Refactored `assess()` to delegate to shared private `_score()` method
- `assess_with_criteria()` also delegates to `_score()` — guarantees score parity

**`ProductOnboardingAgent`** (`product_onboarding_agent.py`):
- `_load_pipeline_from_db(product_code)` — queries `domain_product_pipelines`; returns `None` on miss
- `_load_suitability_criteria_from_db(product_code)` — queries `domain_products.suitability_criteria`; returns `None` on miss
- `_handle_onboard()` tries DB path first; falls back to hardcoded constants silently
- `_execute_step()` accepts `step_config` kwarg with `min_ms`/`max_ms`; falls back to `_STEP_DURATIONS_MS`

**`graph.py`** (`agents/product_onboarding/graph.py`):
- `_validate_agent_entry(task_type)` — soft check against `domain_agent_capabilities` rows;
  logs a warning if task type not found; wrapped in try/except, never blocks execution
- `_onboard_product_node()` calls `_validate_agent_entry` then sets `_named_agent = f"product_onboarding[{product_code}]"`
- Named agent used in socket events, `AgentTask.to_agent` trace field, and log messages

**22 unit tests** in `backend/tests/unit/agents/test_product_pipeline_config.py`:
- 8 parametrized snapshot-parity tests (`assess_with_criteria == assess` for 4 client profiles × 2 products)
- 6 threshold-enforcement tests (min_risk, min_income, min_age, ideal_horizons, retirement bonus, custom weights)
- 4 hardcoded fallback shape tests (step lists match migration data)
- 4 backward-compat tests (`assess()` returns correct outcomes)

**Domain code defaulting:** `_load_pipeline_from_db` and `_load_suitability_criteria_from_db`
default `domain_code="wealth_management"` since `OnboardingStateDict` does not carry it
(consistent with ADR-010 single-tenant deployment).

### Files changed
- **New:** `backend/alembic/versions/0017_product_pipeline_seed.py`
- **New:** `backend/tests/unit/agents/test_product_pipeline_config.py`
- **Modified:** `backend/app/agents/product_onboarding/suitability_assessor.py` (`assess_with_criteria`, `_score` refactor)
- **Modified:** `backend/app/agents/product_onboarding/product_onboarding_agent.py` (DB loaders, fallback logic, step_config)
- **Modified:** `backend/app/agents/product_onboarding/graph.py` (capability validation, named trace)
- **Modified:** `docs/FRAMEWORK.md`, `docs/TRACEABILITY.md`, `docs/planning/cadf-framework-plan.md`

### Session start checklist
- Run `git log --oneline -5` — Phase 3 commit must be present
- Read `backend/app/agents/product_onboarding/product_onboarding_agent.py:95-140`
- Read `backend/app/agents/product_onboarding/suitability_assessor.py:15-85`
- Read `backend/app/services/orchestration/agent_orchestration_service.py` (`_build_agents`)

> **Note:** Phase 4 and Phase 5 are independent and can be worked in parallel.

### What to build

**(a) Finish wiring Product.step_sequence / suitability_criteria / OnboardingQuestion.product_id**

Move hardcoded `_PRODUCT_STEPS`, `_RISK_CAPACITY_MAP`, `_PRODUCT_MIN_RISK/AGE/INCOME`, and
scoring weights into the JSONB columns that already exist. Define typed JSON schemas.
Make `ProductOnboardingAgent` LangGraph graph and `SuitabilityAssessor` read from DB rows.

**(b) Declarative agent entry/exit contracts via `domain_agent_capabilities`**

Migrate each agent's LangGraph graph to declare its subscribed task types and allowed handoffs
via `domain_agent_capabilities` rows. The graph's entry node validates the incoming task type
against the capability spec. Exit nodes validate their handoff target before emitting a Temporal
Signal.

**(c) Per-product named agent instances**

`ParallelProductLauncher` spawns one Temporal child workflow per selected product, each running
the same `ProductOnboardingWorkflow` but with a different `product_code` context. Each child
workflow's Temporal workflow ID includes the product code:
`onboarding-{case_id}-product-{product_code}`. The Temporal Web UI displays a distinct entry for
each product's workflow execution. Agent trace screen shows distinct `ProductOnboardingAgent[{product_code}]` entries.

**Files modified:** `product_onboarding_agent.py` (LangGraph graph), `suitability_assessor.py`,
`parallel_product_launcher.py`, `agent_orchestration_service.py`, all agent LangGraph graphs

### Verification
Snapshot-compare suitability scores and step sequences before/after. Agent trace records must
show `ProductOnboardingAgent[{product_code}]` for each selected product. Temporal Web UI shows
distinct child workflows per product. Existing suite green.

### Session end — commit template
```
feat(cadf-phase-4): make products, questions, and per-product agent instances config-driven

- Product.step_sequence and suitability_criteria JSONB now live source of truth
- SuitabilityAssessor reads thresholds/weights from DB
- AgentCapabilitySpec wired through domain_agent_capabilities rows
- ParallelProductLauncher spawns Temporal child workflows per product
- Named instances: ProductOnboardingAgent[{product_code}] in workflow IDs + trace
```
Mark **Phase 4** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 4.5 — Shared-core document taxonomy (FR-DM-01/02/03)

### Session start checklist
- Run `git log --oneline -5` — Phase 4 commit must be present (or Phase 3 if working in parallel)
- Read `backend/app/models/documents.py` (Document model — adding `scope` field)
- Read `backend/app/api/routers/documents.py` (existing document endpoints)
- Read `backend/app/models/cases.py` (Product model — adding `required_documents_scope`)

### What to build

**Why this phase exists:** FR-DM-01/02/03 require that shared-core documents (Government ID,
utility bill, etc.) are collected **once** and reused across all products that require them.
Currently documents have no scope taxonomy, so each product independently requests the same
documents — violating the BRD's core "collect once, reuse many" principle.

#### 1. Document scope taxonomy

Add `scope` enum field to `Document` model:
- `SHARED_CORE` — collected once; satisfies all products that require this document type
- `PRODUCT_SPECIFIC` — required by exactly one product; not reused

Add `shared_core_types TEXT[]` to `domain_products` table (list of document types that are
shared-core for this domain).

#### 2. Document requirements API

New endpoint: `GET /cases/{id}/requirements`

Returns:
```json
{
  "shared_core": [
    {
      "document_type": "GOVT_PHOTO_ID",
      "label": "Government-issued photo ID",
      "required_by_products": ["equity_fund", "savings_account"],
      "status": "VALIDATED",
      "document_id": "uuid-or-null"
    }
  ],
  "product_specific": [
    {
      "product_code": "equity_fund",
      "document_type": "INVESTMENT_MANDATE",
      "status": "PENDING",
      "document_id": null
    }
  ]
}
```

#### 3. Collect-once enforcement in DocumentIntelligenceAgent

When a SHARED_CORE document is validated for one product track, the agent marks it as satisfying
all product tracks that require it — no re-request. This is enforced at the LangGraph graph node
level: `check_existing_shared_docs` node runs before any document request.

#### 4. Frontend: DocumentCenter collect-once view

Add `frontend/src/features/client/DocumentRequirementsCenter.tsx`:
- Groups documents by scope (Shared / Product-specific)
- Shows which products each shared doc satisfies
- Single upload button per document — not one per product
- Upload satisfies all listed products simultaneously

**Files (new):** migration for `document.scope`, `DocumentRequirementsCenter.tsx`
**Files (modified):** `models/documents.py`, `documents.py` router, `document_intelligence_agent.py`
LangGraph graph, `domain_products` migration

### Verification
- Upload a GOVT_PHOTO_ID — it appears as `VALIDATED` in the requirements view under all products
  that require it; no duplicate upload prompt
- `GET /cases/{id}/requirements` returns correct `required_by_products` list for shared docs
- Product-specific doc upload does not affect other products' requirements status
- Existing suite green

### Session end — commit template
```
feat(cadf-phase-4.5): shared-core document taxonomy for collect-once reuse

- Document.scope: SHARED_CORE vs PRODUCT_SPECIFIC
- GET /cases/{id}/requirements endpoint with collect-once reuse map
- DocumentIntelligenceAgent: shared-core docs satisfy all products requiring them
- Frontend: DocumentRequirementsCenter shows collect-once view
- decision_log entries for DOCUMENT_SCOPE_ASSIGNED events
```
Mark **Phase 4.5** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 4.6 — First-to-complete activation gate (FR-GL-01/02/03) ✅ Done

### As-built summary (2026-06-16)

**Migration 0018** (`backend/alembic/versions/0018_product_activation.py`) adds the
`product_activation` table with per-product state machine
(`PENDING → CRITERIA_MET → ACTIVATED | DECLINED`) and ECOA adverse-action fields.

**`ProductActivation`** ORM model (`backend/app/models/activation.py`).
`OnboardingCase` gains a `product_activations` relationship.

**`ActivationGateService`** (`backend/app/services/activation/activation_gate_service.py`):
- `evaluate(case_id, product_code, track_status)` — strong-consistency DB read of
  `OnboardingCase.shared_context` (ADR-006), loads `domain_products.activation_criteria`
  JSONB, delegates to `_evaluate_policy()`.
- `_evaluate_policy(case_context, activation_criteria, track_status)` — pure Python function
  that mirrors `policies/activation.rego`; evaluates pipeline status, KYC gate, fraud gate,
  and optional `min_risk_level` criteria; returns `(allow, decline_reason, is_adverse_action)`.
- On ACTIVATED: upserts `product_activation` row, provisions account number
  (`GG-{product[:3].upper()}-{uuid[:8].upper()}`), appends `PRODUCT_ACTIVATED` to
  `decision_log` (`is_compliance_event=True`).
- On DECLINED: sets `is_adverse_action=True` for credit products (ECOA FR-AU-04);
  `is_regulatory_breach=True` in `decision_log`.

**`FraudScreeningAgent`** (`backend/app/agents/fraud_screening/graph.py`):
- Single `fraud_screening` LangGraph node; simulates velocity / synthetic-identity /
  tamper-detection scores; threshold = 0.85.
- Sets `extra["fraud_screened"] = "FLAGGED"|"CLEARED"`.
- On FLAGGED: sets `extra["escalation_reason"]`, `next_stage = "ESCALATED"`, writes
  `FRAUD_FLAGGED` to `decision_log` (`is_compliance_event=True`), emits socket event.

**Concurrent KYC + fraud screening** (`backend/app/workflows/onboarding_workflow.py`):
- `fraud_screening_activity` Temporal activity added, registered in `get_all_activities()`.
- `_handle_kyc` now runs both activities via `asyncio.gather`; merges `fraud_screened` flag
  into KYC result's `extra` bag; if `fraud_screened == "FLAGGED"` overrides `next_stage` to
  `"ESCALATED"` regardless of KYC outcome.

**Product onboarding graph restructured** (`backend/app/agents/product_onboarding/graph.py`):
- Graph topology: `onboard_product → activation_gate → END`
- `_onboard_product_node` — pipeline execution (Phase 4); trace write removed.
- `_activation_gate_node` — calls `ActivationGateService.evaluate()`; emits socket event with
  activation result; writes direct `AgentTask` trace (Phase 0.5 guard: trace write is always in
  the terminal node); updates `product_tracks[product_code]` with `activation_state` and
  `account_number`.

**OPA policy** (`policies/activation.rego`) — documents the activation logic; can be deployed
to an external OPA server in production; the Python in-process evaluator mirrors it exactly.

**API** (`backend/app/api/routers/cases.py`):
- `ProductTrackOut` extended with `activation_state` (default `"PENDING"`) and
  `account_number` fields.
- `ProductActivationOut` Pydantic schema added.
- `GET /cases/{id}/product-activations` — returns all `product_activation` rows for a case.
- `get_case_summary` loads activation state via `product_activation` join and passes
  activation map to `_build_product_track`.

**Frontend** (`frontend/src`):
- `ProductTrack` interface extended with `activation_state` and `account_number`.
- `ProductActivation` interface added to `api.ts`.
- `ParallelProductTracks.tsx` shows per-product activation badge (ACTIVATED/DECLINED/PENDING)
  and "First Live" highlight on the first product to reach ACTIVATED state.

**13 unit tests** in `backend/tests/unit/services/test_activation_gate.py`:
- Pipeline incomplete / UNSUITABLE → DECLINED
- KYC not passed / PENDING → DECLINED
- Fraud flagged → DECLINED (not adverse_action)
- All criteria clear → ACTIVATED
- `min_risk_level` below / meets threshold → DECLINED / ACTIVATED
- Credit product KYC decline → `is_adverse_action=True`
- Non-credit decline → `is_adverse_action=False`
- Service exposes no `delete` / `update` method (WORM)

### Files changed
- **New:** `backend/alembic/versions/0018_product_activation.py`
- **New:** `backend/app/models/activation.py`
- **New:** `backend/app/services/activation/__init__.py`
- **New:** `backend/app/services/activation/activation_gate_service.py`
- **New:** `backend/app/agents/fraud_screening/__init__.py`
- **New:** `backend/app/agents/fraud_screening/graph.py`
- **New:** `policies/activation.rego`
- **New:** `backend/tests/unit/services/test_activation_gate.py`
- **Modified:** `backend/app/models/cases.py` (`product_activations` relationship on `OnboardingCase`)
- **Modified:** `backend/app/agents/product_onboarding/graph.py` (two-node graph, activation gate terminal)
- **Modified:** `backend/app/workflows/onboarding_workflow.py` (`fraud_screening_activity`, concurrent KYC)
- **Modified:** `backend/app/api/routers/cases.py` (extended schemas, product-activations endpoint)
- **Modified:** `frontend/src/lib/api.ts` (extended `ProductTrack`, new `ProductActivation` type)
- **Modified:** `frontend/src/features/advisor/ParallelProductTracks.tsx` (activation badges)
- **Modified:** `docs/FRAMEWORK.md`, `docs/TRACEABILITY.md`, `docs/planning/cadf-framework-plan.md`

### Session start checklist (for reference — phase is complete)
- Run `git log --oneline -5` — Phase 4.5 commit must be present
- Read `backend/app/agents/product_onboarding/product_onboarding_agent.py` (LangGraph graph)
- Read the `domain_agent_capabilities` rows for `product_onboarding` — understand existing exit contracts
- Read `backend/app/models/cases.py` (CaseProductStep — activation state goes here or new table)

> **Phase 0.5 trace-fix guard:** `agents/product_onboarding/graph.py` contains a direct
> `AgentTask` write with `payload={"product_code": product_code}` at the end of
> `_onboard_product_node`. This write is what makes the product_onboarding node visible in the
> trace canvas. When this phase restructures the graph into multiple nodes (adding the activation
> gate node), ensure the direct trace write stays in or moves to the **terminal node** of the
> graph — wherever execution ends after all product steps complete. Do not remove it.

### What to build

**Why this phase exists:** FR-GL-01/02/03 require that the first product to satisfy its activation
criteria goes live independently, while remaining products continue in parallel. ADR-006 requires
an OPA policy gate (or equivalent strong-consistency check) before activation. Currently there is
no formal activation gate — all products complete together.

#### 1. `product_activation` table

```sql
CREATE TABLE product_activation (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id        UUID REFERENCES onboarding_cases(id),
    product_code   TEXT NOT NULL,
    state          TEXT NOT NULL DEFAULT 'PENDING',
    -- states: PENDING | CRITERIA_MET | ACTIVATED | DECLINED
    criteria_met_at TIMESTAMPTZ,
    activated_at   TIMESTAMPTZ,
    declined_at    TIMESTAMPTZ,
    decline_reason TEXT,
    account_number TEXT,              -- populated on ACTIVATED
    is_adverse_action BOOL DEFAULT FALSE,  -- ECOA FR-AU-04
    adverse_action_reason TEXT,
    UNIQUE (case_id, product_code)
);
```

#### 2. Activation criteria check in ProductOnboardingAgent

At the end of each product's step sequence (LangGraph graph terminal node), call
`ActivationGateService.check(case_id, product_code, domain_def)`:
1. Resolve activation criteria from `domain_product_pipelines` (JSONB `activation_criteria` field)
2. Evaluate criteria against the current `OnboardingState` (strong-consistency read from DB —
   never from cache, per ADR-006)
3. If all criteria met: transition `product_activation.state` → `CRITERIA_MET`
4. Emit `PRODUCT_ACTIVATED` or `PRODUCT_DECLINED` to Temporal Orchestrator workflow via Signal

#### 3. OPA activation gate

`ActivationGateService` evaluates an OPA policy `activation.rego`:
```rego
package activation
default allow = false
allow {
    input.kyc_status == "PASSED"
    input.documents_validated == true
    not input.fraud_flagged
    # product-specific criteria from domain_product_pipelines.activation_criteria
}
```

OPA is added to `docker-compose.yml`. For simpler deployments, the policy can be evaluated
in-process (Python `opa` library) — the interface is the same.

#### 4. First-to-complete: independent activation

When a product transitions to `CRITERIA_MET`:
- Immediately provision account number (existing `AccountService.create_account()`)
- Transition to `ACTIVATED`
- Append to `decision_log` with `event_type = PRODUCT_ACTIVATED`
- Send `SEND_NOTIFICATION` to `NotificationAgent` (product-specific activation message)
- **Do not wait for other products** — their Temporal child workflows continue independently

#### 5. Fraud/Anomaly Screening Agent (FR-AG fraud)

New LangGraph agent: `FraudScreeningAgent` (graph in `backend/app/agents/fraud_screening/graph.py`)
- Runs concurrently with KYC (parallel Temporal Activities in the same workflow step)
- Scores: device fingerprint velocity, synthetic-identity signals, document tamper detection
- Sets `OnboardingState.extra["fraud_screened"]` = `CLEARED` or `FLAGGED`
- On `FLAGGED`: transitions case to ESCALATED (existing escalation path), writes
  `decision_log FRAUD_FLAGGED` with `is_compliance_event=True`
- `fraud_screened == CLEARED` is a required criterion in `activation.rego`

#### 6. Adverse-action records (FR-AU-04 / ECOA)

When a product is declined (`PRODUCT_DECLINED`):
- Set `product_activation.is_adverse_action = True`
- Set `product_activation.adverse_action_reason` (specific reason from criteria evaluation)
- Write `decision_log` entry with `is_regulatory_breach=True` if credit-related decline
- Future: generate adverse-action notice (deferred to Phase 9/10 admin portal)

#### 7. Frontend: first-to-complete UX

Update `ParallelProductTracks.tsx` and `CaseDashboard`:
- Show per-product `activation_state` badge (`PENDING` | `ACTIVATED` | `DECLINED`)
- When first product reaches `ACTIVATED`: highlight with account number, "First product live!"
- Other products continue showing progress — no UI freeze

**Files (new):** migration for `product_activation`, `backend/app/agents/fraud_screening/graph.py`,
`backend/app/services/activation/activation_gate_service.py`, OPA policy `policies/activation.rego`
**Files (modified):** `product_onboarding_agent.py` LangGraph graph (add activation gate node),
`onboarding_workflow.py` (add fraud screening parallel with KYC), `docker-compose.yml` (OPA),
frontend `ParallelProductTracks.tsx`, `CaseDashboard.tsx`

### Verification
- Product A completes all criteria → immediately activates with account number while Product B's
  workflow continues in parallel (Temporal Web UI shows both active)
- Fraud score above threshold → case ESCALATED, `fraud_screened = FLAGGED`, `decision_log` entry
- Declined product shows `DECLINED` badge with reason in frontend
- OPA gate blocks activation if `kyc_status != PASSED` (even if all other criteria met)
- `GET /audit/verify` shows chain valid after activation events
- Existing suite green

### Session end — commit template
```
feat(cadf-phase-4.6): first-to-complete activation gate and fraud screening

- product_activation table with per-product state machine
- ActivationGateService: OPA policy evaluation (strong-consistency read)
- ProductOnboardingAgent: activation gate node at graph terminal
- First-to-complete: independent activation per product; others continue
- FraudScreeningAgent: scores velocity/synthetic-identity/tamper; fraud_screened gate
- Adverse-action records on credit decline (FR-AU-04 / ECOA)
- Frontend: per-product activation badges + first-product live highlight
- decision_log entries for PRODUCT_ACTIVATED, PRODUCT_DECLINED, FRAUD_FLAGGED
```
Mark **Phase 4.6** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 5 — Configurable SLA enforcement with feature flags and per-stage parameters

### Session start checklist
- Run `git log --oneline -5` — Phase 3 commit must be present (Phase 4 not required)
- Read `backend/app/services/orchestration/agent_orchestration_service.py` (Temporal worker lifecycle)
- Read `backend/app/agents/notification/notification_agent.py` (existing escalation handler pattern)
- Read `backend/app/workflows/onboarding_workflow.py` (the Temporal workflow — SLA timer goes here)
- Read `backend/app/services/orchestration/stage_dispatcher.py` (the `SLAHook` stub from Phase 3)

> **Note:** Phase 4 and Phase 5 are independent. Both depend on Phase 3. Can be parallel.

### What to build

**`SLAMonitorService`** — in the Temporal context, SLA monitoring is implemented as a
**Temporal Timer** within the `OnboardingWorkflow`, not a polling loop. This is more reliable:

```python
@workflow.defn
class OnboardingWorkflow:
    async def _watch_sla(self, stage_code: str, window_hours: float, warning_pct: int, escalation_pct: int):
        warning_secs = window_hours * 3600 * warning_pct / 100
        breach_secs = window_hours * 3600 * escalation_pct / 100
        await workflow.sleep(timedelta(seconds=warning_secs))
        await workflow.execute_activity(send_sla_warning_activity, ...)
        await workflow.sleep(timedelta(seconds=breach_secs - warning_secs))
        await workflow.execute_activity(trigger_sla_breach_activity, ...)
```

The `SLAHook.on_stage_entered()` stub from Phase 3 starts this timer as a detached Temporal
coroutine. If the stage exits before the timer fires, the coroutine is cancelled.

For each row in `case_sla_tracking` (created by `SLAHook`):
1. Resolve the applicable `domain_stage_slas` row using priority chain
2. **If `is_enabled=false` → skip entirely**
3. Compute net elapsed (excluding paused duration for human-pending stages)
4. Warning → NotificationAgent `SLA_WARNING` task
5. Breach → Orchestrator `SLA_BREACH` → ESCALATED stage via existing escalation path
6. Log `AuditEventType.SLA_BREACH` with `is_compliance_event=True`, `is_regulatory_breach=True`

**Clock pausing** on human-review stages via `case_sla_tracking.paused_at` +
`paused_duration_seconds` fields.

**Files (new):** `backend/app/services/sla/sla_monitor_service.py` (activates the Phase 3 stub)
**Files (modified):** `onboarding_workflow.py` (add SLA timer), `notification_agent.py` LangGraph graph
(add `SLA_WARNING` node), `audit_event_types.py` (already done in Phase 2.5)

### Verification
Integration tests with `window_hours` ≈ 0.0003 (≈ 1 second):
- `is_enabled=true`, `warning_pct=70`, `escalation_pct=90` → warning fires at 70%, escalation at 90%
- `is_enabled=false` → zero events fire
- `pause_on_human_review=true` → elapsed excludes hold period
- Product-scoped `is_enabled=false` overrides domain-level `is_enabled=true`
- SLA breach writes `is_regulatory_breach=True` to `decision_log`

### Session end — commit template
```
feat(cadf-phase-5): configurable SLA enforcement with per-stage/per-product feature flags

- SLAMonitorService: Temporal Timer replaces polling loop (durable, crash-safe)
- Per-row feature flag: is_enabled=false disables monitoring for that stage/product
- Warning/escalation thresholds, clock pausing for human-review stages
- SLA breach reuses existing orchestrator escalation path
- decision_log.is_regulatory_breach set on breach events
```
Mark **Phase 5** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 6 — Wire Skills & MCP into live agent execution, made domain-configurable

### Session start checklist
- Run `git log --oneline -5` — Phases 4 and 5 commits must both be present
- Read `backend/app/agents/skills/__init__.py` (the 6 dormant skill singletons)
- Read `backend/app/agents/skills/base_skill.py` (the `invoke()` ABC)
- Read `backend/app/agents/kyc_compliance/graph.py` (the LangGraph KYC graph — find `_simulate_*` calls)
- Read `backend/app/mcp/mcp_connector.py` (MCPRegistry — the gateway to route through)
- Read `backend/app/services/validation/prompt_override_store.py`

### What to build

**Skills:** Replace each agent graph node's inline reasoning/extraction logic with `skill.invoke(...)` calls, bindings read from `domain_agent_skills` rows. No agent knows at code time which skill it calls — the binding is data.

**MCP:** Replace `_simulate_identity_verification()` and all `_simulate_*` methods with
`mcp_registry.invoke(tool, ...)`. Add grant-checking to `MCPRegistry.invoke()`: look up
`domain_agent_tool_grants` — if the calling agent is not granted the tool, raise a loud error
and fail closed (not just log). This enforces ADR-007.

**Prompts:** Extend `prompt_override_store` from validation-prompt scope to all agent system
prompts, keyed by `(domain_id, agent_id, prompt_role)`.

**Files modified:** all agent LangGraph graphs with `_simulate_*` calls, `prompt_override_store.py`,
`mcp/mcp_connector.py`

### Verification
Snapshot agent decisions before/after — routing through `mcp_registry` and `skill.invoke()`
must produce equivalent outputs. An agent calling an ungranted MCP tool must raise an error.
Existing suite green.

### Session end — commit template
```
feat(cadf-phase-6): wire Skills and MCP gateway into live agent execution

- Agents now call skill.invoke() with bindings from domain_agent_skills rows
- _simulate_* methods replaced by mcp_registry.invoke() with grant-checking
- MCPRegistry.invoke() fails closed on ungranted tools (ADR-007 enforced)
- prompt_override_store generalized to all agent prompts, domain-scoped
```
Mark **Phase 6** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 7 — Replace hardcoded personas/roles with configurable persona + permission model

### Session start checklist
- Run `git log --oneline -5` — Phase 6 commit must be present
- Read `backend/app/api/routers/cases.py` (find all `require_role(...)` call sites)
- Grep `backend/app/api/routers/` for `require_role` — list every file and line
- Read `backend/alembic/versions/0010_add_sales_manager_role.py` (proof of why this phase exists)

### What to build

#### Permission catalog (framework-declared, portal-assigned)

The framework declares a fixed set of permission scopes. The portal assigns scopes to personas.

| Scope | Description |
|---|---|
| `case:read` | View cases and their status |
| `case:create` | Create new onboarding cases |
| `case:approve` | Approve case stage advancement |
| `review:read` | View review queue |
| `review:approve` | Approve/reject a compliance review |
| `review:escalate` | Escalate a review |
| `sales:review` | Access sales manager review queue |
| `sales:decide` | Approve/reject institutional product |
| `compliance:read` | View compliance checks and KYC results |
| `compliance:decide` | Make compliance decisions |
| `audit:read` | Access audit logs and decision log |
| `audit:export` | Export audit data (BSA compliance role) |
| `document:upload` | Upload documents |
| `document:validate` | Trigger document validation |
| `admin:config` | Access admin portal configuration |

Replace `require_role(...)` guards with `require_permission("scope")` throughout all routers.
Build a compatibility layer expressing existing wealth personas as `domain_personas` rows — zero
behavior change. That's the regression test for this phase.

**Security note:** include a security review confirming no persona can be configured to access
endpoints its scope should exclude. Document in `docs/specs/permission-model-security-review.md`.

**Files modified (migration):** `users.role` CHECK → `persona_code` FK
**Files modified (guards):** `cases.py`, `clients.py`, `reviews.py`, `audit.py`,
`collaboration.py`, `auth.py`

### Verification
Regression test: every existing wealth persona retains exactly its current permissions, landing
pages, and nav. `require_permission("audit:export")` rejects a persona without that scope.
Suite green.

### Session end — commit template
```
feat(cadf-phase-7): replace hardcoded role guards with configurable persona + permission model

- users.role CHECK → persona_code FK to domain_personas
- require_role() replaced by require_permission() across all routers
- Permission catalog: 15 scopes documented (see docs/specs/permission-model-security-review.md)
- Wealth personas expressed as domain_personas rows with matching scopes
```
Mark **Phase 7** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 8 — Loosen DB CHECK constraints; make domain reference rows authoritative

### Session start checklist
- Run `git log --oneline -5` — Phase 7 commit must be present
- Read `db/schema/002_onboarding_cases.sql` (the CHECK constraints to loosen)
- Read `backend/app/services/context_store/context_store_service.py`

### What to build
Replace `oc_status_chk`, `oc_stage_chk`, and `products.product_type` CHECK constraints with
application-layer validation in `ContextStoreService` validating against `domain_stages`/
`domain_product_types` reference rows. Single source of truth moves from hardcoded CHECKs to
`domain_*` tables.

**Files (new):** loosening migration
**Files (modified):** `context_store_service.py`, `models/cases.py`

### Verification
Insert a wealth case with a stage value not in the old CHECK enum — must fail at app layer but
succeed at DB layer. Valid domain stage — succeeds. Suite green.

### Session end — commit template
```
feat(cadf-phase-8): loosen DB CHECK constraints, domain reference rows now authoritative

- Dropped oc_status_chk, oc_stage_chk, product_type CHECK constraints
- ContextStoreService validates stage/product_type against domain_stages rows
```
Mark **Phase 8** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 9 — Build the Admin Portal

### Session start checklist
- Run `git log --oneline -5` — Phase 8 commit must be present
- Read `backend/app/domain/domain_definition.py` (the model the portal edits)
- Read `frontend/src/` structure to understand existing component/router patterns
- Read `docs/UX_UI_STANDARDS.md` — **all admin screens must comply with this**

### What to build
Admin-facing UI + CRUD/validation API letting a business user define a domain end-to-end.

**Backend API routers (new):**
- `api/routers/admin/domains.py` — domain CRUD + draft/validate/activate lifecycle
- `api/routers/admin/stages.py` — stage/transition graph editor
- `api/routers/admin/agents.py` — agent roster, capability, prompts, skill bindings, MCP grants;
  **agent enable/disable toggle** (APPROVED/DEPRECATED status — controls dispatch without redeploy)
- `api/routers/admin/pipelines.py` — per-product pipeline composer (validates wiring)
- `api/routers/admin/products.py` — product catalog, step sequences, suitability criteria,
  questionnaire assignment, `shared_core_types` (from Phase 4.5), `activation_criteria` (Phase 4.6)
- `api/routers/admin/sla.py` — SLA grid; rejects `warning_pct >= escalation_pct`; requires
  confirmation before disabling SLA on regulated stages
- `api/routers/admin/personas.py` — persona/permission editor (scopes from Phase 7 catalog)
- Config changes write a `CONFIG_CHANGE` entry to `decision_log` (Phase 2.5)

**Frontend (new):** `frontend/src/features/admin/*` — all screens must comply with
`docs/UX_UI_STANDARDS.md` (tokens-only, dark/light, mobile-first, axe-verified):
- Domain & FSM editor with visual transition graph
- Agent behavior editor (prompt, skill-binding, MCP tool-grant, enable/disable toggle)
- Visual per-product step sequence editor
- **SLA editor**: stage × tier × product grid; `is_enabled` toggle (requires confirmation on regulated stages)
- **SLA health dashboard**: active cases by stage — % elapsed, tier, breach/warning status
- **Document requirements editor**: shared-core vs product-specific taxonomy (Phase 4.5)
- **Activation criteria editor**: per-product criteria JSONB editor (Phase 4.6)
- Persona & permission editor; display vocabulary editor

**Draft → validate → activate lifecycle**. Config changes write `CONFIG_CHANGE` to `decision_log`.

### Verification
Portal validation tests: submit malformed domains (orphan stage, SLA `warning_pct >= escalation_pct`,
`is_enabled=false` on KYC without confirmation) — all rejected. Agent enable/disable verified to
control dispatch without code change. Suite green. axe check on all admin screens with 0 violations.

### Session end — commit template
```
feat(cadf-phase-9): admin portal for domain configuration

- CRUD + validation API for all domain_* tables
- Visual FSM editor, pipeline composer, SLA editor, persona editor
- Agent enable/disable toggle (APPROVED/DEPRECATED without redeploy)
- Document requirements + activation criteria editors
- Draft/validate/activate lifecycle with DomainDefinitionLoader
- SLA health dashboard
- All screens compliant with UX_UI_STANDARDS.md (tokens, dark/light, axe verified)
```
Mark **Phase 9** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 10 — Serve frontend vocabulary from the domain API

### Session start checklist
- Run `git log --oneline -5` — Phase 9 commit must be present
- Grep `frontend/src` for: `STAGE_LABELS`, `STAGE_STYLES`, `ALL_STAGES`, `TeamRole`,
  `ROLE_COLORS`, `NAV_LINKS`, `OnboardingStage`-shaped literals, `case_stage_changed`
  socket handlers — every hardcoded vocabulary site to replace

### What to build
Add `GET /api/config/domain` (serves `DomainDefinition` display vocabulary +
`domain_display_config` rows + document scope taxonomy + activation state labels).
Replace all hardcoded stage/persona/role display constants with a `useDomainConfig()` hook.
Static fallback (current wealth values) during rollout.

Also add SSE endpoint `GET /cases/{id}/events` for live product activation status updates,
replacing the current socket.io-based approach for product track state (retaining socket.io for
existing real-time features that are not domain-vocabulary-driven).

**Files (new):** `api/routers/domain_config.py`, `frontend/src/hooks/useDomainConfig.ts`
**Files (modified):** `CaseListTable.tsx`, `tokens.ts`, `App.tsx`, `ProtectedRoute.tsx`,
`ParallelProductTracks.tsx` (SSE-backed product activation state)

### Verification
With the wealth domain active, frontend renders identically to before. With a test domain loaded,
frontend renders that domain's vocabulary. Product activation SSE updates fire within 1s of
activation. Suite green.

### Session end — commit template
```
feat(cadf-phase-10): serve frontend vocabulary from domain config API

- GET /api/config/domain endpoint (stages, personas, document scopes, activation labels)
- useDomainConfig() hook replaces all hardcoded stage/persona display constants
- GET /cases/{id}/events SSE endpoint for live product activation status
- Static fallback preserves current behavior during rollout
```
Mark **Phase 10** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 11 — Stand up Retail/Deposit through the admin portal (the real proof)

### Session start checklist
- Run `git log --oneline -5` — Phase 10 commit must be present
- Read `docs/specs/Technical_Architecture_Client_Onboarding.docx` (Retail/Deposit section)
- Open the admin portal at the running Phase 10 deployment

### What to build
Using the admin portal — **not migration scripts** — define Retail/Deposit end-to-end. Expect
**at most one new Python agent class** (e.g. `DepositSpecialistAgent`). All wiring via portal.

### Verification — acceptance checklist
Run every item; any failure means re-visiting the indicated phase:

- [ ] Zero `domain_*`/product/pipeline/SLA/questionnaire rows for Retail/Deposit from scripts
- [ ] ≤ 1 new agent class; 0 modifications to any existing wealth agent class
- [ ] New agent wired via portal only — zero `AgentEventBus`/orchestrator/workflow code changes
- [ ] 0 changes to `a2a_types.py`, `onboarding_workflow.py`, `orchestrator_agent.py`,
      `prompt_override_store.py`, `mcp_connector.py`, `sla_monitor_service.py`,
      `require_permission` call sites for this launch
- [ ] Frontend renders Retail/Deposit vocab from `/api/config/domain`
- [ ] `priority_tier="sme"` deposit case gets a different SLA window than `priority_tier="standard"`
- [ ] Overdue test case fires `SLA_WARNING` at `warning_pct`%, auto-escalates at `escalation_pct`%,
      `is_regulatory_breach=True` in `decision_log`
- [ ] Case in `pause_on_human_review=true` stage does NOT consume SLA during hold
- [ ] "instant-account" product has SLA fully disabled — zero SLA events fire
- [ ] "deposit-ops" persona logs in with correct landing page/nav — no frontend code change
- [ ] Shared-core document (e.g. GOVT_PHOTO_ID) satisfies all Retail/Deposit products in one upload
- [ ] First Retail/Deposit product to complete activates independently; other continues in background
- [ ] Hash-chain audit explorer shows valid chain for Retail/Deposit cases
- [ ] Pipeline composer shows correct step sequence per deposit product
- [ ] Temporal Web UI shows distinct child workflows per product
- [ ] SLA health dashboard shows overdue test case correctly flagged

### Session end — commit template
```
feat(cadf-phase-11): retail/deposit domain configured through admin portal

- All domain config via portal (zero seed scripts for retail/deposit)
- DepositSpecialistAgent (if needed) — single new class, wired via portal
- Acceptance checklist passed (see docs/planning/cadf-framework-plan.md)
```
Mark **Phase 11** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 12 — Extract the framework/domain package boundary

### Session start checklist
- Run `git log --oneline -5` — Phase 11 + passing acceptance checklist must be present
- Run `grep -r "from app.agents.kyc" backend/app/framework` — should find nothing

### What to build
Draw the line between **framework** (generic infrastructure) and **domain pack** (wealth-specific).
Package restructure (`backend/app/framework/` vs `backend/app/domains/{wealth,retail_deposit}/`)
or enforced import-boundary lint rule (`flake8-import-linter`). Boundary derived from what Phase
11 proved.

### Verification
Import-boundary lint: no `framework/` imports from `domains/`; no cross-domain imports. Suite green.

### Session end — commit template
```
feat(cadf-phase-12): extract framework/domain package boundary

- backend/app/framework/ contains all generic infrastructure
- backend/app/domains/{wealth,retail_deposit}/ contain domain-specific code
- Import-boundary lint rule enforced in CI
```
Mark **Phase 12** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 13 — Observability, IaC & Operations (NFR-03 / NFR-10)

### Session start checklist
- Run `git log --oneline -5` — Phase 12 commit must be present
- Read `docs/specs/Technical_Architecture_Client_Onboarding.docx` §Deployment (dual-AZ topology)
- Read `frontend-reference-project/deploy/helm/` (Helm chart to adapt)
- Read `frontend-reference-project/scripts/ops/` (backup/restore/audit scripts to adapt)

### What to build

**OpenTelemetry instrumentation:**
- Add OTel SDK (`opentelemetry-sdk`, `opentelemetry-exporter-otlp`) to all agent Temporal Activities
- Instrument: Temporal workflow/activity spans, LLM call durations, MCP tool call latencies,
  DB query times, API request/response
- Export to OTLP collector → Tempo (traces) + Prometheus (metrics) + Loki (logs)

**Prometheus metrics:**
- Add `/metrics` endpoint (via `prometheus_client`)
- Key metrics: `onboarding_cases_active`, `stage_transition_duration_seconds`,
  `llm_call_duration_seconds`, `mcp_tool_call_total`, `sla_breach_total`, `agent_error_total`

**Observability stack (docker-compose overlay):**
```yaml
# docker-compose.observability.yml (adapt from reference project)
services:
  otel-collector: ...
  prometheus: ...
  grafana: ...    # SLO dashboards from NFR targets
  loki: ...
  tempo: ...
```

**Helm chart:**
- Adapt `frontend-reference-project/deploy/helm/` for this project's services
- Services: `backend` (FastAPI), `frontend` (nginx), `temporal`, `postgres`, `redis`
- `values-prod.yaml`: multi-replica, HPA, resource limits
- Optional ingress routing `/api` → backend, `/` → frontend, `/docs` → in-app docs

**CI/CD (GitHub Actions):**
- Adapt `frontend-reference-project/.github/workflows/ci.yml`
- Jobs: Python tests, frontend build + type-check, Docker image build, Semgrep SAST, Trivy scan
- Release: SBOM + image signing (cosign)

**DR & compliance operations:**
- Adapt `frontend-reference-project/scripts/ops/backup.sh` for PostgreSQL + MinIO
- `scripts/ops/audit_integrity_check.sh` — calls `GET /audit/verify` and alerts if chain broken
- DR failover runbook: RTO ≤ 15 min, RPO ≈ 0 (per NFR-03)

**Files (new):** `docker-compose.observability.yml`, `deploy/helm/`, `.github/workflows/ci.yml`,
`.github/workflows/release.yml`, `scripts/ops/backup.sh`, `scripts/ops/audit_integrity_check.sh`,
`docs/OPERATIONS.md`

### Verification
- `docker compose -f docker-compose.yml -f docker-compose.observability.yml up` — all services
  healthy; Grafana shows agent metrics; Tempo shows traces for an onboarding case
- `helm lint deploy/helm/` passes
- `helm template` renders correctly for dev and prod values
- `scripts/ops/audit_integrity_check.sh` reports valid chain
- `scripts/ops/backup.sh` + restore round-trip verified
- GitHub Actions CI runs green

### Session end — commit template
```
feat(cadf-phase-13): observability, IaC, and operations for NFR-03/NFR-10

- OTel instrumentation: agent spans, LLM/MCP latencies, stage transition metrics
- Prometheus /metrics + Grafana SLO dashboards
- docker-compose.observability.yml overlay
- Helm chart for Kubernetes deployment (dev + prod values)
- GitHub Actions CI: Python tests, frontend build, Semgrep SAST, Trivy scan, cosign signing
- DR: backup/restore scripts + failover runbook (RTO ≤ 15m / RPO ≈ 0)
- Audit integrity CronJob script
- docs/OPERATIONS.md
```
Mark **Phase 13** as `[x]` in the Phase Status Tracker and commit this file. All phases complete.

---

## Standing risks (keep in mind across all phases)

| Risk | Where it matters | Mitigation |
|---|---|---|
| Temporal migration scope | Phase 0.5 | Largest single phase; consider feature-branch + incremental PR strategy |
| `is_enabled=false` is a compliance risk | Phase 5, Phase 9 | Portal requires confirmation to disable SLA on regulated stages; flag visually |
| `warning_pct < escalation_pct` must be enforced | Phase 1, Phase 9 | DB CHECK constraint + portal UI validation |
| Clock pausing requires net-elapsed tracking | Phase 5 | `paused_at` + `paused_duration_seconds` in `case_sla_tracking`; tested |
| `is_regulatory_breach` is audit-trail critical | Phase 2.5, Phase 5 | Set on escalation-threshold breach only; BSA 5-year retention |
| Pipeline dangling-edge check is load-bearing | Phase 1, Phase 4, Phase 9 | `DomainDefinitionLoader.validate()` checks wiring; portal blocks activation |
| Permission model security boundary | Phase 7, Phase 9 | Security review; document permission catalog; test over-grant scenarios |
| OPA adds a new infrastructure dependency | Phase 4.6 | Provide in-process Python fallback for dev; OPA required for prod |
| Temporal adds operational complexity | All phases | Phase 13 adds Temporal to observability + Helm; Temporal Web UI is built-in |
| Hash-chain audit WORM semantics | Phase 2.5 | Enforce at DB role level; test that app user cannot UPDATE decision_log |
| `asyncio.Lock`-per-case → Temporal | Phase 0.5 | Temporal handles concurrency at workflow level; remove asyncio locks in migration |
| ADR conformance | All phases | This plan conforms to ADR-001 through ADR-008; new ADRs documented in Phase 0.5 |
| Event bus is asyncio queue → Temporal Signal | Phase 0.5 | Temporal Signals are durable; asyncio queues are in-process only — major durability improvement |
