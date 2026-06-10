# CADF — Client Agentic Development Framework
## Conversion Plan: GlideGate → Generic Admin-Configurable Onboarding Framework

## Phase Status Tracker

> **Read this first every session.** Find the first unchecked phase — that is where to start.
> When a phase is fully verified and committed, change `[ ]` to `[x]` and commit this file.

- [ ] **Phase 0** — Audit & wire dead orchestrator config
- [ ] **Phase 1** — Design the DB-backed DomainDefinition model
- [ ] **Phase 2** — Split OnboardingState into typed core + extension bag
- [ ] **Phase 3** — Replace if/elif stage routing with config-driven StageDispatcher
- [ ] **Phase 4** — Make products, questions, and per-product agent pipelines config-driven
- [ ] **Phase 5** — Configurable SLA enforcement with feature flags and per-stage parameters
- [ ] **Phase 6** — Wire Skills & MCP into live agent execution, made domain-configurable
- [ ] **Phase 7** — Replace hardcoded personas/roles with configurable persona + permission model
- [ ] **Phase 8** — Loosen DB CHECK constraints; make domain reference rows authoritative
- [ ] **Phase 9** — Build the Admin Portal
- [ ] **Phase 10** — Serve frontend vocabulary from the domain API
- [ ] **Phase 11** — Stand up Retail/Deposit through the admin portal (acceptance proof)
- [ ] **Phase 12** — Extract the framework/domain package boundary

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
`docs/specs/` (BRD, Technical Architecture, ADRs) describe an *aspirational* target architecture
(Temporal, Kafka, LangGraph, DMN/Camunda, OPA, MCP Gateway, "Criteria & Wiring Designer" UI) —
much of which already exists in skeletal/dormant form in the real code, just not wired up or made
configurable.

**New requirement:** generalize this into a reusable framework for *different onboarding domains*
(Retail/Deposit, Loans, Mortgage, etc. — already named in the Technical Architecture roadmap),
where new domains, their workflows, personas/roles, agent prompts/skills/MCP tool-access,
products and their onboarding questions, per-product agent pipeline composition, per-stage SLA
windows with priority-tier overrides and per-product feature flags can all be configured
**through an admin portal** — not by an engineer editing code or redeploying.

---

## Strategy (decided — do not re-litigate)

- **Config-driven, DB-backed, admin-authored.** Keep and generalize the existing working
  substrate (asyncio event bus, `BaseAgent`, blackboard/ContextStore, Skills framework, MCP
  gateway abstraction, existing `Product.step_sequence`/`suitability_criteria` JSONB columns,
  `OnboardingQuestion.product_id` FK, and `OnboardingCase.sla_deadline` field + escalation flow).
  Do not rewrite to BPMN/DSL or adopt the aspirational Temporal/Kafka/LangGraph stack.
- **Finish wiring what already exists.** Most abstractions (Skills, MCP gateway,
  `AgentEventBus.subscribe()`, product JSONB columns, SLA deadline field) are already built but
  dormant/bypassed. The plan is mostly "activate + generalize", not "build from scratch".
- **Explicit over implicit.** Keep the FSM, product pipelines, and SLA schedules as editable,
  visualizable graphs in the admin portal — avoids the "criteria-driven selection uncertainty"
  pitfall of ADR-002.
- **Single-tenant per deployment.** No runtime domain-switching. Prove genericity by standing up
  Retail/Deposit as a separate deployment configured entirely through the admin portal.
- **Event bus decoupling principle.** The `AgentEventBus` uses publisher/subscriber — adding a
  new agent/subscriber requires zero changes to upstream agents. Note: the bus is a custom asyncio
  queue, not Kafka/Pulsar (aspirational in spec docs, not in actual code).
- **Extensibility contract.** New stages inserted via `domain_stages`/`domain_transitions` rows.
  New agents declare entry/exit contracts via `domain_agent_capabilities` rows and subscribe via
  `AgentEventBus.subscribe()`. Existing agents are never modified when new stages or agents are
  added. A new domain needs at most one new agent class; everything else is portal-authored rows.

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
- Agent entry/exit contracts are implicit: `handlers = {TaskType.X: self._handle_y}` dicts
  (entry) + hardcoded `self.send_task(TaskPacket(...))` calls (exit). `AgentEventBus.subscribe()`
  (`agent_event_bus.py:40`) exists as a declarative seam — never called.

### SLA / escalation
- `OnboardingCase.sla_deadline` field exists (`models/cases.py:37`) — appears in API response
  schemas but no business logic sets or enforces it. Dead field.
- No `priority_tier` on cases or clients. `AgentTask.priority` (LOW/NORMAL/HIGH/CRITICAL) exists
  at task level only.
- No background scheduler — no APScheduler/Celery. Only `asyncio.create_task()` fire-and-forget.
  `orchestration_service.start()/stop()` are the lifecycle hooks (`main.py:103,108`).
