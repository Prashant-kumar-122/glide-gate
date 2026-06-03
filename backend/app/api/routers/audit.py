from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.role_guard import require_role
from app.database import get_db
from app.models.agents import EventLog
from app.services.audit.audit_event_types import AuditEventType

router = APIRouter(prefix="/audit", tags=["audit"])


# ── Response models ───────────────────────────────────────────────────────────

class EventLogOut(BaseModel):
    id: UUID
    case_id: UUID | None
    client_id: UUID | None
    agent_id: str | None
    event_type: str
    event_category: str | None
    entity_type: str | None
    entity_id: UUID | None
    actor_id: str | None
    actor_role: str | None
    payload: dict[str, Any]
    is_compliance_event: bool
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedLogsOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[EventLogOut]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/event-types", response_model=list[str])
async def list_event_types(
    _user: dict = Depends(require_role("advisor", "compliance_officer", "admin", "sales_manager")),
) -> list[str]:
    """Return all known audit event type strings for filter dropdowns."""
    return sorted(str(e) for e in AuditEventType)


@router.get("/logs", response_model=PaginatedLogsOut)
async def get_audit_logs(
    case_id: UUID | None = Query(None),
    client_id: UUID | None = Query(None),
    agent_id: str | None = Query(None),
    event_type: str | None = Query(None),
    event_category: str | None = Query(None),
    compliance_only: bool = Query(False),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("advisor", "compliance_officer", "admin", "sales_manager")),
) -> PaginatedLogsOut:
    query = select(EventLog).order_by(EventLog.created_at.desc())

    if case_id:
        query = query.where(EventLog.case_id == case_id)
    if client_id:
        query = query.where(EventLog.client_id == client_id)
    if agent_id:
        query = query.where(EventLog.agent_id == agent_id)
    if event_type:
        query = query.where(EventLog.event_type == event_type)
    if event_category:
        query = query.where(EventLog.event_category == event_category)
    if compliance_only:
        query = query.where(EventLog.is_compliance_event.is_(True))
    if from_date:
        query = query.where(EventLog.created_at >= from_date)
    if to_date:
        query = query.where(EventLog.created_at <= to_date)

    count_result = await db.execute(query.with_only_columns(EventLog.id))
    total = len(count_result.scalars().all())

    paged = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(paged)
    items = result.scalars().all()

    return PaginatedLogsOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[EventLogOut.model_validate(e) for e in items],
    )


@router.get("/logs.csv")
async def export_audit_logs_csv(
    case_id: UUID | None = Query(None),
    event_type: str | None = Query(None),
    compliance_only: bool = Query(False),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("compliance_officer", "admin")),
) -> StreamingResponse:
    query = select(EventLog).order_by(EventLog.created_at)

    if case_id:
        query = query.where(EventLog.case_id == case_id)
    if event_type:
        query = query.where(EventLog.event_type == event_type)
    if compliance_only:
        query = query.where(EventLog.is_compliance_event.is_(True))
    if from_date:
        query = query.where(EventLog.created_at >= from_date)
    if to_date:
        query = query.where(EventLog.created_at <= to_date)

    result = await db.execute(query)
    logs = result.scalars().all()

    async def _csv_generator():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "created_at", "case_id", "client_id", "agent_id",
            "event_type", "event_category", "entity_type", "entity_id",
            "actor_id", "actor_role", "is_compliance_event",
        ])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate()

        for log in logs:
            writer.writerow([
                str(log.id), log.created_at.isoformat(),
                str(log.case_id) if log.case_id else "",
                str(log.client_id) if log.client_id else "",
                log.agent_id or "", log.event_type,
                log.event_category or "", log.entity_type or "",
                str(log.entity_id) if log.entity_id else "",
                log.actor_id or "", log.actor_role or "",
                str(log.is_compliance_event),
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()

    filename = f"audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        _csv_generator(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
