# Task View Feature — Implementation Plan

## Context

The advisor and sales manager workspaces currently only show a Case view (CaseListTable). There is no unified task-action surface. The request is to add a **Task View** tab alongside the Case View that surfaces actionable items generated from two workflow events:

1. **Document uploaded** → create a `PENDING` task assigned to the **advisor** (to review/approve the document).
2. **Case enters SALES_REVIEW** → create a `PENDING` task assigned to the **sales manager** (to approve or reject the case).

Clicking a task row **opens the existing case tab** for that case. Inside the case page, the content area gains a new `Overview` tab prepended to the existing `[Documents] [Application]` tabs — so the inner tab bar becomes `Overview (N)` | `Documents` | `Application`. The Overview tab shows a Tasks section (Pending / Completed sub-tabs). Clicking a task row opens a closeable task sub-tab alongside with a two-column detail view. When the task has a linked document, the left card shows the document and the existing `DocumentDetailDrawer` can be opened from it. Minimum scroll throughout.

---

## Architecture Overview

```
DB:         workspace_tasks (new table)
Backend:    app/models/tasks.py
            app/services/task/task_service.py
            app/api/routers/tasks.py
            ── hooks into ──
            app/services/document/document_upload_service.py  (create advisor task)
            app/services/sales_review/sales_review_service.py (create SM task)
Socket:     TASK_CREATED, TASK_UPDATED events via socket_emitter
Frontend:   src/hooks/useTasks.ts
            src/features/advisor/TaskListPanel.tsx
            src/features/advisor/TaskActionPanel.tsx   ← injected into existing case content view
            src/routes/AdvisorWorkspace.tsx            ← add Tasks tab to dashboard
```

---

## Step 1 — Backend Model (`workspace_tasks`)

**File:** `backend/app/models/tasks.py` *(new)*

```python
class WorkspaceTask(Base):
    __tablename__ = "workspace_tasks"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('DOCUMENT_REVIEW','SALES_REVIEW')",
            name="wt_type_chk"
        ),
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED')",
            name="wt_status_chk"
        ),
        CheckConstraint(
            "assignee_role IN ('advisor','sales_manager')",
            name="wt_role_chk"
        ),
    )

    id:            UUID PK, default uuid4
    case_id:       FK → onboarding_cases.id, indexed
    assignee_id:   UUID, nullable, indexed   # advisor or SM user id
    assignee_role: str(20)                   # 'advisor' | 'sales_manager'
    task_type:     str(30)                   # 'DOCUMENT_REVIEW' | 'SALES_REVIEW'
    title:         str(200)                  # human-readable e.g. "Review Passport.pdf"
    status:        str(20), default='PENDING'
    document_id:   UUID, nullable, FK → documents.id   # set for DOCUMENT_REVIEW tasks
    review_id:     UUID, nullable            # set for SALES_REVIEW tasks (SalesManagerReview.id)
    decision_notes:str, nullable
    decided_by:    UUID, nullable            # user who acted
    decided_at:    datetime, nullable
    extra_metadata:JSONB, default={}
    created_at:    datetime, utcnow
    updated_at:    datetime, utcnow onupdate

    # Relationships
    case:     → OnboardingCase
    document: → Document (nullable)
```

Register in `backend/app/models/__init__.py`.

---

## Step 2 — Alembic Migration

**File:** `backend/alembic/versions/<hash>_add_workspace_tasks.py` *(new)*

