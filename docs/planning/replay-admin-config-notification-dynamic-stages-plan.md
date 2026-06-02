# GlideGate — Action Items Implementation Plan

## Overview

Four action items to implement next. Each item has a clear scope, lists the exact files to create or modify, and describes the approach in enough detail to execute without ambiguity.

---

## Action 1 — Replay Button in Agent Trace Screen

### Goal
Add a Replay button to the Agent Trace screen that rewinds all agent nodes to idle and then animates the full historical execution flow — edge-by-edge, state-change-by-state-change — for a selected case.

### Why it's frontend-only
All data needed already exists in `GET /api/agents/trace/{case_id}`. The `tasks` array contains `from_agent`, `to_agent`, `task_type`, `status`, `created_at`, and `duration_ms` — enough to replay every state transition without a new backend endpoint.

### Approach

**`frontend/src/store/traceStore.ts`** — extend state shape:
```typescript
replayState: 'idle' | 'playing'  // replaces nothing; new field
replayProgress: number            // 0–100
replaySpeed: number               // ms per event (default 600)
startReplay: (tasks: AgentTaskOut[]) => void
stopReplay: () => void
setReplaySpeed: (ms: number) => void
```

`startReplay(tasks)`:
1. Sort `tasks` by `created_at` ascending.
2. Set all `nodeStates` to `'idle'` and clear `messageLog` and `edgeQueue`.
3. Set `replayState = 'playing'`.
4. Use `setInterval(speed)` — on each tick pop the next task, call `setNodeState` and `enqueueEdge` exactly as `useAgentTraceSocket` does for live events. Update `replayProgress` as `(index / total) * 100`.
5. On last task: `replayState = 'idle'`, clear the interval.

`stopReplay()`: clears the interval, sets `replayState = 'idle'`, does not reset node states (leaves canvas at replay end position).

Store the interval ID in a module-level ref inside the store action (not in Zustand state, to avoid stale closure issues).

**`frontend/src/features/agent-trace/ReplayControls.tsx`** — new component:
- "Replay" button (RotateCcw icon). Disabled when `!activeCaseId` or when no tasks exist.
- Speed selector: three chips — `0.5×` (1200 ms), `1×` (600 ms), `2×` (300 ms). Pre-selected default: `1×`.
- When `replayState === 'playing'`: show a slim progress bar + "Stop" button (Square icon).
- Mount point: toolbar strip at the top of `AgentTraceCanvas`, left side, next to the case selector.

**`frontend/src/features/agent-trace/AgentTraceCanvas.tsx`** — integrate:
- Import and render `<ReplayControls activeCaseId={activeCaseId} tasks={traceData?.tasks ?? []} />`.
- The existing `useEffect` that hydrates node states from `traceData` should short-circuit while `replayState === 'playing'` so polling does not override the replay animation mid-flight.

### Files
| File | Action |
|------|--------|
| `frontend/src/store/traceStore.ts` | Add replay state + 4 actions |
| `frontend/src/features/agent-trace/ReplayControls.tsx` | New component |
| `frontend/src/features/agent-trace/AgentTraceCanvas.tsx` | Mount `ReplayControls`, guard hydration effect |

---

## Action 2 — Enhance Admin Config (Onboarding Questions, Agents, Skills)

Three new tabs added to `frontend/src/routes/AdminConfig.tsx`. Each tab has backend endpoints and a frontend editor.

---

### 2A — Onboarding Questions Tab

#### Backend — `backend/app/api/routers/admin/questionnaire.py` (new file)

All endpoints are `admin`-role-guarded.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/questionnaire/questions` | List all questions ordered by section + order_index |
| `POST` | `/admin/questionnaire/questions` | Create a new question (returns 201) |
| `PUT` | `/admin/questionnaire/questions/{question_id}` | Full update of a question |
| `DELETE` | `/admin/questionnaire/questions/{question_id}` | Delete (returns 409 if any `onboarding_answers` reference it) |
| `POST` | `/admin/questionnaire/questions/reorder` | Batch `order_index` update — body: `[{id, order_index}]` |

Pydantic schemas:

```python
class QuestionAdminOut(BaseModel):
    id: UUID
    questionnaire_id: UUID
    question_key: str
    section: str
    label: str           # from extra_metadata["label"] or formatted question_key
    order_index: int
    question_type: str   # text | select | multi_select | boolean | currency | number | date | textarea
    options: list[str] | None
    validation_rules: dict[str, Any] | None
    show_if: dict[str, Any] | None
    is_required: bool