- Escalation path IS fully built (risk-score driven): KYC → Orchestrator
  (`orchestrator_agent.py:385-439`) → ESCALATED stage + `SEND_ESCALATION_ALERT` →
  NotificationAgent (`notification_agent.py:88-114`, CRITICAL priority, socket.io broadcast).
  SLA breach will reuse this exact path.
- `EventLog` (`models/agents.py:72-90`): `event_type`, `event_category`, `is_compliance_event`
  bool. `AuditEventType` enum (`audit_event_types.py:6-77`) has `KYC_ESCALATED`,
  `COMPLIANCE_DECISION`. Will add `SLA_WARNING`/`SLA_BREACH`.

### Schema / frontend
- DB CHECK constraints (`oc_status_chk`, `oc_stage_chk`, `product_type`) hardcode wealth vocab.
- `frontend/src/features/advisor/CaseListTable.tsx:14-34`: `STAGE_LABELS`/`STAGE_STYLES`/
  `ALL_STAGES` hardcoded; no domain-config API today.
- `ContextStoreService`: per-case `asyncio.Lock`, optimistic `version`-locking, DB snapshot
  persistence — clean, reusable blackboard as-is.

---

## Phase Dependency Map

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 ──────────────────────────────────────────┐
                                    └──── Phase 4 (parallel-safe with Phase 5) ──┤
                                    └──── Phase 5 (parallel-safe with Phase 4) ──┤
                                                                                   ↓
                           Phase 6 → Phase 7 → Phase 8 → Phase 9 → Phase 10 → Phase 11 → Phase 12
```

Phases 4 and 5 both depend on Phases 1–3 but are independent of each other (different code
areas) and can be worked in parallel by two team members.

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

**Why this matters:** closes a real drift bug AND proves "data drives the FSM" cheaply —
same fix shape used in Phases 4 and 5 one layer down. If this works, the pattern is validated.

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

## Phase 1 — Design the DB-backed DomainDefinition model

### Session start checklist
- Run `git log --oneline -5` — Phase 0 commit must be present
- Read `backend/app/agents/base/a2a_types.py` (AgentID, TaskType, OnboardingStage enums to generalize)
- Read `backend/app/services/orchestration/agent_orchestration_service.py:250-285` (`_build_agents`)
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
| `domain_product_pipelines` | Step sequence executed by each product's `ProductOnboardingAgent` instance (`domain_id`, `product_code`, `step_id`, `step_label`, `step_order`, `is_parallel bool`, `step_config JSONB`) |
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
  strings checked against the loaded domain's vocabulary (do not use dynamic StrEnum
  construction — it breaks static typing for no gain)
- Seed script: migrate the corrected Phase-0 config into `domain_*` rows for the wealth domain
  (golden proof the model faithfully represents what's running today)

**Modified:** `a2a_types.py`, `agent_orchestration_service.py` (pass `DomainDefinition` to agent
construction rather than hardcoded list)

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
- Read `backend/app/services/context_store/context_store_service.py` (blackboard — understand
  how state is read/written before touching the model)
- Grep `backend/app/agents/` for direct field accesses to `kyc_status`, `kyc_risk_score`,
  `sales_review_decision`, `escalation_reason`, `human_review_id`, `sales_review_id` — these are
  all the call sites that must be converted before the model changes

### What to build
Restructure `OnboardingState` into:
- **Generic typed core**: `case_id`, `client_id`, `stage: str`, `selected_products`,
  `product_tracks`, `priority_tier: str` *(new — needed for SLA window selection in Phase 5)*,
  `version`, timestamps
- **Extension bag**: `extra: dict[str, Any]` backed by existing `shared_context JSONB` column
  (no schema migration needed)
- **Typed extension view helpers**: `WealthExtension.from_state(state)` giving
  `state.extra["kyc_status"]` etc. with type safety for existing wealth agents — zero behavior
  change, just a typed accessor layer

**Order of operations (do not skip):**
1. Write characterization tests (request/response/state snapshots) on the current wealth flow
   *before* touching the model — these are your regression guard
2. Convert all grepped call sites to `state.extra["..."]` / typed accessors
3. Audit `orchestrator_agent.py`'s `self._states` dict for in-place mutation bypassing
   `ContextStoreService.update_state()` — would silently break optimistic locking; fix any found
4. Change the model

**Migration:** add `priority_tier varchar default 'standard'` to `onboarding_cases` (used in
Phase 5 for SLA window selection; default keeps existing rows valid)

### Verification
Re-run characterization tests taken in step 1 — diff must be empty. Existing suite green.

### Session end — commit template
```
feat(cadf-phase-2): split OnboardingState into typed core + extension bag