```python
def upgrade():
    op.create_table('workspace_tasks',
        sa.Column('id',             postgresql.UUID, primary_key=True),
        sa.Column('case_id',        postgresql.UUID, sa.ForeignKey('onboarding_cases.id')),
        sa.Column('assignee_id',    postgresql.UUID, nullable=True),
        sa.Column('assignee_role',  sa.String(20)),
        sa.Column('task_type',      sa.String(30)),
        sa.Column('title',          sa.String(200)),
        sa.Column('status',         sa.String(20), default='PENDING'),
        sa.Column('document_id',    postgresql.UUID, sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('review_id',      postgresql.UUID, nullable=True),
        sa.Column('decision_notes', sa.Text,         nullable=True),
        sa.Column('decided_by',     postgresql.UUID, nullable=True),
        sa.Column('decided_at',     sa.DateTime,     nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB, default={}),
        sa.Column('created_at',     sa.DateTime),
        sa.Column('updated_at',     sa.DateTime),
    )
    op.create_index('ix_workspace_tasks_case_id',      'workspace_tasks', ['case_id'])
    op.create_index('ix_workspace_tasks_assignee_id',  'workspace_tasks', ['assignee_id'])
    op.create_index('ix_workspace_tasks_status',       'workspace_tasks', ['status'])
    op.create_check_constraint('wt_type_chk',  'workspace_tasks', "task_type IN ('DOCUMENT_REVIEW','SALES_REVIEW')")
    op.create_check_constraint('wt_status_chk','workspace_tasks', "status IN ('PENDING','APPROVED','REJECTED')")
    op.create_check_constraint('wt_role_chk',  'workspace_tasks', "assignee_role IN ('advisor','sales_manager')")
```

---

## Step 3 — Task Service

**File:** `backend/app/services/task/task_service.py` *(new)*

```python
class TaskService:
    async def create_task(
        self, *, case_id, assignee_id, assignee_role, task_type,
        title, document_id=None, review_id=None, db
    ) -> WorkspaceTask:
        """Persist task, emit TASK_CREATED socket event."""

    async def decide(
        self, *, task_id, decision: Literal['APPROVED','REJECTED','MORE_INFO_REQUESTED'],
        decision_notes, decided_by, db
    ) -> WorkspaceTask:
        """
        Set task.status = decision, record decided_by + decided_at.
        Emit TASK_UPDATED socket event.

        NOTE — document status is NOT updated here for DOCUMENT_REVIEW tasks.
        The frontend calls PATCH /documents/{id} directly (reusing useUpdateDocumentStatus,
        same as DocumentDetailDrawer) before calling this endpoint. This keeps document
        status transitions identical to the drawer flow.

        For SALES_REVIEW tasks:
            Delegate to sales_review_service.decide(review_id, decision, ...)
        """

    async def list_tasks(
        self, *, assignee_role, assignee_id=None, case_id=None, db
    ) -> list[WorkspaceTask]:
        """Filter by role; optionally by assignee or case."""

task_service = TaskService()
```

Socket emitter calls needed (add to `socket_emitter.py`):
- `socket_emitter.task_created(case_id, payload)`
- `socket_emitter.task_updated(case_id, payload)`

---

## Step 4 — Hook Task Creation into Upload Service

**File:** `backend/app/services/document/document_upload_service.py`

After `await db.flush()` (line ~200, after the doc record is persisted), add a fire-and-forget background task:

```python
asyncio.create_task(
    _create_document_task(
        case_id=case_id,
        document_id=doc.id,
        filename=filename,
    ),
    name=f"task-doc-{doc.id}",
)
```

New helper (uses its own `AsyncSessionLocal()` context, same pattern as `_post_decision_workflow`):
```python
async def _create_document_task(case_id, document_id, filename):
    async with AsyncSessionLocal() as db:
        await task_service.create_task(
            case_id=case_id,
            assignee_id=None,           # broadcast to all advisors on this case
            assignee_role='advisor',
            task_type='DOCUMENT_REVIEW',
            title=f"Review uploaded document: {filename}",
            document_id=document_id,
            db=db,
        )
```

---

## Step 5 — Hook Task Creation into Sales Review Service

**File:** `backend/app/services/sales_review/sales_review_service.py`

Inside `create_review()`, after `await db.commit()` (line ~71), add:

```python
asyncio.create_task(
    self._create_sm_task(review_id=str(review.id), case_id=case_id)
)
```

New helper:
```python
async def _create_sm_task(self, review_id: str, case_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        await task_service.create_task(
            case_id=case_id,
            assignee_id=None,          # any sales manager can pick it up
            assignee_role='sales_manager',
            task_type='SALES_REVIEW',
            title="Sales Manager Review Required",
            review_id=review_id,
            db=db,
        )
```

---

## Step 6 — API Router

**File:** `backend/app/api/routers/tasks.py` *(new)*