class CreateQuestionRequest(BaseModel):
    question_key: str
    section: str
    label: str
    order_index: int
    question_type: str
    options: list[str] | None = None
    validation_rules: dict[str, Any] | None = None
    show_if: dict[str, Any] | None = None
    is_required: bool = True

class UpdateQuestionRequest(CreateQuestionRequest):
    pass  # same fields, all required for PUT

class ReorderItem(BaseModel):
    id: UUID
    order_index: int
```

The default questionnaire (seeded in `db/seeds/03_questionnaire.py`) is fetched by `questionnaire_id = QUESTIONNAIRE_ID` from `seed_constants.py`. All CRUD operations target this default questionnaire.

#### Frontend — `frontend/src/features/admin/QuestionnaireEditor.tsx` (new)

- Fetches questions from `GET /admin/questionnaire/questions`.
- Groups by `section` in a vertical accordion list. Within each section, questions are sorted by `order_index`.
- Each question row shows: `question_key`, `label`, type chip, required/optional badge, edit (pencil) and delete (trash) icon buttons.
- "Add Question" button at the top of each section opens an **add/edit drawer** (right-side slide-in) with:
  - `question_key` text input (unique enforced by backend; validated on blur)
  - `section` select (pre-populated with existing sections + free-text option)
  - `label` text input
  - `field_type` select (text / select / multi_select / boolean / currency / number / date / textarea)
  - `options` tag input — shown only when type is `select` or `multi_select`; press Enter to add, × to remove
  - `is_required` toggle
  - `validation_rules` — key-value pair editor (min_length, max_length, min_age, etc.); raw JSON toggle for advanced editing
  - `show_if` — JSON textarea with a helper note explaining the `{field, operator, value}` shape
- Delete shows `ConfirmationModal`; if backend returns 409 (answers exist), shows an inline error instead of deleting.
- Drag-to-reorder within a section fires `POST /admin/questionnaire/questions/reorder` on drop.

#### Hooks — `frontend/src/hooks/useAdminQuestionnaire.ts` (new)
- `useAdminQuestions()` — TanStack Query, `staleTime: 30_000`
- `useCreateQuestion()`, `useUpdateQuestion()`, `useDeleteQuestion()`, `useReorderQuestions()` — mutations; all invalidate `['admin', 'questionnaire']` on success

---

### 2B — Agents Configuration Tab

The `agents` table already stores per-agent config JSONB and `is_active`. This tab surfaces that data for admin editing.

#### Backend — `backend/app/api/routers/admin/agents_config.py` (new file)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/agents` | List all agents with current config |
| `PUT` | `/admin/agents/{agent_id}` | Update agent `config` JSONB and/or `is_active` |
| `POST` | `/admin/agents/{agent_id}/reset-config` | Reset `config` from `configs/agents/{agent_id}.config.json` |

```python
class AgentAdminOut(BaseModel):
    id: UUID
    agent_id: str           # e.g. "kyc_compliance"
    name: str
    role: str
    capabilities: list[str]
    config: dict[str, Any]
    is_active: bool

class UpdateAgentConfigRequest(BaseModel):
    config: dict[str, Any] | None = None
    is_active: bool | None = None
```

`POST /admin/agents/{agent_id}/reset-config` reads `configs/agents/{agent_id}.config.json` from disk and writes it back to the DB row's `config` column.

#### Frontend — `frontend/src/features/admin/AgentConfigEditor.tsx` (new)

- Left panel: list of 8 agents as compact cards (name, role badge, active/inactive dot).
- Clicking an agent opens a detail panel (right side):
  - Agent name + role badge + capability chips (read-only)
  - `is_active` toggle with `ConfirmationModal` (warn: "Deactivating this agent will stop it from processing tasks")
  - JSON config editor: `<textarea>` with monospace font, JSON syntax validation on blur; "Save Config" button calls `PUT /admin/agents/{agent_id}`
  - "Reset to Defaults" button calls `POST /admin/agents/{agent_id}/reset-config` with confirmation modal