- OnboardingState: generic core fields + extra JSONB bag
- WealthExtension typed accessor helpers
- All wealth agents converted to typed accessors (no raw field access)
- Characterization snapshot tests added
- Migration: priority_tier added to onboarding_cases
```
Mark **Phase 2** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 3 — Replace if/elif stage routing with a config-driven StageDispatcher

### Session start checklist
- Run `git log --oneline -5` — Phase 2 commit must be present
- Read `backend/app/agents/orchestrator/orchestrator_agent.py:195-700` (the if/elif chain and
  `_resume_routing` dict you are replacing)
- Read `backend/app/domain/domain_definition.py` (the `DomainDefinition` model to source from)

### What to build
Replace `_route_to_stage`'s ~150-line if/elif chain (`orchestrator_agent.py:538-687`) and
`_resume_routing` dict with a generic `StageDispatcher` that:
- Walks `StageActionSpec` rows from `DomainDefinition.task_routing[stage_code]`
- Each spec: `{target_agent, task_type, priority, payload_template, notification_templates}`
- Template placeholders resolved by small named "resolver" functions (generalizing the inline
  DB-fetch at orchestrator lines 624-648)
- Emits the same `TaskPacket` sequence the old if/elif produced for the wealth domain (verified
  by snapshot test)

**Also wire the stage-transition SLA hook here** (Phase 5 depends on it): on every stage
transition, call `SLAHook.on_stage_entered(case_id, new_stage, domain_def)` — a stub in Phase 3,
activated in Phase 5. Having the hook in place means Phase 5 needs no orchestrator changes.

**Preserve — do not remove:**
- FSM/DB drift resync logic in `_handle_advance` (~lines 248-255) — active durability behavior
- Cold-start product-track recreation (~lines 296-299) — active durability behavior

**Files (new):** `backend/app/services/orchestration/stage_dispatcher.py`
**Files (modified):** `orchestrator_agent.py`

### Verification
Snapshot-compare `TaskPacket` sequences emitted by `StageDispatcher` vs. the old if/elif chain
for every stage in the wealth journey — must be byte-identical. Existing suite green.

### Session end — commit template
```
feat(cadf-phase-3): replace if/elif stage routing with config-driven StageDispatcher

- StageDispatcher reads StageActionSpec rows from DomainDefinition
- Template resolver functions replace inline DB-fetches
- SLAHook.on_stage_entered stub wired into stage transitions (activated in Phase 5)
- Snapshot tests confirm TaskPacket sequences identical for wealth domain
```
Mark **Phase 3** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 4 — Make products, questions, and per-product agent pipelines config-driven

### Session start checklist
- Run `git log --oneline -5` — Phase 3 commit must be present
- Read `backend/app/agents/product_onboarding/product_onboarding_agent.py:95-140`
  (hardcoded `_PRODUCT_STEPS` dict — the dead config to fix)
- Read `backend/app/agents/product_onboarding/suitability_assessor.py:15-85`
  (hardcoded risk maps and scoring weights — the dead config to fix)
- Read `backend/app/agents/base/agent_event_bus.py` (the `subscribe()` method to activate)
- Read `backend/app/services/orchestration/agent_orchestration_service.py:250-285`
  (hardcoded `_build_agents()` list to replace)

> **Note:** Phase 4 and Phase 5 are independent and can be worked in parallel by two team members.
> Phase 4 touches product/agent wiring. Phase 5 touches SLA monitoring.

### What to build

**(a) Finish wiring Product.step_sequence / suitability_criteria / OnboardingQuestion.product_id**

Move hardcoded `_PRODUCT_STEPS`, `_RISK_CAPACITY_MAP`, `_PRODUCT_MIN_RISK/AGE/INCOME`, and
scoring weights into the JSONB columns that already exist in the schema. Define typed JSON schemas:
- `step_sequence`: `[{"step_id": "suitability_assessment", "label": "...", "order": 1}]`
- `suitability_criteria`: `{"risk_thresholds": {...}, "scoring_weights": {"risk": 0.4, "income": 0.3, ...}, "min_age": ..., "min_income": ...}`

Make `ProductOnboardingAgent` and `SuitabilityAssessor` read from DB rows instead of constants.
Per-product questionnaires: make `OnboardingQuestion.product_id` linkage first-class — the
product catalog editor (Phase 9) will author these rows.

**(b) Declarative agent entry/exit contracts**

Introduce `AgentCapabilitySpec` — each agent's entry contract (subscribed `TaskType`s) and exit
contract (emitted `TaskType`s + allowed handoff targets) sourced from `domain_agent_capabilities`
rows and wired through `AgentEventBus.subscribe()` (the seam that exists but is never called).
Migrate each agent:
- Replace inline `handlers = {TaskType.X: self._handle_y, ...}` dicts in `process()` with
  subscriptions declared in the agent's capability spec row
- Replace hardcoded `self.send_task(TaskPacket(to_agent=..., task_type=...))` exit calls with
  calls that validate against the allowed exit contracts before sending

This is the mechanism enabling "plug in a new agent with zero orchestrator changes": write the
agent class → declare its capability spec rows → wire into a product pipeline.

**(c) Per-product named agent instances**

Keep a single `ProductOnboardingAgent` class but change how it is instantiated.
`ParallelProductLauncher` spawns one instance per selected product, assigning each instance an
agent name of `ProductOnboardingAgent[{product_code}]` (e.g. `ProductOnboardingAgent[equity_fund]`,
`ProductOnboardingAgent[savings_account]`). Each instance reads its step sequence from
`domain_product_pipelines` rows keyed by its product code. Remove `_build_agents()`'s fixed global
8-agent list and replace with dynamic per-product instantiation.

The named-instance identity flows through `AgentEventBus` so every `TaskPacket` and event log
entry carries the product-scoped agent name. The agent trace screen displays a distinct row for
each product's instance — a case with three selected products shows three
`ProductOnboardingAgent[*]` entries. "Which steps, in what order/parallelism, with what config" is
data per product; the agent class is shared by all.

**Files modified:** `product_onboarding_agent.py`, `suitability_assessor.py`,
`parallel_product_launcher.py`, `agent_orchestration_service.py`, `agent_event_bus.py`,
all agents' `process()` and exit-handler methods (entry/exit contract migration)

### Verification
Snapshot-compare suitability scores, step sequences, and emitted `TaskPacket` handoff sequences
for existing wealth products before/after — values identical, only source changes (Python constant
→ JSONB row / capability-spec row). Agent trace records must show `ProductOnboardingAgent[{product_code}]`
for each selected product. Existing suite green.

### Session end — commit template
```
feat(cadf-phase-4): make products, questions, and per-product agent instances config-driven

