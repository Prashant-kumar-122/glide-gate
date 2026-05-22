from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClientAccount(Base):
    __tablename__ = "client_accounts"
    __table_args__ = (
        UniqueConstraint("case_id", name="client_accounts_case_id_uq"),
        UniqueConstraint("account_number", name="client_accounts_number_uq"),
        Index("ix_client_accounts_client_id", "client_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False)
    products: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    account_number: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
