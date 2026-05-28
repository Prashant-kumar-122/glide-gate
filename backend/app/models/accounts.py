from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClientAccount(Base):
    __tablename__ = "client_accounts"
    __table_args__ = (
        UniqueConstraint("case_id", "product", name="client_accounts_case_product_uq"),
        UniqueConstraint("account_number", name="client_accounts_number_uq"),
        Index("ix_client_accounts_client_id", "client_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("onboarding_cases.id"), nullable=False)
    product: Mapped[str] = mapped_column(String(100), nullable=False)
    account_number: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