- Product.step_sequence and suitability_criteria JSONB now live source of truth
- SuitabilityAssessor reads thresholds/weights from DB, not hardcoded constants
- AgentCapabilitySpec wired through AgentEventBus.subscribe()
- Single ProductOnboardingAgent class; ParallelProductLauncher spawns one named instance per
  selected product (ProductOnboardingAgent[{product_code}])
- domain_product_pipelines drives step sequence per instance (replaces _build_agents list)
- Snapshot tests confirm identical suitability scores and TaskPacket sequences; trace shows
  named instances
```
Mark **Phase 4** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 5 — Configurable SLA enforcement with feature flags and per-stage parameters

### Session start checklist
- Run `git log --oneline -5` — Phase 3 commit must be present (Phase 4 not required)
- Read `backend/app/services/orchestration/agent_orchestration_service.py` (start/stop lifecycle
  hooks — this is where `SLAMonitorService` is launched)
- Read `backend/app/agents/notification/notification_agent.py:80-115`
  (existing `_handle_escalation_alert` — the pattern SLA warnings reuse)
- Read `backend/app/agents/orchestrator/orchestrator_agent.py:385-439`
  (existing escalation path — SLA breach reuses this exactly)
- Read `backend/app/models/agents.py:72-90` (EventLog — adding `is_regulatory_breach` field)
- Read `backend/app/services/orchestration/stage_dispatcher.py` (the `SLAHook` stub from Phase 3)

> **Note:** Phase 4 and Phase 5 are independent. Both depend on Phase 3. Can be parallel.

### What to build

**`SLAMonitorService`** (`backend/app/services/sla/sla_monitor_service.py`):
A background asyncio task launched in `orchestration_service.start()`:

```python
async def _monitor_loop(self):
    while True:
        await asyncio.sleep(self._poll_interval)
        await self._check_all_active_cases()
