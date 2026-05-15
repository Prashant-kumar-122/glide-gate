from __future__ import annotations

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
from app.services.conversation.conversation_coordinator import conversation_coordinator

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


class CallSummaryOut(BaseModel):
    case_id: str
    summary: str
    key_points: list[str]
    recommended_actions: list[str]
    stage_label: str
    generated_at: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/{case_id}/greet")
async def start_greeting(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream an initial greeting when the client opens a fresh conversation."""
    case_row = await db.execute(
        select(OnboardingCase.client_id).where(OnboardingCase.id == case_id)
    )
    client_id = case_row.scalar_one_or_none()
    if client_id is None:
        raise NotFoundError("OnboardingCase", str(case_id))

    return StreamingResponse(
        conversation_coordinator.handle_greeting(
            case_id=case_id,
            client_id=client_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{case_id}/message")
async def send_message(
    case_id: UUID,
    body: MessageRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    case_row = await db.execute(
        select(OnboardingCase.client_id).where(OnboardingCase.id == case_id)
    )
    client_id = case_row.scalar_one_or_none()
    if client_id is None:
        raise NotFoundError("OnboardingCase", str(case_id))

    # Persist user message before streaming so the coordinator can load full history
    db.add(
        ConversationMessage(
            case_id=case_id,
            client_id=client_id,
            role="user",
            content=body.message,
            extra_metadata={
                "session_id": body.session_id,
                "sender_id": user.get("sub"),
                "sender_role": user.get("role", "client"),
            },
        )
    )
    await db.commit()

    return StreamingResponse(
        conversation_coordinator.handle_message(
            case_id=case_id,
            client_id=client_id,
            user_message=body.message,
            session_id=body.session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{case_id}/call-summary", response_model=CallSummaryOut)
async def get_call_summary(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> CallSummaryOut:
    """Stub — full AI summary generation wired in STEP-34 via ContactCentreAgent."""
    case_row = await db.execute(
        select(OnboardingCase.current_stage).where(OnboardingCase.id == case_id)
    )
    stage = case_row.scalar_one_or_none()
    if stage is None:
        raise NotFoundError("OnboardingCase", str(case_id))

    return CallSummaryOut(
        case_id=str(case_id),
        summary="AI call summary will be generated after a call is logged for this case.",
        key_points=[],
        recommended_actions=[
            "Review uploaded documents",
            "Contact client to schedule onboarding session",
        ],
        stage_label=stage,
        generated_at=datetime.utcnow().isoformat(),
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