#### Hooks — `frontend/src/hooks/useAdminAgents.ts` (new)
- `useAdminAgents()` — TanStack Query
- `useUpdateAgentConfig()`, `useResetAgentConfig()` — mutations; invalidate `['admin', 'agents']` on success

---

### 2C — Skills Configuration Tab

Skills are static Python classes. Their tunable parameters (thresholds, flags) are stored in `admin_config` under a new `skill_config` namespace.

#### Backend — `backend/app/api/routers/admin/skills_config.py` (new file)

Skills catalog is code-defined (not DB-backed). The catalog maps each skill ID to its human-readable name, description, and the schema of its configurable parameters.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/skills` | Returns catalog + current param values for each skill |
| `PUT` | `/admin/skills/{skill_id}` | Save updated params to `admin_config` (namespace: `skill_config`) |
| `POST` | `/admin/skills/{skill_id}/reset` | Clear params; skill reverts to hardcoded defaults |

`SkillAdminOut`:
```python
class SkillParamDef(BaseModel):
    key: str
    label: str
    type: Literal["float", "int", "bool"]
    default: float | int | bool
    min: float | None = None
    max: float | None = None
    description: str

class SkillAdminOut(BaseModel):
    skill_id: str
    name: str
    description: str
    params: list[SkillParamDef]    # schema
    current_config: dict[str, Any] # values (from admin_config)