```
GET  /tasks
     Query params: role (advisor|sales_manager), case_id (optional)
     Auth: advisor or sales_manager
     Returns: list[TaskOut]

GET  /tasks/{task_id}
     Returns task + related document/review snapshot

PATCH /tasks/{task_id}/decide
     Body: { decision: 'APPROVED'|'REJECTED'|'MORE_INFO_REQUESTED', decision_notes?: str }
     Calls task_service.decide(...)
     Returns: TaskOut
```

`TaskOut` schema:
```python
class TaskOut(BaseModel):
    id, case_id, assignee_role, task_type, title, status
    document_id, review_id
    case_name, client_name          # joined from case/client
    created_at, decided_at
    # Returned only by GET /tasks/{task_id}:
    document_snapshot: dict | None  # filename, status, category, storage_path
    review_snapshot: dict | None    # ai_risk_summary, risk_score, case_snapshot
```

Register router in `backend/app/main.py`.

---

## Step 7 — Frontend Hook

**File:** `frontend/src/hooks/useTasks.ts` *(new)*

```typescript
export function useTasks(role: 'advisor' | 'sales_manager') {
  return useQuery({ queryKey: ['tasks', role], queryFn: () => api.getTasks(role) })
}

export function useTaskDetail(taskId: string | null) {
  return useQuery({
    queryKey: ['tasks', 'detail', taskId],
    queryFn: () => api.getTask(taskId!),
    enabled: !!taskId,
  })
}

export function useDecideTask() {
  return useMutation({
    mutationFn: ({ taskId, decision, notes }) =>
      api.decideTask(taskId, { decision, decision_notes: notes }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  })
}
```

Add API client methods to `frontend/src/lib/api.ts`:
- `getTasks(role)` → `GET /tasks?role=<role>`
- `getTask(id)` → `GET /tasks/{id}`
- `decideTask(id, body)` → `PATCH /tasks/{id}/decide`

---

## Step 8 — TaskListPanel Component

**File:** `frontend/src/features/advisor/TaskListPanel.tsx` *(new)*

Modelled after `CaseListTable.tsx` (same AG Grid / BaseGrid pattern). Columns:

| Column  | Source field        | Notes                              |
|---------|---------------------|------------------------------------|
| CLIENT  | `client_name`       | Bold, same as CaseListTable        |
| CASE    | `case_id`           | Short UUID prefix                  |
| TASK    | `title`             | Truncated                          |
| STAGE   | `task_type` badge   | Client Enrollment / KYC style      |
| STATUS  | `status` badge      | Pending=amber, Approved=green, Rejected=red |
| CREATED | `created_at`        | Relative time (same helper)        |
| Action  | "Open in Case" btn  | Calls `openCaseTab` + `setActiveTask` |

Clicking a row or "Open in Case": calls `openCaseTab(caseId, clientId, caseName)` + `setActiveTask(taskId)` from `workspaceStore`.

Role filtering: reads `useAuthStore().user.role` and passes it to `useTasks(role)`.

---

## Step 9 — Replace Case Content Area with Overview + Tasks

The right-side content panel of the case tab currently shows `[Documents] [Application]` tabs. **Replace this entire area** with a new `CaseOverviewPanel` that shows an `Overview` tab containing the task list.

### 9a — Visual Layout: Overview Tab (task list)

The inner tab bar is **`Overview (N)` | `Documents` | `Application`** — Overview is prepended; the existing Documents and Application tabs are preserved unchanged.

The content area has **three zones** stacked top-to-bottom:
1. **Case summary strip** (~80px, pinned at the very top — above the tab bar, always visible regardless of which tab is active).
2. **Inner tab bar** — `Overview (N)` | `Documents` | `Application` | task sub-tabs.
3. **Tab content** — fills remaining height.

