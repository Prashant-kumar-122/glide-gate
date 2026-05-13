from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "category IN ('identity','financial','legal','insurance','compliance','entity')",
            name="doc_category_chk",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_REQUESTED")
    original_filename: Mapped[str | None] = mapped_column(String(500))
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    ocr_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    classification_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    validation_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    diff_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_doc_id: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id"))
    uploaded_by: Mapped[str | None] = mapped_column(String(50))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    uploaded_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    case: Mapped[Any] = relationship("OnboardingCase", back_populates="documents")
    client: Mapped[Any] = relationship("Client")
    parent: Mapped[Document | None] = relationship("Document", remote_side="Document.id", foreign_keys=[parent_doc_id])
    versions: Mapped[list[Document]] = relationship("Document", foreign_keys=[parent_doc_id], back_populates="parent")
    comments: Mapped[list[Any]] = relationship("CollaborationComment", back_populates="document")
