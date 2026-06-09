from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.push import PushSubscription

router = APIRouter(prefix="/push", tags=["push"])


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class SubscribeRequest(BaseModel):
    endpoint: str
    keys: PushKeys


@router.get("/public-key")
async def get_public_key() -> dict[str, str]:
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications are not configured on this server",
        )
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def subscribe(
    body: SubscribeRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    user_id = UUID(current_user["sub"])
    user_agent = request.headers.get("User-Agent", "")[:512]

    async with db.begin():
        result = await db.execute(
            select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.user_id = user_id
            existing.p256dh = body.keys.p256dh
            existing.auth = body.keys.auth
            existing.user_agent = user_agent
            existing.expired_at = None
            existing.last_used_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            db.add(PushSubscription(
                user_id=user_id,
                endpoint=body.endpoint,
                p256dh=body.keys.p256dh,
                auth=body.keys.auth,
                user_agent=user_agent,
            ))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/subscribe")
async def unsubscribe(
    body: SubscribeRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    user_id = UUID(current_user["sub"])
    async with db.begin():
        result = await db.execute(
            select(PushSubscription).where(
                PushSubscription.endpoint == body.endpoint,
                PushSubscription.user_id == user_id,
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            await db.delete(sub)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