```
┌─────────────┬──────────────────────────────────────────────────────────┐
│ Left sidebar │  Content area                                            │
│ CASE INFO    │                                                          │
│ PROGRESS     │  ┌── CASE SUMMARY STRIP (~80px, always visible) ──────┐ │
│  ✓ Intake    │  │  Giri Prasath V 28       Stage: REVIEW      90%   │ │
│  ● Advisor   │  │  📦 Cash Account ·············· PENDING  0/0  0%  │ │
│    Review    │  └────────────────────────────────────────────────────┘ │
│    ACTIVE    │                                                          │
│  3 KYC       │  [Overview (2)]  [Documents]  [Application]  ← tab bar │
│  4 Products  │  ────────────────────────────────────────────────────── │
│  5 Complete  │                                                          │
│              │  Tasks  2   [2 pending]                              ∧  │
│              │  ──────────────────────────────────────────────────────  │
│              │  [Pending (2)]   [Completed (0)]                         │
│              │                                                          │
│              │  ┌────────────────────────────────────────────────────┐ │
│              │  │ Enrollment Form Review [Client Enrollment] [Pending]│ │
│              │  │ Assignee: Marcus Chen · Created: Nov 20, 2024      │ │
│              │  │                                   [Review Task >]  │ │
│              │  ├────────────────────────────────────────────────────┤ │
│              │  │ KYC Review             [KYC]          [Pending]    │ │
│              │  │ Assignee: Priya Sharma · Created: Nov 8, 2024      │ │
│              │  │                                   [Review Task >]  │ │
│              │  └────────────────────────────────────────────────────┘ │
└─────────────┴──────────────────────────────────────────────────────────┘
```

**Case summary strip implementation:**
- Rendered as a `shrink-0` strip at the top of `CaseOverviewPanel`, **outside and above** the inner tab bar.
- Reuses the existing case header JSX from `DocumentWorkspacePanel` (case name, stage badge, completion %, product tracks collapsed to one compact line each).
- `text-sm` / reduced padding to stay ~80px tall.
- Visible on **all tabs** (Overview, Documents, Application, task sub-tabs) — it never scrolls away.

### 9b — Visual Layout: Task Detail Sub-Tab (opens on "Review Task >")

Clicking a task row opens it as a **closeable sub-tab** appended after Documents/Application (e.g. `Overview (1)` | `Documents` | `Application` | `Enrollment Form Review ×`).

```
┌─────────────┬──────────────────────────────────────────────────────────┐
│ Left sidebar │  [Overview(1)] [Documents] [Application] [Enroll. Rev ×]│
│ CASE INFO    │  ──────────────────────────────────────────────────────  │
│ PROGRESS     │                                                          │
│  ✓ Intake    │  ┌────────────────────────┐  ┌──────────────────────┐   │
│  ● Advisor   │  │ ← document preview     │  │ TASK STATUS          │   │
│    Review    │  │   (if doc linked)      │  │ [Pending]            │   │
│    KYC       │  │   OR                   │  │ Created Nov 20, 2024 │   │
│    Products  │  │ "No form or document   │  └──────────────────────┘   │
│    Complete  │  │  linked to this task." │                              │
│              │  │                        │  ┌──────────────────────┐   │
│              │  │  [Open Document ↗]     │  │ ACTIONS              │   │
│              │  │  (if doc linked →      │  │ ✓ Approve            │   │
│              │  │   opens existing       │  │ ✗ Reject             │   │
│              │  │   DocumentDetailDrawer)│  │ ⟳ Request Info       │   │
│              │  └────────────────────────┘  └──────────────────────┘   │
│              │  ┌────────────────────────┐                              │
│              │  │ TASK DETAILS           │                              │
│              │  │ Task ID   task-038     │                              │
│              │  │ Type  Enrollment Rev.  │                              │
│              │  │ Stage [Client Enrol.]  │                              │
│              │  │ Assigned  Marcus Chen  │                              │
│              │  │ Created   Nov 20, 2024 │                              │
│              │  └────────────────────────┘                              │
└─────────────┴──────────────────────────────────────────────────────────┘
```

Left column (2 cards stacked):
1. **Document/Form preview card**
   - If `document_id` set: shows filename, category, status badge + an **"Open Document ↗"** button that calls the existing `setActiveDocument(doc.id)` + `setDrawerOpen(true)` from `workspaceStore` to open `DocumentDetailDrawer` (already exists — zero new code for the drawer itself).
   - If no document: shows "No form or document linked to this task."
2. **Task Details card** — Task ID, Type, Stage badge, Assigned To, Created

Right column (2 cards stacked):
1. **Task Status card** — status badge (Pending / Approved / Rejected) + created date
2. **Actions card** — three full-width buttons: Approve (green), Reject (red), Request Information (amber).

**Approve / Reject behaviour for `DOCUMENT_REVIEW` tasks — must mirror the drawer exactly:**

