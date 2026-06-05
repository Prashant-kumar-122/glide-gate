from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.role_guard import require_role
from app.api.error_handlers import NotFoundError, UnprocessableError
from app.database import get_db
from app.models.tasks import WorkspaceTask
from app.models.cases import OnboardingCase
from app.models.documents import Document
from app.models.sales_reviews import SalesManagerReview
from app.services.task.task_service import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])

TaskDecisionType = Literal["APPROVED", "REJECTED", "MORE_INFO_REQUESTED"]


# ── Schemas ───────────────────────────────────────────────────────────────────

class TaskDecideRequest(BaseModel):
    decision: TaskDecisionType
    decision_notes: str | None = None


class TaskOut(BaseModel):
    id: UUID
    case_id: UUID
    assignee_id: UUID | None
    assignee_role: str
    task_type: str
    title: str
    status: str
    document_id: UUID | None
    review_id: UUID | None
    decision_notes: str | None
    decided_by: UUID | None
    decided_at: datetime | None
    case_name: str | None
    client_name: str | None
    created_at: datetime
    updated_at: datetime
    document_snapshot: dict[str, Any] | None = None
    review_snapshot: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _enrich_task(task: WorkspaceTask, db: AsyncSession) -> dict[str, Any]:
    from app.models.clients import Client

    case_result = await db.execute(
        select(OnboardingCase).where(OnboardingCase.id == task.case_id)
    )
    case = case_result.scalar_one_or_none()
    case_name: str | None = None
    client_name: str | None = None
    if case:
        # case_name lives in extra_metadata, not as a direct column
        case_name = (case.extra_metadata or {}).get("case_name") or ""
        client_result = await db.execute(
            select(Client).where(Client.id == case.client_id)
        )
        client = client_result.scalar_one_or_none()
        if client:
            client_name = f"{client.first_name} {client.last_name}".strip()

    return {"case_name": case_name, "client_name": client_name}


async def _get_document_snapshot(document_id: UUID, db: AsyncSession) -> dict[str, Any] | None:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        return None
    return {
        "id": str(doc.id),
        "filename": doc.original_filename or doc.document_type,
        "status": doc.status,
        "category": doc.category,
        "storage_path": doc.storage_path,
        "mime_type": doc.mime_type,
    }


async def _get_review_snapshot(review_id: UUID, db: AsyncSession) -> dict[str, Any] | None:
    result = await db.execute(
        select(SalesManagerReview).where(SalesManagerReview.id == review_id)
    )
    review = result.scalar_one_or_none()
    if review is None:
        return None
    return {
        "id": str(review.id),
        "ai_risk_summary": review.ai_risk_summary,
        "risk_score": review.risk_score,
        "case_snapshot": review.case_snapshot,
        "status": review.status,
    }


async def _task_to_out(
    task: WorkspaceTask,
    db: AsyncSession,
    include_snapshots: bool = False,
) -> TaskOut:
    enriched = await _enrich_task(task, db)
    doc_snapshot = None
    review_snapshot = None
    if include_snapshots:
        if task.document_id:
            doc_snapshot = await _get_document_snapshot(task.document_id, db)
        if task.review_id:
            review_snapshot = await _get_review_snapshot(task.review_id, db)

    return TaskOut(
        id=task.id,
        case_id=task.case_id,
        assignee_id=task.assignee_id,
        assignee_role=task.assignee_role,
        task_type=task.task_type,
        title=task.title,
        status=task.status,
        document_id=task.document_id,
        review_id=task.review_id,
        decision_notes=task.decision_notes,
        decided_by=task.decided_by,
        decided_at=task.decided_at,
        case_name=enriched["case_name"],
        client_name=enriched["client_name"],
        created_at=task.created_at,
        updated_at=task.updated_at,
        document_snapshot=doc_snapshot,
        review_snapshot=review_snapshot,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[TaskOut])
async def list_tasks(
    role: str | None = None,
    case_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("advisor", "sales_manager", "Admin", "admin")),
) -> list[TaskOut]:
    user_role = role or user.get("role", "advisor")
    tasks = await task_service.list_tasks(
        assignee_role=user_role,
        case_id=case_id,
        db=db,
    )
    result = []
    for t in tasks:
        result.append(await _task_to_out(t, db, include_snapshots=False))
    return result


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("advisor", "sales_manager", "Admin", "admin")),
) -> TaskOut:
    task = await task_service.get_task(task_id, db)
    if task is None:
        raise NotFoundError("WorkspaceTask", str(task_id))
    return await _task_to_out(task, db, include_snapshots=True)


@router.patch("/{task_id}/decide", response_model=TaskOut)
async def decide_task(
    task_id: UUID,
    body: TaskDecideRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("advisor", "sales_manager", "Admin", "admin")),
) -> TaskOut:
    try:
        raw_id = user.get("sub")
        decided_by = UUID(raw_id) if raw_id else None
        task = await task_service.decide(
            task_id=task_id,
            decision=body.decision,
            decision_notes=body.decision_notes,
            decided_by=decided_by,
            db=db,
        )
    except ValueError as exc:
        raise UnprocessableError(str(exc)) from exc
    return await _task_to_out(task, db, include_snapshots=True)
