from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import asyncio

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskType
from app.api.dependencies.auth import get_current_user
from app.api.error_handlers import NotFoundError
from app.database import AsyncSessionLocal, get_db
from app.models.cases import OnboardingCase
from app.models.clients import Client
from app.models.communications import CollaborationComment, CollaborationRoom
from app.models.users import User
from app.services.orchestration.agent_orchestration_service import orchestration_service

router = APIRouter(prefix="/cases", tags=["collaboration"])

# Frontend uses ALL | ADVISOR_ONLY; DB uses client_visible | team
_VIS_TO_DB: dict[str, str] = {
    "ALL": "client_visible",
    "ADVISOR_ONLY": "team",
}
_VIS_FROM_DB: dict[str, str] = {
    "client_visible": "ALL",
    "team": "ADVISOR_ONLY",
    "compliance_only": "ADVISOR_ONLY",
}

_ROLE_MAP: dict[str, str] = {
    "advisor": "Advisor",
    "client": "Client",
    "admin": "Admin",
    "complianceofficer": "ComplianceOfficer",
    "ccrep": "CCRep",
    "sales_manager": "SalesManager",
}


class CommentOut(BaseModel):
    id: UUID
    author_name: str
    author_role: str
    body: str
    visibility: str
    document_id: UUID | None
    created_at: datetime


class CommentIn(BaseModel):
    body: str
    visibility: str = "ADVISOR_ONLY"
    document_id: UUID | None = None


async def _notify_comment(
    case_id: UUID,
    comment_body: str,
    author_name: str,
    author_role: str,
    visibility: str,
    document_id: UUID | None = None,
) -> None:
    """Email client when comment is client-visible OR document needs attention.
    Email advisor when client comments."""
    from app.models.documents import Document

    async with AsyncSessionLocal() as db:
        case = await db.get(OnboardingCase, case_id)
        if case is None:
            return
        client = await db.get(Client, case.client_id)
        client_name = f"{client.first_name} {client.last_name}".strip() if client else ""
        client_email = client.email if client else ""

        advisor_email = ""
        if case.assigned_advisor_id:
            advisor = await db.get(User, case.assigned_advisor_id)
            if advisor:
                advisor_email = advisor.email

        # Check if the linked document requires client attention
        doc_needs_attention = False
        if document_id:
            doc = await db.get(Document, document_id)
            if doc and doc.status in ("UNDER_REVIEW", "NEEDS_REVISION"):
                doc_needs_attention = True

    _case_name = (case.extra_metadata or {}).get("case_name", "") if case else ""
    base = {
        "author_name": author_name,
        "comment_body": comment_body,
        "client_name": client_name,
        "case_name": _case_name,
    }

    # Notify client only when visibility is ALL AND document needs attention
    should_notify_client = (
        visibility == "client_visible"
        and doc_needs_attention
        and client_email
    )
    if should_notify_client:
        await orchestration_service.publish_task(TaskPacket(
            from_agent=AgentID.CUSTOMER_SERVICE,
            to_agent=AgentID.NOTIFICATION,
            task_type=TaskType.SEND_NOTIFICATION,
            case_id=case_id,
            client_id=case.client_id,
            priority="NORMAL",
            payload={"template": "document_comment", "recipient_email": client_email, **base},
        ))

    if author_role == "Client" and advisor_email:
        await orchestration_service.publish_task(TaskPacket(
            from_agent=AgentID.CUSTOMER_SERVICE,
            to_agent=AgentID.NOTIFICATION,
            task_type=TaskType.SEND_NOTIFICATION,
            case_id=case_id,
            client_id=case.client_id,
            priority="NORMAL",
            payload={
                "template": "document_comment",
                "recipient_email": advisor_email,
                "author_name": client_name,
                "comment_body": comment_body,
                "client_name": "Advisor",
                "case_name": _case_name,
            },
        ))


async def _get_or_create_room(case_id: UUID, db: AsyncSession) -> CollaborationRoom:
    result = await db.execute(
        select(CollaborationRoom)
        .where(CollaborationRoom.case_id == case_id)
        .where(CollaborationRoom.status == "OPEN")
        .limit(1)
    )
    room = result.scalar_one_or_none()
    if room is None:
        room = CollaborationRoom(case_id=case_id, room_name="Main", status="OPEN")
        db.add(room)
        await db.flush()
    return room


@router.get("/{case_id}/comments", response_model=list[CommentOut])
async def list_comments(
    case_id: UUID,
    document_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[CommentOut]:
    case = await db.get(OnboardingCase, case_id)
    if case is None:
        raise NotFoundError("Case not found")

    query = (
        select(CollaborationComment)
        .where(CollaborationComment.case_id == case_id)
        .where(CollaborationComment.parent_id.is_(None))
    )

    # Clients only see comments marked for everyone (client_visible)
    if current_user.get("role") == "client":
        query = query.where(CollaborationComment.visibility == "client_visible")

    if document_id is not None:
        query = query.where(CollaborationComment.document_id == document_id)

    query = query.order_by(CollaborationComment.created_at)
    rows = (await db.execute(query)).scalars().all()

    return [
        CommentOut(
            id=r.id,
            author_name=r.extra_metadata.get("author_name", r.author_role or "Unknown"),
            author_role=r.author_role or "Advisor",
            body=r.content,
            visibility=_VIS_FROM_DB.get(r.visibility, "ADVISOR_ONLY"),
            document_id=r.document_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/{case_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(
    case_id: UUID,
    payload: CommentIn,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> CommentOut:
    case = await db.get(OnboardingCase, case_id)
    if case is None:
        raise NotFoundError("Case not found")

    room = await _get_or_create_room(case_id, db)

    raw_role = current_user.get("role", "advisor")
    author_role = _ROLE_MAP.get(raw_role.lower(), raw_role.capitalize())
    author_name = current_user.get("name") or current_user.get("email", "Unknown")
    db_visibility = _VIS_TO_DB.get(payload.visibility, "team")

    comment = CollaborationComment(
        room_id=room.id,
        case_id=case_id,
        author_id=str(current_user["sub"]),
        author_role=author_role,
        content=payload.body,
        visibility=db_visibility,
        document_id=payload.document_id,
        extra_metadata={"author_name": author_name},
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    asyncio.create_task(
        _notify_comment(
            case_id=case_id,
            comment_body=payload.body,
            author_name=author_name,
            author_role=author_role,
            visibility=db_visibility,
            document_id=payload.document_id,
        )
    )

    return CommentOut(
        id=comment.id,
        author_name=author_name,
        author_role=author_role,
        body=comment.content,
        visibility=_VIS_FROM_DB.get(comment.visibility, "ADVISOR_ONLY"),
        document_id=comment.document_id,
        created_at=comment.created_at,
    )
