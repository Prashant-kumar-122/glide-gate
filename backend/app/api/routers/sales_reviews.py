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
from app.models.sales_reviews import SalesManagerReview
from app.services.sales_review.sales_review_service import sales_review_service

router = APIRouter(prefix="/sales-reviews", tags=["sales-reviews"])

SalesDecisionType = Literal["APPROVED", "REJECTED", "MORE_INFO_REQUESTED"]


# ── Request / Response schemas ────────────────────────────────────────────────

class SalesDecideRequest(BaseModel):
    decision: SalesDecisionType
    decision_notes: str | None = None


class SalesReviewOut(BaseModel):
    id: UUID
    case_id: UUID
    reviewer_id: UUID | None
    reviewer_role: str | None
    status: str
    decision: str | None
    decision_notes: str | None
    ai_risk_summary: str | None
    risk_score: float | None
    case_snapshot: dict[str, Any]
    assigned_at: datetime
    decided_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SalesDecisionOut(BaseModel):
    review_id: UUID
    decision: str
    decided_at: datetime
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_review_or_404(review_id: UUID, db: AsyncSession) -> SalesManagerReview:
    result = await db.execute(
        select(SalesManagerReview).where(SalesManagerReview.id == review_id)
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise NotFoundError("SalesManagerReview", str(review_id))
    return review


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[SalesReviewOut])
async def list_sales_reviews(
    case_id: UUID | None = None,
    include_decided: bool = False,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("sales_manager", "Admin", "admin", "Advisor", "advisor")),
) -> list[SalesReviewOut]:
    query = select(SalesManagerReview)

    if case_id:
        query = query.where(SalesManagerReview.case_id == case_id)

    if not include_decided:
        query = query.where(SalesManagerReview.status == "PENDING")

    query = query.order_by(SalesManagerReview.assigned_at.desc())
    result = await db.execute(query)
    reviews = result.scalars().all()
    return [SalesReviewOut.model_validate(r) for r in reviews]


@router.get("/{review_id}", response_model=SalesReviewOut)
async def get_sales_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("sales_manager", "Admin", "admin", "Advisor", "advisor")),
) -> SalesReviewOut:
    review = await _get_review_or_404(review_id, db)
    return SalesReviewOut.model_validate(review)


@router.post(
    "/{review_id}/decide",
    status_code=status.HTTP_200_OK,
    response_model=SalesDecisionOut,
)
async def decide_sales_review(
    review_id: UUID,
    body: SalesDecideRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("sales_manager", "Admin", "admin")),
) -> SalesDecisionOut:
    try:
        reviewer_id_raw = user.get("sub")
        reviewer_id = UUID(reviewer_id_raw) if reviewer_id_raw else None

        review = await sales_review_service.decide(
            review_id=review_id,
            decision=body.decision,
            decision_notes=body.decision_notes,
            reviewer_id=reviewer_id,
            reviewer_role=user.get("role"),
            db=db,
        )
    except ValueError as exc:
        raise UnprocessableError(str(exc)) from exc

    return SalesDecisionOut(
        review_id=review_id,
        decision=review.decision,
        decided_at=review.decided_at,
        message={
            "APPROVED": "Case approved — KYC will be initiated.",
            "REJECTED": "Case rejected — case moved to review.",
            "MORE_INFO_REQUESTED": "Additional information requested — case moved to review.",
        }.get(body.decision, "Decision recorded."),
    )
