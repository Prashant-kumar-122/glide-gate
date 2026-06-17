from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.permission_guard import require_permission
from app.api.error_handlers import ConflictError, NotFoundError
from app.database import get_db
from app.models.domain import Domain, DomainStage, DomainTaskRouting, DomainTransition
from app.services.audit.audit_event_types import AuditEventType
from app.services.audit.decision_log_service import DecisionLogEntry, decision_log_service

router = APIRouter(prefix="/admin/domains", tags=["admin"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_domain_or_404(domain_id: UUID, db: AsyncSession) -> Domain:
    result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = result.scalar_one_or_none()
    if not domain:
        raise NotFoundError(f"Domain {domain_id} not found")
    return domain


async def _log(action: str, payload: dict[str, Any]) -> None:
    await decision_log_service.append(
        DecisionLogEntry(
            agent_id="admin_portal",
            event_type=AuditEventType.CONFIG_CHANGE,
            payload={"action": action, **payload},
        )
    )


# ── Stage request / response models ──────────────────────────────────────────

class StageOut(BaseModel):
    id: str
    domain_id: str
    stage_code: str
    display_name: str
    is_terminal: bool
    is_human_pending: bool


class StageCreate(BaseModel):
    stage_code: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z0-9_]+$")
    display_name: str = Field(..., min_length=1, max_length=200)
    is_terminal: bool = False
    is_human_pending: bool = False


class StageUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=200)
    is_terminal: bool | None = None
    is_human_pending: bool | None = None


# ── Transition request / response models ──────────────────────────────────────

class TransitionOut(BaseModel):
    id: str
    domain_id: str
    from_stage: str
    to_stage: str


class TransitionCreate(BaseModel):
    from_stage: str = Field(..., min_length=1, max_length=50)
    to_stage: str = Field(..., min_length=1, max_length=50)


# ── Task routing request / response models ────────────────────────────────────

class TaskRoutingOut(BaseModel):
    id: str
    domain_id: str
    stage_code: str
    target_agent: str
    task_type: str
    priority: str
    payload_template: dict[str, Any]
    notification_templates: dict[str, Any]


class TaskRoutingCreate(BaseModel):
    stage_code: str = Field(..., min_length=1, max_length=50)
    target_agent: str = Field(..., min_length=1, max_length=100)
    task_type: str = Field(..., min_length=1, max_length=100)
    priority: str = Field("NORMAL", max_length=20)
    payload_template: dict[str, Any] = {}
    notification_templates: dict[str, Any] = {}


class TaskRoutingUpdate(BaseModel):
    target_agent: str | None = Field(None, min_length=1, max_length=100)
    task_type: str | None = Field(None, min_length=1, max_length=100)
    priority: str | None = Field(None, max_length=20)
    payload_template: dict[str, Any] | None = None
    notification_templates: dict[str, Any] | None = None


# ── Stage routes ──────────────────────────────────────────────────────────────

@router.get("/{domain_id}/stages", response_model=list[StageOut])
async def list_stages(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[StageOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainStage)
        .where(DomainStage.domain_id == domain_id)
        .order_by(DomainStage.stage_code)
    )
    return [
        StageOut(
            id=str(s.id), domain_id=str(s.domain_id),
            stage_code=s.stage_code, display_name=s.display_name,
            is_terminal=s.is_terminal, is_human_pending=s.is_human_pending,
        )
        for s in result.scalars().all()
    ]