The drawer (`DocumentDetailDrawer`) uses `useUpdateDocumentStatus(caseId)` → `PATCH /documents/{docId} { status }` with a `ConfirmationModal` before applying. The `StatusEditor` maps:
- **Approve** → `status: 'APPROVED'`
- **Reject** → `status: 'NEEDS_REVISION'`

The task Actions card reuses **the same hook and the same confirmation modal**:

```tsx
// TaskDetailView.tsx — Actions card (DOCUMENT_REVIEW)
const statusMutation = useUpdateDocumentStatus(caseId)   // ← reuse existing hook
const decideMutation = useDecideTask()

function handleApprove() {
  // Step 1: update document status (same as drawer)
  statusMutation.mutate({ docId: task.document_id, status: 'APPROVED' })
  // Step 2: mark task as decided
  decideMutation.mutate({ taskId: task.id, decision: 'APPROVED' })
}

function handleReject() {
  // Step 1: update document status to NEEDS_REVISION (same as drawer)
  statusMutation.mutate({ docId: task.document_id, status: 'NEEDS_REVISION' })
  // Step 2: mark task as decided
  decideMutation.mutate({ taskId: task.id, decision: 'REJECTED' })
}
```

A `ConfirmationModal` (existing component) is shown before each action — same as `StatusEditor` does in the drawer.

On success:
- Task status badge → Approved / Rejected
- Document status in the Documents tab updates in real-time (same `qk.documents(caseId)` query invalidation that `useUpdateDocumentStatus` already triggers)
- Action buttons become disabled

**`SALES_REVIEW` tasks — Approve/Reject must mirror `SalesReviewPanel` exactly:**

`SalesReviewPanel` uses:
- `useDecideSalesReview()` → `POST /sales-reviews/{reviewId}/decide { decision, decision_notes }`
- `DecisionModal` — a custom modal with required notes for `REJECTED` and `MORE_INFO_REQUESTED`, optional for `APPROVED`
- On approve: shows "Approve — Initiate KYC" label + triggers KYC immediately via backend
- On reject: shows "Reject Application" + **notes required**
- On more info: shows "Request More Information" + **notes required**

The task Actions card for `SALES_REVIEW` reuses **the same hook and the same `DecisionModal`**:

```tsx
// TaskDetailView.tsx — Actions card (SALES_REVIEW)
const salesDecideMutation = useDecideSalesReview()   // ← reuse existing hook
const decideMutation = useDecideTask()

function handleDecision(notes: string) {
  // Step 1: call sales review decide (same as SalesReviewPanel)
  salesDecideMutation.mutate(
    { reviewId: task.review_id, decision: pendingDecision, decision_notes: notes || undefined },
    {
      onSuccess: () => {
        // Step 2: mark task as decided
        decideMutation.mutate({ taskId: task.id, decision: pendingDecision })
        setPendingDecision(null)
      }
    }
  )
}
```

`DecisionModal` is extracted from `SalesReviewPanel.tsx` into a shared component (e.g. `features/advisor/DecisionModal.tsx`) so both `SalesReviewPanel` and `TaskDetailView` import it from the same place — no duplication.

On success:
- Task status badge → Approved / Rejected / More Info Requested
- `salesReviewQk.all` query invalidated (same as `useDecideSalesReview` `onSuccess` already does)
- Case stage advances to KYC (backend handles this, same as today)
- Action buttons become disabled

### 9c — New Files

**`frontend/src/features/advisor/CaseOverviewPanel.tsx`** *(new — wraps existing content + adds Overview tab)*

```tsx
// Props: caseId: string
// State:
//   activeInnerTab: 'overview' | 'documents' | 'application' | taskId
//   openTaskTabs: TaskOut[]   (task sub-tabs opened by user)
//   pendingFilter: 'pending' | 'completed'
//
// Inner tab bar order:
//   Overview (N) | Documents | Application | [task tabs, closeable] ...
//
// Overview tab content:
//   Section header: "Tasks  N  [N pending]" + chevron
//   Sub-tabs: Pending | Completed
//   <TaskRow> list for current sub-tab
//
// Documents tab content:
//   Renders existing <DocumentWorkspacePanel> content unchanged
//   DocumentDetailDrawer continues to work as before
//
// Application tab content:
//   Renders existing application/form view unchanged
//
// Task sub-tab content (activeInnerTab === taskId):
//   <TaskDetailView task={...} />  (two-column layout from 9b)
```

