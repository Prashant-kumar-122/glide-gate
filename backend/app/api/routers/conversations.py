from __future__ import annotations

import asyncio
import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.error_handlers import NotFoundError
from app.database import get_db
from app.models.cases import OnboardingCase
from app.models.communications import ConversationMessage

router = APIRouter(prefix="/cases", tags=["conversations"])


# ── Request / Response models ─────────────────────────────────────────────────

class MessageRequest(BaseModel):
    message: str
    session_id: str | None = None


class MessageHistoryOut(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── SSE helpers ───────────────────────────────────────────────────────────────

def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _placeholder_stream(case_id: UUID, user_message: str):
    """Placeholder SSE generator — replaced by ConversationCoordinator in STEP-27."""
    yield _sse_event({"type": "start", "case_id": str(case_id)})
    await asyncio.sleep(0)

    placeholder = (
        "Thank you for your message. The conversational AI interface will be "
        "fully wired in STEP-27 (Streaming Conversational Interface). "
        "Your case is currently being processed."
    )
    for word in placeholder.split():
        yield _sse_event({"type": "token", "token": word + " "})
        await asyncio.sleep(0.02)

    yield _sse_event({"type": "end", "case_id": str(case_id)})


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/{case_id}/message")
async def send_message(
    case_id: UUID,
    body: MessageRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    # Fetch client_id from the case (also verifies the case exists)
    case_row = await db.execute(
        select(OnboardingCase.client_id).where(OnboardingCase.id == case_id)
    )
    client_id = case_row.scalar_one_or_none()
    if client_id is None:
        raise NotFoundError("OnboardingCase", str(case_id))

    # Persist the user message
    msg = ConversationMessage(
        case_id=case_id,
        client_id=client_id,
        role="user",
        content=body.message,
        metadata={
            "session_id": body.session_id,
            "sender_id": user.get("sub"),
            "sender_role": user.get("role", "Client"),
        },
    )
    db.add(msg)
    await db.commit()

    return StreamingResponse(
        _placeholder_stream(case_id, body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{case_id}/messages", response_model=list[MessageHistoryOut])
async def get_message_history(
    case_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> list[MessageHistoryOut]:
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.case_id == case_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return [MessageHistoryOut.model_validate(m) for m in reversed(messages)]