```

For each row in `case_sla_tracking` with no `breach_fired_at`:
1. Resolve the applicable `domain_stage_slas` row using priority chain:
   `(domain, stage, product+tier) > (domain, stage, product) > (domain, stage, tier) > (domain, stage, default)`
2. **If `is_enabled=false` → skip entirely.** No events fire. This is the per-stage/per-product
   feature flag. SLA can be enabled for one product's workflow and disabled for others — the
   product-scoped row overrides the domain-level default.
3. Compute `net_elapsed_seconds = (now - entered_at).seconds - paused_duration_seconds`
4. Compute `net_elapsed_pct = (net_elapsed_seconds / (window_hours * 3600)) * 100`
5. If `net_elapsed_pct >= warning_pct` and `warning_fired_at IS NULL`:
   emit `warning_task_type` (default `SLA_WARNING`) to NotificationAgent
   (add `_handle_sla_warning` handler mirroring `_handle_escalation_alert`)
6. If `net_elapsed_pct >= escalation_pct` and `breach_fired_at IS NULL`:
   emit `escalation_task_type` (default `SLA_BREACH`) to Orchestrator.
   Orchestrator handles `SLA_BREACH` by routing to ESCALATED stage via the
   **existing escalation path** (`orchestrator_agent.py:385-439`) — reuse, don't duplicate.
   Log `AuditEventType.SLA_BREACH` with `is_compliance_event=True` +
   `is_regulatory_breach=True` (new field on `EventLog` — load-bearing for regulatory audit).

**Clock pausing** (if `pause_on_human_review=true`):
- On stage entry, if stage is human-pending (`domain_stages.is_human_pending=true`),
  set `case_sla_tracking.paused_at = now`
- On stage exit from a human-pending stage: add `(now - paused_at)` to
  `paused_duration_seconds`, clear `paused_at`
- Monitor loop uses `net_elapsed_seconds` (excludes paused duration) for all threshold checks

**`priority_tier` SLA window selection**: on stage entry, look up `domain_stage_slas` by the
case's `priority_tier` (from `OnboardingCase.priority_tier` added in Phase 2) and `product_code`.
If `is_enabled=false` for the resolved row, write nothing to `case_sla_tracking`. If enabled,
compute `deadline_at = entered_at + window_hours`, write tracking row, update
`OnboardingCase.sla_deadline`.

**The feature flag axes are independent:**
- Disable SLA for a stage across all products: global default row with `is_enabled=false`
- Disable SLA for one product across all its stages: product-scoped rows with `is_enabled=false`
- Enable SLA for one product while all others are disabled: product-scoped `is_enabled=true`
  overrides a global `is_enabled=false` default

**Files (new):** `backend/app/services/sla/sla_monitor_service.py`
**Files (modified):** `orchestrator_agent.py` (activate `SLAHook`, add `SLA_BREACH` handler),
`notification_agent.py` (add `SLA_WARNING` handler), `models/agents.py` (add
`is_regulatory_breach bool default false` to `EventLog`),
`audit_event_types.py` (add `SLA_WARNING`, `SLA_BREACH`),
`agent_orchestration_service.py` (start/stop `SLAMonitorService`)

### Verification
Integration tests with a `window_hours` of ~0.0003 (≈ 1 second):
- `is_enabled=true`, `warning_pct=70`, `escalation_pct=90` → warning fires at 70%, escalation
  fires independently at 90%, case transitions to ESCALATED, `is_regulatory_breach=True` on log
- `is_enabled=false` → zero events fire
- `pause_on_human_review=true` → elapsed excludes hold period; thresholds fire on net elapsed
- Product-scoped `is_enabled=false` overrides domain-level `is_enabled=true`
- Portal (Phase 9) rejects `warning_pct >= escalation_pct` with a validation error

### Session end — commit template
```
feat(cadf-phase-5): configurable SLA enforcement with per-stage/per-product feature flags

- SLAMonitorService: background asyncio loop, poll interval configurable
- Per-row feature flag: is_enabled=false disables monitoring for that stage/product
- Configurable warning_pct, escalation_pct (independent thresholds), window_hours
- Clock pausing for human-review stages (paused_duration_seconds in case_sla_tracking)
- SLA breach reuses existing orchestrator escalation path
- EventLog.is_regulatory_breach field added (BSA audit trail)
- Integration tests covering all flag/threshold combinations
```
Mark **Phase 5** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 6 — Wire Skills & MCP into live agent execution, made domain-configurable

### Session start checklist
- Run `git log --oneline -5` — Phases 4 and 5 commits must both be present
- Read `backend/app/agents/skills/__init__.py` (the 6 dormant skill singletons)
- Read `backend/app/agents/skills/base_skill.py` (the `invoke()` ABC)
- Read `backend/app/agents/kyc_compliance/kyc_compliance_agent.py:260-380`
  (the `_simulate_identity_verification` method to replace with `mcp_registry.invoke`)
- Read `backend/app/mcp/mcp_connector.py` (MCPRegistry — the gateway to route through)
- Read `backend/app/services/validation/prompt_override_store.py` (the existing override store
  to generalize)

### What to build

**Skills:** Replace each agent's inline reasoning/extraction logic with `skill.invoke(...)` calls,
bindings read from `domain_agent_skills` rows (which skill, with what parameters). No agent knows
at code time which skill it calls — the binding is data.

**MCP:** Replace `_simulate_identity_verification()` and all `_simulate_*` methods with
`mcp_registry.invoke(tool, ...)`. Add grant-checking to `MCPRegistry.invoke()`: look up
`domain_agent_tool_grants` — if the calling agent is not granted the tool, raise a loud, audible
error and fail closed (not just log). Connectors stay simulated — only the *path* changes.
This is ADR-007's "MCP Gateway as sole egress" finally enforced in code.

**Prompts:** Extend `prompt_override_store` from validation-prompt scope to all agent system
prompts, keyed by `(domain_id, agent_id, prompt_role)`. The existing DB-backed override + cache
pattern generalizes cleanly — mostly scope-widening. On startup, load all `domain_agent_prompts`
rows into the override store cache.

**Files modified:** all agents with `_simulate_*` calls (notably `kyc_compliance_agent.py`,
`document_intelligence_agent.py`), `prompt_override_store.py`, `mcp/mcp_connector.py`

### Verification
Snapshot agent decisions and outputs before/after — routing through `mcp_registry` and
`skill.invoke()` must produce equivalent outputs. An agent calling an ungranted MCP tool must
raise an error (not silently pass). Existing suite green.

### Session end — commit template
```
feat(cadf-phase-6): wire Skills and MCP gateway into live agent execution