**`frontend/src/features/advisor/TaskRow.tsx`** *(new)*

```tsx
// Props: task: TaskOut, onOpen: (taskId: string) => void
// Compact row (~56px):
//   title (bold) · task_type badge · status badge · "Review Task >" btn
//   Assignee · Created date (small text)
// "Review Task >" → calls onOpen(task.id) → CaseOverviewPanel adds inner tab
```

**`frontend/src/features/advisor/TaskDetailView.tsx`** *(new)*

```tsx
// Props: task: TaskOut (full detail with document_snapshot)
// Two-column layout (left: 2 stacked cards, right: 2 stacked cards)
// Uses useDecideTask() for action buttons
// On success: status card badge updates; action buttons disabled
```

### 9d — Wiring into AdvisorWorkspace

Replace `<DocumentWorkspacePanel>` with `<CaseOverviewPanel>` in the case tab branch. `DocumentDetailDrawer` stays mounted alongside — `CaseOverviewPanel` passes through the `setActiveDocument` / `setDrawerOpen` calls from `workspaceStore` exactly as `DocumentWorkspacePanel` does today:

```tsx
// Before:
{selectedCaseId && <DocumentWorkspacePanel caseId={selectedCaseId} />}
{selectedCaseId && isDrawerOpen && <DocumentDetailDrawer caseId={selectedCaseId} />}

// After:
{selectedCaseId && <CaseOverviewPanel caseId={selectedCaseId} />}
{selectedCaseId && isDrawerOpen && <DocumentDetailDrawer caseId={selectedCaseId} />}
```

`WorkflowTracker` (left sidebar) is unchanged. `DocumentDetailDrawer` is unchanged — it still opens via `workspaceStore.setActiveDocument` + `setDrawerOpen`, triggered either from the Documents tab or from the "Open Document ↗" button in `TaskDetailView`.

### 9e — Backend: `case_id` filter on GET /tasks

`CaseOverviewPanel` calls `GET /tasks?case_id=<id>` — already covered in Step 6. No new endpoint.

### 9f — `workspaceStore` changes

None needed. All inner tab state (`activeInnerTab`, open task tabs) lives as local `useState` inside `CaseOverviewPanel`.

---

## Step 10 — Add Tasks Tab to AdvisorWorkspace Dashboard

**File:** `frontend/src/routes/AdvisorWorkspace.tsx`

Add `activeView: 'cases' | 'tasks'` local state (default `'cases'`). In the dashboard content area, add My Tasks / All Cases toggle buttons above the grid:

```tsx
activeTabId === 'dashboard' ? (
  <div className="flex flex-1 flex-col overflow-hidden">
    {/* Toggle */}
    <div className="flex shrink-0 items-center gap-1 border-b border-gray-200 px-4 py-2 dark:border-gray-800">
      <button
        onClick={() => setActiveView('tasks')}
        className={activeView === 'tasks' ? 'tab-active' : 'tab-inactive'}
      >
        My Tasks <span className="badge">{taskCount}</span>
      </button>
      <button
        onClick={() => setActiveView('cases')}
        className={activeView === 'cases' ? 'tab-active' : 'tab-inactive'}
      >
        All Cases <span className="badge">{caseCount}</span>
      </button>
    </div>
    {activeView === 'tasks' ? <TaskListPanel /> : <CaseListTable />}
  </div>
) : (
  /* existing case workspace — unchanged */
)
```

No changes to the tab bar itself; no new tab types in `openTabs`.

---

## Step 11 — Real-time Socket Updates

**File:** `frontend/src/hooks/useWorkspaceSocket.ts`

```typescript
socket.on('TASK_CREATED', () => queryClient.invalidateQueries({ queryKey: ['tasks'] }))
socket.on('TASK_UPDATED', () => queryClient.invalidateQueries({ queryKey: ['tasks'] }))
```

**File:** `backend/app/websocket/socket_emitter.py`

```python
async def task_created(self, case_id: UUID, payload: dict) -> None:
    await self._emit(str(case_id), 'TASK_CREATED', payload)

async def task_updated(self, case_id: UUID, payload: dict) -> None:
    await self._emit(str(case_id), 'TASK_UPDATED', payload)
```