@router.post("/{domain_id}/stages", response_model=StageOut, status_code=201)
async def create_stage(
    domain_id: UUID,
    body: StageCreate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> StageOut:
    await _get_domain_or_404(domain_id, db)
    existing = await db.execute(
        select(DomainStage).where(
            DomainStage.domain_id == domain_id,
            DomainStage.stage_code == body.stage_code,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Stage '{body.stage_code}' already exists in this domain")

    stage = DomainStage(
        domain_id=domain_id,
        stage_code=body.stage_code,
        display_name=body.display_name,
        is_terminal=body.is_terminal,
        is_human_pending=body.is_human_pending,
    )
    db.add(stage)
    await db.flush()
    await db.refresh(stage)
    out = StageOut(
        id=str(stage.id), domain_id=str(stage.domain_id),
        stage_code=stage.stage_code, display_name=stage.display_name,
        is_terminal=stage.is_terminal, is_human_pending=stage.is_human_pending,
    )
    await db.commit()
    await _log("stage_created", {"domain_id": str(domain_id), "stage_code": body.stage_code})
    return out


@router.put("/{domain_id}/stages/{stage_id}", response_model=StageOut)
async def update_stage(
    domain_id: UUID,
    stage_id: UUID,
    body: StageUpdate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> StageOut:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainStage).where(DomainStage.id == stage_id, DomainStage.domain_id == domain_id)
    )
    stage = result.scalar_one_or_none()
    if not stage:
        raise NotFoundError(f"Stage {stage_id} not found in domain {domain_id}")

    if body.display_name is not None:
        stage.display_name = body.display_name
    if body.is_terminal is not None:
        stage.is_terminal = body.is_terminal
    if body.is_human_pending is not None:
        stage.is_human_pending = body.is_human_pending

    await db.flush()
    await db.refresh(stage)
    out = StageOut(
        id=str(stage.id), domain_id=str(stage.domain_id),
        stage_code=stage.stage_code, display_name=stage.display_name,
        is_terminal=stage.is_terminal, is_human_pending=stage.is_human_pending,
    )
    await db.commit()
    await _log("stage_updated", {"domain_id": str(domain_id), "stage_id": str(stage_id)})
    return out


@router.delete("/{domain_id}/stages/{stage_id}", status_code=204)
async def delete_stage(
    domain_id: UUID,
    stage_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainStage).where(DomainStage.id == stage_id, DomainStage.domain_id == domain_id)
    )
    stage = result.scalar_one_or_none()
    if not stage:
        raise NotFoundError(f"Stage {stage_id} not found in domain {domain_id}")
    stage_code = stage.stage_code
    await db.delete(stage)
    await db.commit()
    await _log("stage_deleted", {"domain_id": str(domain_id), "stage_code": stage_code})
    return Response(status_code=204)


# ── Transition routes ─────────────────────────────────────────────────────────

@router.get("/{domain_id}/transitions", response_model=list[TransitionOut])
async def list_transitions(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[TransitionOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainTransition)
        .where(DomainTransition.domain_id == domain_id)
        .order_by(DomainTransition.from_stage, DomainTransition.to_stage)
    )
    return [
        TransitionOut(
            id=str(t.id), domain_id=str(t.domain_id),
            from_stage=t.from_stage, to_stage=t.to_stage,
        )
        for t in result.scalars().all()
    ]


@router.post("/{domain_id}/transitions", response_model=TransitionOut, status_code=201)
async def create_transition(
    domain_id: UUID,
    body: TransitionCreate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> TransitionOut:
    await _get_domain_or_404(domain_id, db)
    existing = await db.execute(
        select(DomainTransition).where(
            DomainTransition.domain_id == domain_id,
            DomainTransition.from_stage == body.from_stage,
            DomainTransition.to_stage == body.to_stage,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Transition {body.from_stage} → {body.to_stage} already exists")

    transition = DomainTransition(
        domain_id=domain_id, from_stage=body.from_stage, to_stage=body.to_stage
    )
    db.add(transition)
    await db.flush()
    await db.refresh(transition)
    out = TransitionOut(
        id=str(transition.id), domain_id=str(transition.domain_id),
        from_stage=transition.from_stage, to_stage=transition.to_stage,
    )
    await db.commit()
    await _log("transition_created", {"domain_id": str(domain_id), "from": body.from_stage, "to": body.to_stage})
    return out


@router.delete("/{domain_id}/transitions/{transition_id}", status_code=204)
async def delete_transition(
    domain_id: UUID,
    transition_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainTransition).where(
            DomainTransition.id == transition_id,
            DomainTransition.domain_id == domain_id,
        )
    )
    transition = result.scalar_one_or_none()
    if not transition:
        raise NotFoundError(f"Transition {transition_id} not found in domain {domain_id}")
    await db.delete(transition)
    await db.commit()
    await _log("transition_deleted", {"domain_id": str(domain_id), "transition_id": str(transition_id)})
    return Response(status_code=204)


# ── Task routing routes ───────────────────────────────────────────────────────

@router.get("/{domain_id}/task-routing", response_model=list[TaskRoutingOut])
async def list_task_routing(
    domain_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> list[TaskRoutingOut]:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainTaskRouting)
        .where(DomainTaskRouting.domain_id == domain_id)
        .order_by(DomainTaskRouting.stage_code)
    )
    return [
        TaskRoutingOut(
            id=str(r.id), domain_id=str(r.domain_id),
            stage_code=r.stage_code, target_agent=r.target_agent,
            task_type=r.task_type, priority=r.priority,
            payload_template=r.payload_template,
            notification_templates=r.notification_templates,
        )
        for r in result.scalars().all()
    ]


@router.post("/{domain_id}/task-routing", response_model=TaskRoutingOut, status_code=201)
async def create_task_routing(
    domain_id: UUID,
    body: TaskRoutingCreate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> TaskRoutingOut:
    await _get_domain_or_404(domain_id, db)
    existing = await db.execute(
        select(DomainTaskRouting).where(
            DomainTaskRouting.domain_id == domain_id,
            DomainTaskRouting.stage_code == body.stage_code,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Task routing for stage '{body.stage_code}' already exists")

    row = DomainTaskRouting(
        domain_id=domain_id,
        stage_code=body.stage_code,
        target_agent=body.target_agent,
        task_type=body.task_type,
        priority=body.priority,
        payload_template=body.payload_template,
        notification_templates=body.notification_templates,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    out = TaskRoutingOut(
        id=str(row.id), domain_id=str(row.domain_id),
        stage_code=row.stage_code, target_agent=row.target_agent,
        task_type=row.task_type, priority=row.priority,
        payload_template=row.payload_template,
        notification_templates=row.notification_templates,
    )
    await db.commit()
    await _log("task_routing_created", {"domain_id": str(domain_id), "stage_code": body.stage_code})
    return out


@router.put("/{domain_id}/task-routing/{routing_id}", response_model=TaskRoutingOut)
async def update_task_routing(
    domain_id: UUID,
    routing_id: UUID,
    body: TaskRoutingUpdate,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> TaskRoutingOut:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainTaskRouting).where(
            DomainTaskRouting.id == routing_id,
            DomainTaskRouting.domain_id == domain_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError(f"Task routing {routing_id} not found in domain {domain_id}")

    if body.target_agent is not None:
        row.target_agent = body.target_agent
    if body.task_type is not None:
        row.task_type = body.task_type
    if body.priority is not None:
        row.priority = body.priority
    if body.payload_template is not None:
        row.payload_template = body.payload_template
    if body.notification_templates is not None:
        row.notification_templates = body.notification_templates

    await db.flush()
    await db.refresh(row)
    out = TaskRoutingOut(
        id=str(row.id), domain_id=str(row.domain_id),
        stage_code=row.stage_code, target_agent=row.target_agent,
        task_type=row.task_type, priority=row.priority,
        payload_template=row.payload_template,
        notification_templates=row.notification_templates,
    )
    await db.commit()
    await _log("task_routing_updated", {"domain_id": str(domain_id), "routing_id": str(routing_id)})
    return out


@router.delete("/{domain_id}/task-routing/{routing_id}", status_code=204)
async def delete_task_routing(
    domain_id: UUID,
    routing_id: UUID,
    _user: dict = Depends(require_permission("admin:config")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _get_domain_or_404(domain_id, db)
    result = await db.execute(
        select(DomainTaskRouting).where(
            DomainTaskRouting.id == routing_id,
            DomainTaskRouting.domain_id == domain_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError(f"Task routing {routing_id} not found in domain {domain_id}")
    await db.delete(row)
    await db.commit()
    await _log("task_routing_deleted", {"domain_id": str(domain_id), "routing_id": str(routing_id)})
    return Response(status_code=204)
