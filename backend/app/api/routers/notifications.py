from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.database import get_db
from app.models.communications import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: str
    template_id: str | None
    channel: str
    subject: str | None
    body_preview: str | None
    received_at: str


@router.get("", response_model=list[NotificationOut])
async def list_my_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[NotificationOut]:
    """Return the current user's in-app notifications, newest first."""
    user_id = UUID(current_user["sub"])

    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .where(Notification.channel == "in_app")
        .order_by(Notification.sent_at.desc().nullslast(), Notification.created_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()

    return [
        NotificationOut(
            id=str(n.id),
            template_id=n.template_name,
            channel=n.channel,
            subject=n.subject,
            body_preview=n.body or "",
            received_at=(n.sent_at or n.created_at).isoformat(),
        )
        for n in rows
    ]
