from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WorkspaceTask(Base):
    __tablename__ = "workspace_tasks"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('DOCUMENT_REVIEW','SALES_REVIEW')",
            name="wt_type_chk",
        ),
        CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED','MORE_INFO_REQUESTED')",
            name="wt_status_chk",
        ),
        CheckConstraint(
            "assignee_role IN ('advisor','sales_manager')",
            name="wt_role_chk",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("onboarding_cases.id"), nullable=False, index=True
    )
    assignee_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    assignee_role: Mapped[str] = mapped_column(String(20), nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    review_id: Mapped[UUID | None] = mapped_column(nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[UUID | None] = mapped_column(nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    case: Mapped[Any] = relationship("OnboardingCase")
    document: Mapped[Any] = relationship("Document")