---

## Step 12 — Mobile Responsive Design

All new components must support mobile (≥320px) and tablet (≥768px) using Tailwind responsive prefixes (`sm:`, `md:`). The existing workspace already uses `md:flex-row md:overflow-hidden` for its split layout — follow the same pattern.

### Dashboard Tab (TaskListPanel) — mobile

AG Grid is replaced with a **card list** on small screens. The grid is hidden below `md`, replaced by stacked task cards:

```
mobile (< md):                    desktop (≥ md):
┌──────────────────────┐          AG Grid table with columns
│ Enrollment Form Rev. │          CLIENT | CASE | TASK | STAGE | STATUS | CREATED | Action
│ [Client Enrollment]  │
│ [Pending]            │
│ Jordan Lee · case-001│
│ Nov 1, 2024          │
│        [Open in Case>]│
└──────────────────────┘
```

```tsx
// TaskListPanel.tsx
<div className="block md:hidden">          {/* mobile card list */}
  {tasks.map(t => <TaskCard key={t.id} task={t} />)}
</div>
<div className="hidden md:flex flex-1">   {/* desktop AG Grid */}
  <BaseGrid ... />
</div>
```

**`TaskCard`** (mobile-only sub-component inside `TaskListPanel`):
- Full-width card, ~80px tall
- Line 1: title (bold) + status badge (right)
- Line 2: task_type badge + client name
- Line 3: case ID + created date (muted)
- Full-width "Open in Case" button at bottom

### Case Tab layout — mobile

On mobile the left sidebar (Case Info + Progress) collapses **above** the content area (stacks vertically instead of side-by-side):

```
mobile:                           desktop:
┌─────────────────────┐           ┌──────────┬──────────────────────────┐
│ CASE INFO + PROGRESS│           │ sidebar  │ CASE SUMMARY STRIP       │
│ (collapsed strip)   │           │          │ ──────────────────────── │
├─────────────────────┤           │          │ [Overview][Docs][App]    │
│ CASE SUMMARY STRIP  │           │          │ ──────────────────────── │
│ Giri P. · REVIEW 90%│          │          │  tab content             │
├─────────────────────┤           └──────────┴──────────────────────────┘
│ [Overview][Docs][App│
│ scroll →            │
│ ─────────────────── │
│ Tasks  2  [pending] │
│ [Pending] [Completed]│
│ ┌─────────────────┐ │
│ │ Task row        │ │
│ │ [Review Task >] │ │
│ └─────────────────┘ │
└─────────────────────┘
```

The inner tab bar scrolls horizontally on mobile using `overflow-x-auto`.

### Task Detail Sub-Tab — mobile

The two-column layout (left cards + right cards) **stacks vertically** on mobile:

```
mobile:                           desktop:
┌─────────────────────┐           ┌──────────────┬──────────────┐
│ TASK STATUS         │           │ doc preview  │ TASK STATUS  │
│ [Pending]           │           │ card         │ card         │
│ Created Nov 20      │           │              │              │
├─────────────────────┤           │ TASK DETAILS │ ACTIONS      │
│ ACTIONS             │           │ card         │ card         │
│ ✓ Approve           │           └──────────────┴──────────────┘
│ ✗ Reject            │
│ ⟳ Request Info      │
├─────────────────────┤
│ doc preview card    │
│ [Open Document ↗]   │
├─────────────────────┤
│ TASK DETAILS        │
│ Task ID  task-038   │
│ Type     Enroll Rev │
│ Stage    [badge]    │
│ Assigned Marcus C.  │
│ Created  Nov 20     │
└─────────────────────┘
```

On mobile, **Task Status + Actions** appear first (above the fold) so the user can act immediately without scrolling past the document preview.

```tsx
// TaskDetailView.tsx
<div className="flex flex-col md:flex-row gap-4 p-4">
  {/* Right col shown first on mobile */}
  <div className="flex flex-col gap-4 md:order-2 md:w-64 shrink-0">
    <TaskStatusCard task={task} />
    <ActionsCard task={task} onDecide={handleDecide} />
  </div>
  {/* Left col below on mobile */}
  <div className="flex flex-col gap-4 md:order-1 flex-1">
    <DocumentPreviewCard task={task} />
    <TaskDetailsCard task={task} />
  </div>
</div>
```

