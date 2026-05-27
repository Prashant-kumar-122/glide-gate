from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("channel IN ('email','sms','in_app')", name="notif_channel_chk"),
        CheckConstraint(
            "status IN ('PENDING','SENT','FAILED','BOUNCED','SIMULATED_SENT')",
            name="notif_status_chk",
        ),
        CheckConstraint(
            "user_type IN ('client', 'advisor', 'admin')",
            name="notif_user_type_chk",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID | None] = mapped_column(ForeignKey("onboarding_cases.id"))
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    user_type: Mapped[str | None] = mapped_column(String(20))
    template_name: Mapped[str | None] = mapped_column(String(100))
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    recipient_email: Mapped[str | None] = mapped_column(String(255))
    recipient_phone: Mapped[str | None] = mapped_column(String(50))
    subject: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sent_at: Mapped[datetime | None] = mapped_column()
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    case: Mapped[Any] = relationship("OnboardingCase", back_populates="notifications")
    user: Mapped[Any] = relationship("User")


class CaseSummary(Base):
    __tablename__ = "case_summaries"
    __table_args__ = (
        CheckConstraint("summary_type IN ('call_summary','stage_summary','ai_summary')", name="cs_type_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False)
    summary_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(100))
    generated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    case: Mapped[Any] = relationship("OnboardingCase", back_populates="case_summaries")


class CollaborationRoom(Base):
    __tablename__ = "collaboration_rooms"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','CLOSED','ARCHIVED')", name="cr_status_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False)
    room_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    case: Mapped[Any] = relationship("OnboardingCase", back_populates="collaboration_rooms")
    participants: Mapped[list[CollaborationParticipant]] = relationship("CollaborationParticipant", back_populates="room", cascade="all, delete-orphan")
    comments: Mapped[list[CollaborationComment]] = relationship("CollaborationComment", back_populates="room", cascade="all, delete-orphan")


class CollaborationParticipant(Base):
    __tablename__ = "collaboration_participants"
    __table_args__ = (
        CheckConstraint("role IN ('Advisor','Client','ComplianceOfficer','CCRep','system')", name="cpart_role_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    room_id: Mapped[UUID] = mapped_column(ForeignKey("collaboration_rooms.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    left_at: Mapped[datetime | None] = mapped_column()
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    room: Mapped[CollaborationRoom] = relationship("CollaborationRoom", back_populates="participants")


class CollaborationComment(Base):
    __tablename__ = "collaboration_comments"
    __table_args__ = (
        CheckConstraint("visibility IN ('team','client_visible','compliance_only')", name="cc_visibility_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    room_id: Mapped[UUID] = mapped_column(ForeignKey("collaboration_rooms.id", ondelete="CASCADE"), nullable=False)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False)
    author_id: Mapped[str] = mapped_column(String(100), nullable=False)
    author_role: Mapped[str | None] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(30), nullable=False, default="team")
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id"))
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("collaboration_comments.id"))
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    room: Mapped[CollaborationRoom] = relationship("CollaborationRoom", back_populates="comments")
    document: Mapped[Any] = relationship("Document", back_populates="comments")
    parent: Mapped[CollaborationComment | None] = relationship("CollaborationComment", remote_side="CollaborationComment.id", foreign_keys=[parent_id])
    replies: Mapped[list[CollaborationComment]] = relationship("CollaborationComment", foreign_keys=[parent_id], back_populates="parent")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant','system')", name="cm_role_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    case: Mapped[Any] = relationship("OnboardingCase", back_populates="conversation_messages")
    client: Mapped[Any] = relationship("Client")
