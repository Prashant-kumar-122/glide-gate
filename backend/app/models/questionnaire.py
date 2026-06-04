from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OnboardingQuestionnaire(Base):
    __tablename__ = "onboarding_questionnaires"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sections: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    questions: Mapped[list[OnboardingQuestion]] = relationship("OnboardingQuestion", back_populates="questionnaire", cascade="all, delete-orphan")
    answers: Mapped[list[OnboardingAnswer]] = relationship("OnboardingAnswer", back_populates="questionnaire")
    sessions: Mapped[list[OnboardingQuestionSession]] = relationship("OnboardingQuestionSession", back_populates="questionnaire")


class OnboardingQuestion(Base):
    __tablename__ = "onboarding_questions"
    __table_args__ = (
        UniqueConstraint("questionnaire_id", "question_key", name="oqn_key_uq"),
        CheckConstraint(
            "question_type IN ('text','number','select','multi_select','date','boolean','currency','textarea','email')",
            name="oqn_type_chk",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    questionnaire_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_questionnaires.id", ondelete="CASCADE"), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(100), nullable=False)
    question_key: Mapped[str] = mapped_column(String(100), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    options: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    validation_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    show_if: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    questionnaire: Mapped[OnboardingQuestionnaire] = relationship("OnboardingQuestionnaire", back_populates="questions")
    rules: Mapped[list[OnboardingQuestionRule]] = relationship("OnboardingQuestionRule", back_populates="question", cascade="all, delete-orphan")
    answers: Mapped[list[OnboardingAnswer]] = relationship("OnboardingAnswer", back_populates="question")


class OnboardingQuestionRule(Base):
    __tablename__ = "onboarding_question_rules"
    __table_args__ = (
        CheckConstraint("rule_type IN ('show_if','validate','skip','require')", name="oqr_rule_type_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    action: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    question: Mapped[OnboardingQuestion] = relationship("OnboardingQuestion", back_populates="rules")


class OnboardingAnswer(Base):
    __tablename__ = "onboarding_answers"
    __table_args__ = (
        UniqueConstraint("case_id", "question_id", name="oa_case_question_uq"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False, index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    questionnaire_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_questionnaires.id"), nullable=False, index=True)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_questions.id"), nullable=False, index=True)
    question_key: Mapped[str] = mapped_column(String(100), nullable=False)
    answer_value: Mapped[Any] = mapped_column(JSONB)
    answered_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    case: Mapped[Any] = relationship("OnboardingCase", back_populates="answers")
    client: Mapped[Any] = relationship("Client")
    questionnaire: Mapped[OnboardingQuestionnaire] = relationship("OnboardingQuestionnaire", back_populates="answers")
    question: Mapped[OnboardingQuestion] = relationship("OnboardingQuestion", back_populates="answers")


class OnboardingQuestionSession(Base):
    __tablename__ = "onboarding_question_sessions"
    __table_args__ = (
        UniqueConstraint("case_id", "questionnaire_id", name="oqs_case_q_uq"),
        CheckConstraint("status IN ('IN_PROGRESS','PAUSED','COMPLETED','ABANDONED')", name="oqs_status_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False, index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    questionnaire_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_questionnaires.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="IN_PROGRESS")
    current_section: Mapped[str | None] = mapped_column(String(100))
    current_question_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_sections: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    session_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    paused_at: Mapped[datetime | None] = mapped_column()
    resumed_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    case: Mapped[Any] = relationship("OnboardingCase", back_populates="question_sessions")
    client: Mapped[Any] = relationship("Client")
    questionnaire: Mapped[OnboardingQuestionnaire] = relationship("OnboardingQuestionnaire", back_populates="sessions")
