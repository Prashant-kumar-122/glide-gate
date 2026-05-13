from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("email", name="clients_email_uq"),
        CheckConstraint("kyc_status IN ('PENDING','PASSED','FAILED','ESCALATED')", name="clients_kyc_status_chk"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    nationality: Mapped[str | None] = mapped_column(String(100))
    tax_residency: Mapped[str | None] = mapped_column(String(100))
    employment_status: Mapped[str | None] = mapped_column(String(50))
    annual_income: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    source_of_wealth: Mapped[str | None] = mapped_column(Text)
    risk_appetite: Mapped[str | None] = mapped_column(String(20))
    investment_experience: Mapped[str | None] = mapped_column(String(20))
    investment_horizon: Mapped[str | None] = mapped_column(String(20))
    kyc_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    extra_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile: Mapped[ClientProfile | None] = relationship("ClientProfile", back_populates="client", uselist=False, cascade="all, delete-orphan")
    addresses: Mapped[list[ClientAddress]] = relationship("ClientAddress", back_populates="client", cascade="all, delete-orphan")
    onboarding_cases: Mapped[list[Any]] = relationship("OnboardingCase", back_populates="client")


class ClientProfile(Base):
    __tablename__ = "client_profiles"
    __table_args__ = (
        UniqueConstraint("client_id", name="client_profiles_client_uq"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    profile_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    consent_marketing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_data_processing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    preferred_communication_channel: Mapped[str] = mapped_column(String(20), nullable=False, default="email")
    language_preference: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    client: Mapped[Client] = relationship("Client", back_populates="profile")


class ClientAddress(Base):
    __tablename__ = "client_addresses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    address_type: Mapped[str] = mapped_column(String(20), nullable=False)
    line1: Mapped[str] = mapped_column(String(255), nullable=False)
    line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    client: Mapped[Client] = relationship("Client", back_populates="addresses")