- Agents now call skill.invoke() with bindings from domain_agent_skills rows
- _simulate_* methods replaced by mcp_registry.invoke() with grant-checking
- MCPRegistry.invoke() fails closed on ungranted tools (ADR-007 enforced)
- prompt_override_store generalized to all agent prompts, domain-scoped
- Snapshot tests confirm equivalent agent decisions through new paths
```
Mark **Phase 6** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 7 — Replace hardcoded personas/roles with configurable persona + permission model

### Session start checklist
- Run `git log --oneline -5` — Phase 6 commit must be present
- Read `backend/app/api/routers/cases.py` (find all `require_role(...)` call sites)
- Grep `backend/app/api/routers/` for `require_role` — list every file and line
- Read `backend/alembic/versions/0010_add_sales_manager_role.py` (the migration that proves
  why this phase exists — adding one role touched ~13 files)

### What to build
Replace `users.role` DB CHECK enum and scattered `require_role(...)` guards with:
- `domain_personas` rows as the source of truth for valid roles in a domain
- A `require_permission("scope")` guard function that resolves against the active domain's
  persona definitions (e.g., `require_permission("review:approve")` instead of
  `require_role("sales_manager", "compliance")`)
- A `domain_permissions` scope model with a fixed, framework-defined permission catalog
  (the framework declares *what* can be permissioned; the portal lets a domain decide *who* gets it)

Build a compatibility layer expressing existing wealth personas (advisor, compliance, ops,
sales_manager, client) as `domain_personas` rows with their current permission scopes — zero
behavior change. That's the regression test for this phase.

**Security note:** admin-editable persona definitions move the trust boundary into DB-editable
data. Include a security review: confirm no persona can be configured to access endpoints its
scope should exclude. Document the permission catalog and what each scope gates.

**Files modified (migration):** `users.role` CHECK → `persona_code` FK
**Files modified (guards):** `cases.py`, `clients.py`, `reviews.py`, `audit.py`,
`collaboration.py`, `auth.py` — replace every `require_role(...)` with `require_permission(...)`

### Verification
Regression test: every existing wealth persona retains exactly its current permissions, landing
pages, and nav after migrating to the new model. Suite green.

### Session end — commit template
```
feat(cadf-phase-7): replace hardcoded role guards with configurable persona + permission model

- users.role CHECK → persona_code FK to domain_personas
- require_role() replaced by require_permission() across all routers
- Wealth personas expressed as domain_personas rows with matching permission scopes
- Security review documented in docs/specs/permission-model-security-review.md
```
Mark **Phase 7** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 8 — Loosen DB CHECK constraints; make domain reference rows authoritative

### Session start checklist
- Run `git log --oneline -5` — Phase 7 commit must be present
- Read `db/schema/002_onboarding_cases.sql` (the CHECK constraints to loosen)
- Read `backend/app/services/context_store/context_store_service.py`
  (where application-layer validation will replace the removed CHECKs)

### What to build
Replace `oc_status_chk`, `oc_stage_chk` (hardcoded 7-value enum), and `products.product_type`
CHECK constraint with application-layer validation in `ContextStoreService` and repository
boundaries — validating against `domain_stages`/`domain_product_types` reference rows instead.
Single source of truth moves from three places (enum, dead JSON, CHECK) to one (`domain_*` tables).

**Migration risk:** loosening is always safe for existing data. Make this migration purely
additive (drop CHECKs, add nothing new). Defer any new DB-level constraints until Phase 11.

**Files (new):** loosening migration
**Files (modified):** `context_store_service.py`, `models/cases.py`

### Verification
Insert a wealth case with a stage value not in the old CHECK enum — must fail at app layer but
not at DB layer. Insert a case with a valid domain stage — succeeds. Suite green.

### Session end — commit template
```
feat(cadf-phase-8): loosen DB CHECK constraints, domain reference rows now authoritative

