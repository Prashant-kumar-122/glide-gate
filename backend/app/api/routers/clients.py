from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.role_guard import require_role
from app.api.error_handlers import ConflictError, NotFoundError
from app.database import get_db
from app.models.clients import Client, ClientAddress, ClientProfile

router = APIRouter(prefix="/clients", tags=["clients"])


# ── Request / Response models ─────────────────────────────────────────────────

class AddressIn(BaseModel):
    address_type: str = "residential"
    line1: str
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str
    is_primary: bool = True


class CreateClientRequest(BaseModel):
    email: EmailStr
    phone: str | None = None
    first_name: str
    last_name: str
    date_of_birth: date | None = None
    nationality: str | None = None
    tax_residency: str | None = None
    employment_status: str | None = None
    annual_income: Decimal | None = None
    source_of_wealth: str | None = None
    risk_appetite: str | None = None
    investment_experience: str | None = None
    investment_horizon: str | None = None
    address: AddressIn | None = None
    consent_marketing: bool = False
    consent_data_processing: bool = True
    preferred_communication_channel: str = "email"
    language_preference: str = "en"


class PatchClientRequest(BaseModel):
    phone: str | None = None
    date_of_birth: date | None = None
    nationality: str | None = None
    tax_residency: str | None = None
    employment_status: str | None = None
    annual_income: Decimal | None = None
    source_of_wealth: str | None = None
    risk_appetite: str | None = None
    investment_experience: str | None = None
    investment_horizon: str | None = None
    extra_metadata: dict[str, Any] | None = None


class AddressOut(BaseModel):
    id: UUID
    address_type: str
    line1: str
    line2: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str
    is_primary: bool

    model_config = {"from_attributes": True}


class ProfileOut(BaseModel):
    id: UUID
    consent_marketing: bool
    consent_data_processing: bool
    preferred_communication_channel: str
    language_preference: str

    model_config = {"from_attributes": True}


class ClientOut(BaseModel):
    id: UUID
    email: str
    phone: str | None
    first_name: str
    last_name: str
    date_of_birth: date | None
    nationality: str | None
    tax_residency: str | None
    employment_status: str | None
    annual_income: Decimal | None
    source_of_wealth: str | None
    risk_appetite: str | None
    investment_experience: str | None
    investment_horizon: str | None
    kyc_status: str
    extra_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    profile: ProfileOut | None
    addresses: list[AddressOut]

    model_config = {"from_attributes": True}


class ClientSummaryOut(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    kyc_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_client_or_404(client_id: UUID, db: AsyncSession) -> Client:
    result = await db.execute(
        select(Client)
        .options(selectinload(Client.profile), selectinload(Client.addresses))
        .where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if client is None:
        raise NotFoundError("Client", str(client_id))
    return client


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, response_model=ClientSummaryOut)
async def create_client(
    body: CreateClientRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("Advisor", "Admin", "sales_manager")),
) -> ClientSummaryOut:
    existing = await db.execute(select(Client).where(Client.email == body.email))
    if existing.scalar_one_or_none():
        raise ConflictError(f"Client with email '{body.email}' already exists")

    client = Client(
        email=body.email,
        phone=body.phone,
        first_name=body.first_name,
        last_name=body.last_name,
        date_of_birth=body.date_of_birth,
        nationality=body.nationality,
        tax_residency=body.tax_residency,
        employment_status=body.employment_status,
        annual_income=body.annual_income,
        source_of_wealth=body.source_of_wealth,
        risk_appetite=body.risk_appetite,
        investment_experience=body.investment_experience,
        investment_horizon=body.investment_horizon,
    )
    db.add(client)
    await db.flush()

    profile = ClientProfile(
        client_id=client.id,
        consent_marketing=body.consent_marketing,
        consent_data_processing=body.consent_data_processing,
        preferred_communication_channel=body.preferred_communication_channel,
        language_preference=body.language_preference,
    )
    db.add(profile)

    if body.address:
        addr = ClientAddress(client_id=client.id, **body.address.model_dump())
        db.add(addr)

    await db.commit()
    await db.refresh(client)
    return ClientSummaryOut.model_validate(client)


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
) -> ClientOut:
    client = await _get_client_or_404(client_id, db)
    return ClientOut.model_validate(client)


@router.patch("/{client_id}", response_model=ClientSummaryOut)
async def patch_client(
    client_id: UUID,
    body: PatchClientRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("Advisor", "Admin", "sales_manager")),
) -> ClientSummaryOut:
    client = await _get_client_or_404(client_id, db)

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    await db.commit()
    await db.refresh(client)
    return ClientSummaryOut.model_validate(client)