### Inner tab bar — mobile

Tabs scroll horizontally. On very small screens (< `sm`), tab labels truncate to icons + short text:

```tsx
<div className="flex overflow-x-auto border-b border-gray-200 dark:border-gray-800
                [&::-webkit-scrollbar]:h-[2px]">
  <button className="shrink-0 whitespace-nowrap ...">Overview (2)</button>
  <button className="shrink-0 whitespace-nowrap ...">Documents</button>
  <button className="shrink-0 whitespace-nowrap ...">Application</button>
  {taskTabs.map(t => <button key={t.id} className="shrink-0 whitespace-nowrap ...">...</button>)}
</div>
```

### Breakpoint summary

| Breakpoint | TaskListPanel | Case sidebar | Task detail | Inner tab bar |
|------------|--------------|--------------|-------------|---------------|
| < md (mobile) | Card list | Stacked above content | Single column, status+actions first | Horizontal scroll |
| ≥ md (tablet/desktop) | AG Grid | Side-by-side | Two columns | Normal row |

---

## File Change Summary

| Layer     | File                                                             | Change        |
|-----------|------------------------------------------------------------------|---------------|
| DB Model  | `backend/app/models/tasks.py`                                    | New           |
| DB Model  | `backend/app/models/__init__.py`                                 | Register      |
| Migration | `backend/alembic/versions/<hash>_add_workspace_tasks.py`         | New           |
| Service   | `backend/app/services/task/task_service.py`                      | New           |
| Service   | `backend/app/services/document/document_upload_service.py`       | Hook (add)    |
| Service   | `backend/app/services/sales_review/sales_review_service.py`      | Hook (add)    |
| Socket    | `backend/app/websocket/socket_emitter.py`                        | 2 methods     |
| Router    | `backend/app/api/routers/tasks.py`                               | New           |
| Main      | `backend/app/main.py`                                            | Register      |
| API       | `frontend/src/lib/api.ts`                                        | 3 methods     |
| Hook      | `frontend/src/hooks/useTasks.ts`                                 | New           |
| Component | `frontend/src/features/advisor/TaskListPanel.tsx`                | New           |
| Component | `frontend/src/features/advisor/CaseOverviewPanel.tsx`            | New (replaces DocumentWorkspacePanel in case tab) |
| Component | `frontend/src/features/advisor/TaskRow.tsx`                      | New           |
| Component | `frontend/src/features/advisor/TaskDetailView.tsx`               | New           |
| Component | `frontend/src/features/advisor/DecisionModal.tsx`                | Extracted from SalesReviewPanel (shared) |
| Component | `frontend/src/features/advisor/SalesReviewPanel.tsx`             | Import DecisionModal from shared file |
| Route     | `frontend/src/routes/AdvisorWorkspace.tsx`                       | Tasks tab + swap panel |
| Socket    | `frontend/src/hooks/useWorkspaceSocket.ts`                       | 2 listeners   |

---

## Verification

1. **Document upload trigger** — upload a document via `POST /cases/{id}/documents`; confirm a `workspace_tasks` row exists with `task_type='DOCUMENT_REVIEW'` and `status='PENDING'`.
2. **Sales review trigger** — transition a case to SALES_REVIEW; confirm `workspace_tasks` row with `task_type='SALES_REVIEW'`.
3. **Decide endpoint** — `PATCH /tasks/{id}/decide` `{ decision: 'APPROVED' }`; verify `status='APPROVED'` and the linked document or sales review updated accordingly.
4. **Advisor flow (dashboard)** — log in as advisor → Dashboard → My Tasks → pending document review tasks visible in TaskListPanel → click "Open in Case" → case tab opens.
5. **Advisor flow (case overview)** — inside the case tab, `[Documents] [Application]` tabs are gone; Overview tab shows Tasks section with Pending/Completed sub-tabs → pending task row visible → click "Review Task >" → TaskActionPanel expands inline → click Approve → status badge switches to Approved; task moves to Completed sub-tab.
6. **Sales manager flow** — log in as sales_manager → My Tasks → pending sales review task → "Open in Case" → case tab → Overview → "Review Task >" → Approve/Reject → status updates in real time via socket.