- Dropped oc_status_chk, oc_stage_chk, product_type CHECK constraints
- ContextStoreService validates stage/product_type against domain_stages rows
- No behavior change for existing wealth domain cases
```
Mark **Phase 8** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 9 — Build the Admin Portal

### Session start checklist
- Run `git log --oneline -5` — Phase 8 commit must be present
- Read `backend/app/domain/domain_definition.py` (the model the portal edits)
- Read `frontend/src/` structure to understand existing component/router patterns

### What to build
Admin-facing UI + CRUD/validation API letting a business user define a domain end-to-end.

**Backend API routers (new):**
- `api/routers/admin/domains.py` — domain CRUD + draft/validate/activate lifecycle
- `api/routers/admin/stages.py` — stage/transition graph editor (structural validation on save)
- `api/routers/admin/agents.py` — agent roster, capability (entry/exit), prompts, skill bindings,
  MCP tool grants
- `api/routers/admin/pipelines.py` — per-product pipeline composer (validates against capability
  contracts — rejects wiring agent A's exit to a task type agent B doesn't subscribe to)
- `api/routers/admin/products.py` — product catalog, step sequences, suitability criteria,
  questionnaire assignment
- `api/routers/admin/sla.py` — SLA grid (per-stage × tier × product); `is_enabled` toggle,
  `window_hours`, `warning_pct`, `escalation_pct`, `pause_on_human_review`; rejects
  `warning_pct >= escalation_pct`; requires confirmation before disabling SLA on regulated stages
- `api/routers/admin/personas.py` — persona/permission editor

**Frontend (new):** `frontend/src/features/admin/*`
- Domain & FSM editor with visual transition graph
- Agent behavior editor (prompt, skill-binding, MCP tool-grant, capability contract viewer)
- Visual per-product step sequence editor — shows steps configured for each `ProductOnboardingAgent[{product_code}]` instance (step ID, order, parallel grouping, step config JSONB); preview pane shows expected named agent instances for a given product selection
- **SLA editor**: grid keyed by stage × tier × product; `is_enabled` toggle (prominent, requires
  confirmation when disabling regulated stages), `window_hours`, `warning_pct`, `escalation_pct`
  (enforced: warning < escalation), `pause_on_human_review`; **SLA health dashboard** showing
  active cases by stage — % elapsed, tier, breach/warning status
- Persona & permission editor; display vocabulary editor

**Draft → validate → activate:** staged changes; `DomainDefinitionLoader.validate()` on activate;
effective for new cases only — in-flight cases pinned to their starting version.

### Verification
Portal validation tests: submit malformed domains (orphan stage, dangling pipeline edge, SLA row
with `warning_pct=90, escalation_pct=80`, `is_enabled=false` on KYC without confirmation) — all
rejected with actionable errors. Suite green.

### Session end — commit template
```
feat(cadf-phase-9): admin portal for domain configuration

- CRUD + validation API for all domain_* tables
- Visual FSM editor, pipeline composer, SLA editor, persona editor
- Draft/validate/activate lifecycle with DomainDefinitionLoader contract enforcement
- SLA health dashboard
```
Mark **Phase 9** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 10 — Serve frontend vocabulary from the domain API

### Session start checklist
- Run `git log --oneline -5` — Phase 9 commit must be present
- Grep `frontend/src` for: `STAGE_LABELS`, `STAGE_STYLES`, `ALL_STAGES`, `TeamRole`,
  `ROLE_COLORS`, `NAV_LINKS`, `OnboardingStage`-shaped literals, `case_stage_changed`
  socket handlers — these are every hardcoded vocabulary site to replace

### What to build
Add `GET /api/config/domain` (serves `DomainDefinition` display vocabulary +
`domain_display_config` rows). Replace all hardcoded stage/persona/role display constants in the
frontend with a `useDomainConfig()` hook. Provide a static fallback (the current wealth values)
during rollout — no flag-day cutover.

**Files (new):** `api/routers/domain_config.py`, `frontend/src/hooks/useDomainConfig.ts`
**Files (modified):** `CaseListTable.tsx`, `tokens.ts`, `App.tsx`, `ProtectedRoute.tsx`,
and any others found in the grep above

### Verification
With the wealth domain active, the frontend renders identically to before. With a test domain
loaded, the frontend renders that domain's vocabulary. Suite green.

### Session end — commit template
```
feat(cadf-phase-10): serve frontend vocabulary from domain config API

- GET /api/config/domain endpoint
- useDomainConfig() hook replaces all hardcoded stage/persona display constants
- Static fallback preserves current behavior during rollout
```
Mark **Phase 10** as `[x]` in the Phase Status Tracker and commit this file.

---

## Phase 11 — Stand up Retail/Deposit through the admin portal (the real proof)

### Session start checklist
- Run `git log --oneline -5` — Phase 10 commit must be present
- Read `docs/specs/Technical_Architecture_Client_Onboarding.docx` (Retail/Deposit section —
  source of truth for this domain's workflow and products)
- Open the admin portal at the running Phase 10 deployment

### What to build
Using the admin portal — **not migration scripts** — define Retail/Deposit end-to-end:
- Stages/transitions, agent roster + capability specs
- Product catalog with step sequences, suitability criteria, per-product questionnaires
- Per-product agent pipelines (composed in the visual pipeline editor)
- **SLA schedule** with at least one stage `is_enabled=false` (e.g. INTAKE) and one product
  with all-stages SLA disabled (e.g. "instant-account") — exercises the feature flag
- Personas (e.g. "deposit-ops"), permissions, display vocabulary

Expect **at most one new Python agent class** (e.g. `DepositSpecialistAgent`). Its entry/exit
wiring is done via the portal's capability + pipeline editors — zero changes to `AgentEventBus`,
orchestrator, or any existing agent. Run as a separate single-tenant deployment.

### Verification — acceptance checklist
Run every item; any failure means re-visiting the indicated phase:

- [ ] Zero `domain_*`/product/pipeline/SLA/questionnaire rows for Retail/Deposit from scripts
- [ ] ≤ 1 new agent class; 0 modifications to any existing wealth agent class
- [ ] New agent wired via portal only — zero `AgentEventBus`/orchestrator code changes
- [ ] 0 changes to `a2a_types.py`, `workflow_state_machine.py`, `orchestrator_agent.py`,
      `prompt_override_store.py`, `mcp_connector.py`, `agent_event_bus.py`,
      `sla_monitor_service.py`, `require_permission` call sites for this launch
- [ ] Frontend renders Retail/Deposit vocab from `/api/config/domain`
- [ ] `priority_tier="sme"` deposit case gets a different SLA window than `priority_tier="standard"`
- [ ] Overdue test case fires `SLA_WARNING` at `warning_pct`%, auto-escalates at `escalation_pct`%,
      `is_regulatory_breach=True` in `EventLog`
- [ ] Case in `pause_on_human_review=true` stage does NOT consume SLA during hold
- [ ] "instant-account" product has SLA fully disabled — zero SLA events fire
- [ ] "deposit-ops" persona logs in with correct landing page/nav — no frontend code change
- [ ] Pipeline composer shows correct step sequence per deposit product; agent trace shows distinct `ProductOnboardingAgent[{product_code}]` instances for each selected product
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
- Run `git log --oneline -5` — Phase 11 commit + passing acceptance checklist must be present
- Run `grep -r "from app.agents.kyc" backend/app/framework` — should find nothing

### What to build
Draw the line between **framework** (generic infrastructure — `agents/base/`,
`services/orchestration/`, `services/context_store/`, `services/sla/`, `agents/skills/`, `mcp/`,
`domain/`, `api/routers/admin/`, `api/routers/domain_config.py`) and **domain pack**
(wealth-specific — `agents/kyc_compliance/`, `agents/sales_manager/`,
`agents/product_onboarding/` wealth config, `db/seeds/wealth_domain/`).

Package restructure (`backend/app/framework/` vs `backend/app/domains/{wealth,retail_deposit}/`)
or enforced import-boundary lint rule (`flake8-import-linter`). Deliberately last — boundary
derived from what Phase 11 proved, not guessed upfront.

### Verification
Import-boundary lint: no `framework/` imports from `domains/`; no cross-domain imports.
Suite green.

### Session end — commit template
```
feat(cadf-phase-12): extract framework/domain package boundary

- backend/app/framework/ contains all generic infrastructure
- backend/app/domains/{wealth,retail_deposit}/ contain domain-specific code
- Import-boundary lint rule enforced in CI
```
Mark **Phase 12** as `[x]` in the Phase Status Tracker and commit this file. All phases complete.

---

## Standing risks (keep in mind across all phases)

| Risk | Where it matters | Mitigation |
|---|---|---|
| `is_enabled=false` is a compliance risk | Phase 5, Phase 9 | Portal requires confirmation to disable SLA on regulated stages; flag visually |
| `warning_pct < escalation_pct` must be enforced | Phase 1, Phase 9 | DB CHECK constraint + portal UI validation |
| Clock pausing requires net-elapsed tracking | Phase 5 | `paused_at` + `paused_duration_seconds` in `case_sla_tracking`; tested in integration suite |
| `is_regulatory_breach` is audit-trail critical | Phase 5 | Set on escalation-threshold breach only, never on warning; BSA 5-year retention applies |
| Pipeline dangling-edge check is load-bearing | Phase 1, Phase 4, Phase 9 | `DomainDefinitionLoader.validate()` checks entry/exit wiring; portal blocks activation |
| Permission model security boundary | Phase 7, Phase 9 | Security review; document permission catalog; test over-grant scenarios |
| `asyncio.Lock`-per-case is in-process | All phases | Fine for single-tenant; breaks across replicas — note in ADR trail |
| ADR conformance | All phases | This plan's strategy is a scoped realization of ADR-002 — write up as a proposed ADR before Phase 1 lands |
| Event bus is asyncio queue, not Kafka/Pulsar | All phases | Decoupling principle holds; durability/distribution of Kafka does not — separate initiative if needed |
