from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.role_guard import require_role
from app.api.error_handlers import NotFoundError, UnprocessableError
from app.database import get_db
from app.models.kyc_reviews import HumanReview

router = APIRouter(prefix="/reviews", tags=["reviews"])

DecisionType = Literal["APPROVED", "REJECTED", "MORE_INFO_REQUESTED"]


# ── Request / Response models ─────────────────────────────────────────────────

class DecideRequest(BaseModel):
    decision: DecisionType
    decision_notes: str | None = None


class ReviewOut(BaseModel):
    id: UUID
    case_id: UUID
    kyc_check_id: UUID
    reviewer_id: UUID | None
    reviewer_role: str | None
    status: str
    evidence_packet: dict[str, Any]
    decision: str | None
    decision_notes: str | None
    escalation_reason: str | None
    assigned_at: datetime
    decided_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionOut(BaseModel):
    review_id: UUID
    decision: str
    decided_at: datetime
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_review_or_404(review_id: UUID, db: AsyncSession) -> HumanReview:
    result = await db.execute(
        select(HumanReview).where(HumanReview.id == review_id)
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise NotFoundError("HumanReview", str(review_id))
    return review


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ReviewOut])
async def list_pending_reviews(
    case_id: UUID | None = None,
    include_decided: bool = False,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("ComplianceOfficer", "Admin", "Advisor")),
) -> list[ReviewOut]:
    query = select(HumanReview)

    if case_id:
        query = query.where(HumanReview.case_id == case_id)

    if not include_decided:
        query = query.where(HumanReview.status == "PENDING")

    query = query.order_by(HumanReview.assigned_at.desc())
    result = await db.execute(query)
    reviews = result.scalars().all()
    return [ReviewOut.model_validate(r) for r in reviews]


@router.get("/{review_id}", response_model=ReviewOut)
async def get_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("ComplianceOfficer", "Admin", "Advisor")),
) -> ReviewOut:
    review = await _get_review_or_404(review_id, db)
    return ReviewOut.model_validate(review)


@router.get("/{review_id}/evidence", response_model=dict)
async def get_evidence_packet(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("ComplianceOfficer", "Admin")),
) -> dict:
    review = await _get_review_or_404(review_id, db)
    return {"review_id": str(review_id), "evidence_packet": review.evidence_packet}


@router.post("/{review_id}/decide", status_code=status.HTTP_200_OK, response_model=DecisionOut)
async def decide_review(
    review_id: UUID,
    body: DecideRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("ComplianceOfficer", "Admin")),
) -> DecisionOut:
    review = await _get_review_or_404(review_id, db)

    if review.status != "PENDING":
        raise UnprocessableError(
            f"Review '{review_id}' has already been decided (status: {review.status})"
        )

    review.status = body.decision
    review.decision = body.decision
    review.decision_notes = body.decision_notes
    review.reviewer_role = user.get("role")
    review.decided_at = datetime.utcnow()

    await db.commit()

    # Workflow resumption wired in STEP-17 / STEP-29
    return DecisionOut(
        review_id=review_id,
        decision=body.decision,
        decided_at=review.decided_at,
        message="Decision recorded — workflow will resume via AgentOrchestrationService",
    )