```

Initial skill catalog (hardcoded in the router):

| skill_id | Configurable params |
|----------|---------------------|
| `escalation` | `escalation_threshold` (float, 0–1, default 0.7), `use_llm_narrative` (bool, default True) |
| `product_suitability` | `min_suitability_score` (float, 0–1, default 0.5), `use_llm_assessment` (bool, default True) |
| `decision_reasoning` | `chain_of_thought_depth` (int, 1–5, default 3) |
| `information_extraction` | `max_fields_per_call` (int, 1–20, default 10) |
| `status_summarisation` | `use_llm_enhancement` (bool, default True) |
| `clarification` | `max_questions` (int, 1–10, default 5) |

**Wire params into skill execution:** Each skill's `_execute()` reads from `admin_config_repository.load("skill_config")` (cached on startup via `load_from_db()` pattern) to override its hardcoded defaults. This requires a light update to 3–4 skill files.

**`backend/app/services/admin/admin_config_repository.py`** — add constant:
```python
NAMESPACE_SKILL_CONFIG = "skill_config"
```

**`backend/app/main.py`** — add `load_skill_config()` call to `on_startup()`.

#### Frontend — `frontend/src/features/admin/SkillConfigEditor.tsx` (new)

- Grid of 6 skill cards (2 columns): skill name, description, "configured" badge when params differ from defaults.
- Clicking a card opens a param editor panel:
  - `float` params → range slider + number input, clamped to [min, max]
  - `bool` params → toggle switch
  - `int` params → number stepper
  - "Save" button → `PUT /admin/skills/{skill_id}`
  - "Reset to defaults" button → `POST /admin/skills/{skill_id}/reset`

#### Hooks — `frontend/src/hooks/useAdminSkills.ts` (new)
- `useAdminSkills()` — TanStack Query
- `useUpdateSkillConfig()`, `useResetSkillConfig()` — mutations; invalidate `['admin', 'skills']` on success

---

### Admin Config Route Update

`frontend/src/routes/AdminConfig.tsx` — add three new tab entries:
- `Onboarding Questions` → `<QuestionnaireEditor />`
- `Agents` → `<AgentConfigEditor />`
- `Skills` → `<SkillConfigEditor />`

New interfaces in `frontend/src/lib/api.ts`:
- `QuestionAdminOut`, `CreateQuestionRequest`, `AgentAdminOut`, `UpdateAgentConfigRequest`, `SkillAdminOut`, `SkillParamDef`

### Summary of New Files (Action 2)

| File | Type |
|------|------|
| `backend/app/api/routers/admin/questionnaire.py` | New backend router |
| `backend/app/api/routers/admin/agents_config.py` | New backend router |
| `backend/app/api/routers/admin/skills_config.py` | New backend router |
| `backend/app/main.py` | Register 3 routers + `load_skill_config()` in startup |
| `backend/app/services/admin/admin_config_repository.py` | Add `NAMESPACE_SKILL_CONFIG` constant |
| `backend/app/agents/skills/*.py` | Light update (3–4 files) to read skill params from admin config |
| `frontend/src/features/admin/QuestionnaireEditor.tsx` | New component |
| `frontend/src/features/admin/AgentConfigEditor.tsx` | New component |
| `frontend/src/features/admin/SkillConfigEditor.tsx` | New component |
| `frontend/src/hooks/useAdminQuestionnaire.ts` | New hook |
| `frontend/src/hooks/useAdminAgents.ts` | New hook |
| `frontend/src/hooks/useAdminSkills.ts` | New hook |
| `frontend/src/lib/api.ts` | Add new interfaces |
| `frontend/src/routes/AdminConfig.tsx` | Add 3 tabs |

---

## Action 3 — Client Document Upload Notification

### Goal
When the onboarding questionnaire is fully completed, send the client a notification (in-app + email) asking them to upload required documents via the portal.

### Trigger Point
`ConversationCoordinator.handle_message()` in `backend/app/services/conversation/conversation_coordinator.py` already signals `ADVANCE_STAGE → KYC` when `session.collection_complete` is True (post-streaming step). This is the right place to add the notification trigger — immediately after the advance-stage signal.

### Implementation

**`backend/app/agents/notification/notification_templates.py`** — add two templates:

```python
"document_upload_request": NotificationTemplate(
    template_id="document_upload_request",
    channel="email",
    subject_tmpl="Action Required — Please upload your documents for $case_name",
    body_tmpl=(
        "Dear $client_name,\n\n"
        "Thank you for completing your onboarding questionnaire for $case_name!\n\n"
        "To proceed with your $products application, please log in to the GlideGate "
        "client portal and upload the following documents:\n\n"
        "$required_documents\n\n"
        "Our team will review your documents and keep you updated on your progress.\n\n"
        "Kind regards,\nThe GlideGate Onboarding Team"
    ),
),
"document_upload_request_inapp": NotificationTemplate(
    template_id="document_upload_request_inapp",
    channel="in_app",
    subject_tmpl="Please upload your documents",
    body_tmpl=(
        "Your form is complete! Please upload the required documents "
        "to proceed with your $products application."
    ),
),
```

**`backend/app/services/conversation/conversation_coordinator.py`** — add private method and wire it:

```python
async def _send_document_upload_notification(
    self,
    case_id: UUID,
    client_id: UUID,
    state: OnboardingState,
) -> None:
    """Fires SEND_NOTIFICATION to NotificationAgent after questionnaire completion."""
    products_str = ", ".join(state.selected_products) if state.selected_products else "your product"
    required_docs = (
        "• Identity Document (Passport or National ID)\n"
        "• Proof of Address (utility bill or bank statement)\n"
        "• Financial Statement (last 3 months)\n"
        "• Source of Funds Declaration"
    )
    for template_id in ("document_upload_request", "document_upload_request_inapp"):
        task = TaskPacket(
            id=uuid4(),
            from_agent=AgentID.CUSTOMER_SERVICE,
            to_agent=AgentID.NOTIFICATION,
            task_type=TaskType.SEND_NOTIFICATION,
            case_id=case_id,
            client_id=client_id,
            priority="NORMAL",
            payload={
                "template_id": template_id,
                "recipient_id": str(client_id),
                "variables": {
                    "client_name": state.client_data.get("full_name", "Valued Client"),
                    "case_name": str(case_id)[:8].upper(),
                    "products": products_str,
                    "required_documents": required_docs,
                },
            },
            expected_schema="NotificationResult",
            created_at=datetime.utcnow(),
            ttl=3600,
        )
        await self._bus.publish(task)
```

In `handle_message()`, after the existing `ADVANCE_STAGE` signal block, add:
```python
asyncio.create_task(
    self._send_document_upload_notification(case_id, client_id, state)
)
```

### Files
| File | Action |
|------|--------|
| `backend/app/agents/notification/notification_templates.py` | Add 2 notification templates |
| `backend/app/services/conversation/conversation_coordinator.py` | Add `_send_document_upload_notification()` + wire it |

No DB migrations. No frontend changes. The existing in-app notification rendering in the client portal already displays `SEND_NOTIFICATION` results via the notifications table and the `GET /api/notifications` endpoint (if wired) — or via the socket `NOTIFICATION_SENT` event.

---

## Action 4 — Dynamic Stage Insertion: Approach Definition

### Problem
The `OnboardingStage` StrEnum and `_TRANSITIONS` dict in `workflow_state_machine.py` are hardcoded. Inserting a new stage today requires editing `a2a_types.py`, `workflow_state_machine.py`, and `orchestrator_agent.py` — three files across two layers — before even writing the new agent.

### Design Goal
Adding a new stage should require:
1. Writing a new agent class (unavoidable)
2. Calling `stage_registry.register(StageDefinition(...))` at startup
3. No edits to any existing agent or core framework file

---

### Proposed Design

#### A. String-Based Stage IDs (no StrEnum change required)

`OnboardingStage` StrEnum stays as-is for the six built-in stages. Dynamic stages are plain strings (e.g. `"SALES_MANAGER_REVIEW"`). The `WorkflowStateMachine` already accepts `OnboardingStage` for transitions — update the type annotation to `str` (StrEnum is a subclass of str, so this is backward-compatible). `OnboardingCase.current_stage` column in the DB is already `VARCHAR`, so no migration is needed for the column itself.

**One migration needed:** relax or remove the `CHECK (current_stage IN (...))` constraint on `onboarding_cases` so custom stage strings can be stored. This is a targeted ALTER TABLE — no data change.

```sql
-- backend/alembic/versions/0005_relax_stage_constraint.py
ALTER TABLE onboarding_cases DROP CONSTRAINT IF EXISTS onboarding_cases_current_stage_check;
```

---

#### B. `StageDefinition` Dataclass

New file: `backend/app/agents/orchestrator/stage_registry.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass
class StageDefinition:
    stage_id: str              # unique string key, e.g. "SALES_MANAGER_REVIEW"
    name: str                  # human-readable label
    entry_task_type: str       # task type the orchestrator dispatches on entry
    target_agent: str          # AgentID string of the handling agent
    insert_after: str          # built-in (or custom) stage that precedes this one
    insert_before: str         # built-in (or custom) stage that follows this one
    timeout_seconds: int = 86400
    payload_factory: Callable[[dict], dict] | None = None
    # Called with (shared_context_dict) → extra task payload keys
```

---

#### C. `StageRegistry` Singleton

```python
class StageRegistry:
    def __init__(self) -> None:
        self._stages: dict[str, StageDefinition] = {}

    def register(self, stage: StageDefinition) -> None:
        if stage.stage_id in self._stages:
            raise ValueError(f"Stage '{stage.stage_id}' is already registered")
        self._stages[stage.stage_id] = stage

    def get(self, stage_id: str) -> StageDefinition | None:
        return self._stages.get(stage_id)

    def all(self) -> list[StageDefinition]:
        return list(self._stages.values())

stage_registry = StageRegistry()
```

---

#### D. Dynamic Transition Patching in `WorkflowStateMachine`

`WorkflowStateMachine._build_transitions()` constructs the transition map at init time by starting from the built-in `_BASE_TRANSITIONS` and patching in all registered custom stages:

```python
_BASE_TRANSITIONS: dict[str, set[str]] = {
    "INTAKE":             {"KYC"},
    "KYC":                {"PARALLEL_PRODUCTS", "ESCALATED"},
    "PARALLEL_PRODUCTS":  {"REVIEW", "COMPLETE", "ESCALATED"},
    "REVIEW":             {"COMPLETE", "ESCALATED", "KYC"},
    "COMPLETE":           set(),
    "ESCALATED":          {"REVIEW", "KYC", "COMPLETE"},
}

def _build_transitions(self) -> dict[str, set[str]]:
    transitions: dict[str, set[str]] = {k: set(v) for k, v in _BASE_TRANSITIONS.items()}
    for stage_def in stage_registry.all():
        # Remove the direct link that the new stage intercepts
        transitions.setdefault(stage_def.insert_after, set()).discard(stage_def.insert_before)
        # Insert the new stage into the chain
        transitions[stage_def.insert_after].add(stage_def.stage_id)
        transitions[stage_def.stage_id] = {stage_def.insert_before}
    return transitions
```

`WorkflowStateMachine.__init__()` calls `_build_transitions()` and assigns the result. The `can_transition()` and `transition()` methods use the patched map — no other changes.

---

#### E. Orchestrator Dynamic Routing

`OrchestratorAgent._route_to_stage(stage, ctx)` is updated to check `stage_registry` before its built-in switch:

```python
async def _route_to_stage(self, stage: str, ctx: OnboardingState) -> None:
    # Dynamic stages first
    stage_def = stage_registry.get(stage)
    if stage_def:
        payload = stage_def.payload_factory(ctx.dict()) if stage_def.payload_factory else {}
        await self.send_task(
            task_type=stage_def.entry_task_type,
            to_agent=stage_def.target_agent,
            payload=payload,
        )
        return
    # Built-in routing (unchanged) ...
    match stage:
        case OnboardingStage.INTAKE:
            ...
```

---

#### F. New Agent Exit Protocol (Contract for Stage Authors)

A new agent signals completion by publishing `ADVANCE_STAGE` — the same convention all existing agents follow:

```python
# Inside the new agent's process() method, on completion:
await self.send_task(
    task_type=TaskType.ADVANCE_STAGE,
    to_agent=AgentID.ORCHESTRATOR,
    payload={
        "current_stage": "SALES_MANAGER_REVIEW",
        "outcome": "APPROVED",   # or "REJECTED"
    },
)
```

The orchestrator's existing `_handle_advance_stage()` handler transitions the FSM to `insert_before` and routes accordingly. No change to that handler.

---

#### G. Example — Adding "SALES_MANAGER_REVIEW" (Stage 2 from the Backlog)

```python
# backend/app/plugins/sales_manager_stage.py  (new file — isolated, zero coupling)
from app.agents.orchestrator.stage_registry import StageDefinition, stage_registry

stage_registry.register(StageDefinition(
    stage_id="SALES_MANAGER_REVIEW",
    name="Sales Manager Review",
    entry_task_type="sales_manager_review",
    target_agent="sales_manager",
    insert_after="INTAKE",
    insert_before="KYC",
    timeout_seconds=172800,           # 48-hour SLA
))
```

```python
# backend/app/main.py — add ONE import at the bottom of imports:
import app.plugins.sales_manager_stage  # noqa: F401 — side-effect registration
```

Then create `backend/app/agents/sales_manager/sales_manager_agent.py` (new agent handling `"sales_manager_review"` task type, publishing `ADVANCE_STAGE` on completion). Zero other files change.

---

#### H. Files Required for Full Dynamic Stage Support

| File | Action |
|------|--------|
| `backend/app/agents/orchestrator/stage_registry.py` | New — `StageDefinition` + `StageRegistry` + singleton |
| `backend/app/agents/orchestrator/workflow_state_machine.py` | Update — `_build_transitions()`, relax type annotations to `str` |
| `backend/app/agents/orchestrator/orchestrator_agent.py` | Update — `_route_to_stage()` checks registry first |
| `backend/alembic/versions/0005_relax_stage_constraint.py` | New migration — drop CHECK constraint on `current_stage` |
| `backend/app/plugins/` | New directory — one file per custom stage (e.g. `sales_manager_stage.py`) |

**Existing agents:** zero changes. The FSM and orchestrator routing are fully backward-compatible; built-in stages continue to work exactly as before.

---

### Summary Table

| Action | Backend Changes | Frontend Changes | New Files | Migration |
|--------|----------------|-----------------|-----------|-----------|
| 1 — Replay Button | None | 3 files (traceStore + 2 components) | `ReplayControls.tsx` | None |
| 2 — Admin Config Tabs | 3 new routers + 4 light edits | 3 new editors + 3 hooks + 2 updates | 9 | None |
| 3 — Document Notification | 2 files | None | None | None |
| 4 — Dynamic Stages | 3 updated core files + registry | None | `stage_registry.py` + migration | ALTER TABLE |

---

### Suggested Sequencing

1. **Action 3** (Document Notification) — smallest change, highest user-facing value, good quick win.
2. **Action 1** (Replay Button) — self-contained frontend, safe to ship independently.
3. **Action 4** (Dynamic Stage Infra) — foundational; implement before building Stage 2/4/5/7 agents.
4. **Action 2** (Admin Config Tabs) — larger surface area; build after replay and notification are validated.
