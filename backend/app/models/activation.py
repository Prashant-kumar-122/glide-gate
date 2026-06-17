"""SQLAlchemy ORM model for product_activation table (Phase 4.6).

Tracks the per-product activation state machine:
  PENDING → CRITERIA_MET → ACTIVATED | DECLINED

Adverse-action fields (is_adverse_action, adverse_action_reason) satisfy
ECOA FR-AU-04 for credit-related declines.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProductActivation(Base):
    __tablename__ = "product_activation"
    __table_args__ = (
        CheckConstraint(
            "state IN ('PENDING', 'CRITERIA_MET', 'ACTIVATED', 'DECLINED')",
            name="pa_state_chk",
        ),
        UniqueConstraint("case_id", "product_code", name="pa_case_product_uq"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("onboarding_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_code: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    criteria_met_at: Mapped[datetime | None] = mapped_column()
    activated_at: Mapped[datetime | None] = mapped_column()
    declined_at: Mapped[datetime | None] = mapped_column()
    decline_reason: Mapped[str | None] = mapped_column(Text)
    account_number: Mapped[str | None] = mapped_column(String(100))
    is_adverse_action: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    adverse_action_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=_now, onupdate=_now)

    case: Mapped[Any] = relationship("OnboardingCase", back_populates="product_activations")
