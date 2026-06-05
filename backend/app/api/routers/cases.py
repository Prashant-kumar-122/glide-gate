from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.base.a2a_types import AgentID, OnboardingStage, TaskPacket, TaskType
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.role_guard import require_role
from app.api.error_handlers import ConflictError, NotFoundError
from app.database import get_db
from app.models.cases import CaseProduct, CaseProductStep, OnboardingCase, Product
from app.models.questionnaire import OnboardingQuestion, OnboardingQuestionnaire, OnboardingQuestionSession
from app.models.clients import Client
from app.models.users import User
from app.models.documents import Document
from app.models.accounts import ClientAccount
from app.models.users import User
from app.services.orchestration.agent_orchestration_service import orchestration_service
from app.services.orchestration.journey_resumption_service import journey_resumption_service
from app.websocket.socket_emitter import socket_emitter

router = APIRouter(prefix="/cases", tags=["cases"])


# ── Request / Response models ─────────────────────────────────────────────────

class InitiateCaseRequest(BaseModel):
    client_id: UUID | None = None       # omitted by clients (auto-filled from JWT sub)
    selected_products: list[str]
    assigned_advisor_id: UUID | None = None
    case_name: str | None = None        # stored in metadata
    legal_entity_name: str | None = None  # for institutional cases; used as case_name when no case_name supplied
    metadata: dict[str, Any] = {}


_STAGE_PROGRESS: dict[str, int] = {
    "INTAKE": 10,
    "REVIEW": 25,           # Advisor Review (early gate after intake)
    "SALES_REVIEW": 40,
    "KYC": 55,
    "PARALLEL_PRODUCTS": 75,
    "COMPLETE": 100,
    "ESCALATED": 65,
}

_PRODUCT_STATUS_PROGRESS: dict[str, int] = {
    "PENDING": 0,
    "IN_PROGRESS": 50,
    "COMPLETE": 100,
    "FAILED": 0,
    "SKIPPED": 100,
}


class ProductTrackOut(BaseModel):
    id: UUID
    product_code: str
    product_name: str = ""
    status: str
    progress: int = 0
    steps_total: int = 0
    steps_completed: int = 0
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class CaseSummaryOut(BaseModel):
    id: UUID
    client_id: UUID
    status: str
    current_stage: str
    selected_products: list[str]
    assigned_advisor_id: UUID | None
    created_at: datetime
    updated_at: datetime
    product_tracks: list[ProductTrackOut]

    model_config = {"from_attributes": True}


class CaseDetailOut(BaseModel):
    id: UUID
    client_id: UUID
    status: str
    current_stage: str
    selected_products: list[str]
    shared_context: dict[str, Any]
    assigned_advisor_id: UUID | None
    sla_deadline: datetime | None
    completed_at: datetime | None
    extra_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    product_tracks: list[ProductTrackOut]

    model_config = {"from_attributes": True}


class CaseProgressOut(BaseModel):
    case_id: UUID
    client_id: UUID
    client_name: str
    case_name: str | None
    current_stage: str
    status: str
    overall_progress: int
    questionnaire_pct: float
    documents_total: int
    documents_received: int
    documents_approved: int
    products: list[ProductTrackOut]
    kyc_status: str | None
    escalated: bool
    is_institutional: bool = False


class CaseListOut(BaseModel):
    id: UUID
    client_id: UUID
    client_name: str
    case_name: str | None
    status: str
    current_stage: str
    selected_products: list[str]
    percentage: float
    created_at: datetime
    updated_at: datetime
    assigned_advisor_name: str | None = None


class ResumeResponse(BaseModel):
    case_id: UUID
    message: str
    stage: str


class CollectedFieldsOut(BaseModel):
    client_data: dict[str, Any]


class ClientAccountOut(BaseModel):
    account_number: str
    product: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionSchemaItem(BaseModel):
    question_key: str
    section: str
    label: str
    question_text: str
    order_index: int
    field_type: str
    options: list[str] | None = None
    validation_rules: dict[str, Any] | None = None
    show_if: dict[str, Any] | None = None


class QuestionnaireSchemaOut(BaseModel):
    fields: list[QuestionSchemaItem]


class UpdateCollectedFieldRequest(BaseModel):
    question_key: str
    value: Any


class ProductOut(BaseModel):
    id: UUID
    product_code: str
    name: str
    description: str | None
    product_type: str

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_case_or_404(case_id: UUID, db: AsyncSession) -> OnboardingCase:
    result = await db.execute(
        select(OnboardingCase)
        .options(selectinload(OnboardingCase.case_products))
        .where(OnboardingCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise NotFoundError("OnboardingCase", str(case_id))
    return case


def _case_products_to_tracks(case: OnboardingCase) -> list[ProductTrackOut]:
    return [ProductTrackOut.model_validate(cp) for cp in case.case_products]


def _build_product_track(cp: CaseProduct) -> ProductTrackOut:
    steps = cp.steps or []
    completed = sum(1 for s in steps if s.status in ("COMPLETE", "SKIPPED"))
    product_name = cp.product.name if cp.product else cp.product_code
    # Fall back to the product's defined step sequence when runtime steps
    # haven't been created yet, so we show e.g. "0/4" instead of "0/0".
    step_sequence = (cp.product.step_sequence or []) if cp.product else []
    steps_total = len(steps) if steps else len(step_sequence)
    if steps:
        progress = round(completed / len(steps) * 100)
    else:
        progress = _PRODUCT_STATUS_PROGRESS.get(cp.status, 0)
    return ProductTrackOut(
        id=cp.id,
        product_code=cp.product_code,
        product_name=product_name,
        status=cp.status,
        progress=progress,
        steps_total=steps_total,
        steps_completed=completed,
        started_at=cp.started_at,
        completed_at=cp.completed_at,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/products", response_model=list[ProductOut])
async def list_products(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[ProductOut]:
    query = select(Product).where(Product.is_active.is_(True))
    product_type = "retail" if current_user.get("role") == "client" else "institutional"
    query = query.where(Product.product_type == product_type)
    query = query.order_by(Product.name)
    result = await db.execute(query)
    return [ProductOut.model_validate(p) for p in result.scalars().all()]


@router.get("", response_model=list[CaseListOut])
async def list_cases(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[CaseListOut]:
    AdvisorUser = User.__table__.alias("advisor_user")
    query = (
        select(OnboardingCase, Client, AdvisorUser.c.first_name, AdvisorUser.c.last_name)
        .join(Client, OnboardingCase.client_id == Client.id)
        .outerjoin(AdvisorUser, OnboardingCase.assigned_advisor_id == AdvisorUser.c.id)
        .order_by(OnboardingCase.updated_at.desc())
    )

    # Clients may only see their own cases
    if current_user.get("role") == "client":
        query = query.where(OnboardingCase.client_id == UUID(current_user["sub"]))

    result = await db.execute(query)
    rows = result.all()
    return [
        CaseListOut(
            id=case.id,
            client_id=case.client_id,
            client_name=f"{client.first_name} {client.last_name}",
            case_name=(case.extra_metadata or {}).get("case_name"),
            status=case.status,
            current_stage=case.current_stage,
            selected_products=case.selected_products,
            percentage=case.percentage,
            created_at=case.created_at,
            updated_at=case.updated_at,
            assigned_advisor_name=f"{adv_first} {adv_last}" if adv_first else None,
        )
        for case, client, adv_first, adv_last in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CaseSummaryOut)
async def initiate_case(
    body: InitiateCaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CaseSummaryOut:
    role = current_user.get("role", "")

    # Clients always create cases for themselves; advisors/admins must supply client_id
    if role == "client":
        client_id = UUID(current_user["sub"])
    elif body.client_id is not None:
        client_id = body.client_id
    else:
        raise ConflictError("client_id is required for advisor/admin case creation")

    if not body.selected_products:
        raise ConflictError("At least one product must be selected")

    # Validate products exist
    product_rows = await db.execute(
        select(Product).where(Product.product_code.in_(body.selected_products))
    )
    products = product_rows.scalars().all()
    found_codes = {p.product_code for p in products}
    unknown = set(body.selected_products) - found_codes
    if unknown:
        raise ConflictError(f"Unknown product codes: {sorted(unknown)}")

    effective_case_name = body.case_name or body.legal_entity_name
    if effective_case_name:
        duplicate = await db.execute(
            select(OnboardingCase).where(
                OnboardingCase.client_id == client_id,
                func.lower(OnboardingCase.extra_metadata["case_name"].astext)
                == effective_case_name.strip().lower(),
            )
        )
        if duplicate.scalar_one_or_none() is not None:
            raise ConflictError(
                f"A case named '{effective_case_name.strip()}' already exists. Please choose a different name."
            )

    resolved_case_name = body.case_name or body.legal_entity_name
    metadata = dict(body.metadata)
    if resolved_case_name:
        metadata["case_name"] = resolved_case_name
    if body.legal_entity_name:
        metadata["legal_entity_name"] = body.legal_entity_name

    case = OnboardingCase(
        client_id=client_id,
        selected_products=body.selected_products,
        assigned_advisor_id=body.assigned_advisor_id,
        extra_metadata=metadata,
    )
    db.add(case)
    await db.flush()

    for product in products:
        cp = CaseProduct(
            case_id=case.id,
            product_id=product.id,
            product_code=product.product_code,
        )
        db.add(cp)

    await db.commit()

    refreshed = await _get_case_or_404(case.id, db)

    # Look up the client so we can pass name/email to the notification agent.
    client_row = await db.execute(select(Client).where(Client.id == client_id))
    client = client_row.scalar_one_or_none()
    client_full_name = f"{client.first_name} {client.last_name}".strip() if client else ""
    client_email_addr = client.email if client else ""

    _case_name = (refreshed.extra_metadata or {}).get("case_name") or f"Case {str(refreshed.id)[:8]}"
    _product_display = ", ".join(
        p.replace("_", " ").title() for p in (refreshed.selected_products or [])
    )
    # Notify assigned advisor (if any) of the new case — use case name, not client name
    if body.assigned_advisor_id:
        advisor_result = await db.execute(select(User).where(User.id == body.assigned_advisor_id))
        advisor = advisor_result.scalar_one_or_none()
        if advisor:
            asyncio.create_task(
                orchestration_service.publish_task(
                    TaskPacket(
                        from_agent=AgentID.NOTIFICATION,
                        to_agent=AgentID.NOTIFICATION,
                        task_type=TaskType.SEND_NOTIFICATION,
                        case_id=refreshed.id,
                        client_id=client_id,
                        priority="NORMAL",
                        payload={
                            "template": "advisor_case_assigned",
                            "case_name": _case_name,
                            "client_name": client_full_name,
                            "selected_products": refreshed.selected_products or [],
                            "recipient_email": advisor.email,
                            "user_type": "advisor",
                        },
                    )
                )
            )
            await socket_emitter.notify_user(body.assigned_advisor_id, {
                "notification_id": "",
                "template_id": "advisor_case_assigned_inapp",
                "channel": "in_app",
                "subject": f"New case — {_case_name}",
                "body_preview": (
                    f"A new onboarding case **{_case_name}** for {client_full_name} "
                    f"has been assigned to you. Products: {_product_display}."
                ),
                "priority": "NORMAL",
            })

    # Kick off agent workflow asynchronously — the HTTP response is returned
    # immediately; the orchestrator runs in the background via asyncio.Task.
    asyncio.create_task(
        orchestration_service.start_onboarding(
            case_id=refreshed.id,
            client_id=refreshed.client_id,
            selected_products=refreshed.selected_products,
            client_name=client_full_name,
            client_email=client_email_addr,
            case_name=_case_name,
        )
    )

    return CaseSummaryOut(
        id=refreshed.id,
        client_id=refreshed.client_id,
        status=refreshed.status,
        current_stage=refreshed.current_stage,
        selected_products=refreshed.selected_products,
        assigned_advisor_id=refreshed.assigned_advisor_id,
        created_at=refreshed.created_at,
        updated_at=refreshed.updated_at,
        product_tracks=_case_products_to_tracks(refreshed),
    )


def _assert_case_access(case: OnboardingCase, current_user: dict) -> None:
    if current_user.get("role") == "client" and str(case.client_id) != current_user["sub"]:
        from app.api.error_handlers import NotFoundError
        raise NotFoundError("OnboardingCase", str(case.id))


@router.get("/{case_id}", response_model=CaseDetailOut)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CaseDetailOut:
    case = await _get_case_or_404(case_id, db)
    _assert_case_access(case, current_user)
    return CaseDetailOut(
        id=case.id,
        client_id=case.client_id,
        status=case.status,
        current_stage=case.current_stage,
        selected_products=case.selected_products,
        shared_context=case.shared_context,
        assigned_advisor_id=case.assigned_advisor_id,
        sla_deadline=case.sla_deadline,
        completed_at=case.completed_at,
        extra_metadata=case.extra_metadata,
        created_at=case.created_at,
        updated_at=case.updated_at,
        product_tracks=_case_products_to_tracks(case),
    )


@router.get("/{case_id}/summary", response_model=CaseProgressOut)
async def get_case_summary(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CaseProgressOut:
    result = await db.execute(
        select(OnboardingCase)
        .options(
            selectinload(OnboardingCase.client),
            selectinload(OnboardingCase.case_products).selectinload(CaseProduct.product),
            selectinload(OnboardingCase.case_products).selectinload(CaseProduct.steps),
        )
        .where(OnboardingCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise NotFoundError("OnboardingCase", str(case_id))
    _assert_case_access(case, current_user)

    doc_result = await db.execute(
        select(Document.status).where(Document.case_id == case_id)
    )
    doc_statuses = doc_result.scalars().all()
    total_docs = len(doc_statuses)
    received = sum(1 for s in doc_statuses if s not in ("NOT_REQUESTED", "REQUESTED"))
    approved = sum(1 for s in doc_statuses if s == "APPROVED")

    # Use the persisted percentage column (updated after each question/doc/KYC event)
    questionnaire_pct = case.percentage

    ctx = case.shared_context or {}
    stage = case.current_stage
    client = case.client
    client_name = f"{client.first_name} {client.last_name}" if client else "Unknown"
    escalated = stage == "ESCALATED" or bool(ctx.get("escalated", False))

    # Determine if the case involves at least one institutional product
    is_institutional = False
    if case.selected_products:
        inst_check = await db.execute(
            select(Product).where(
                Product.product_code.in_(case.selected_products),
                Product.product_type == "institutional",
            )
        )
        is_institutional = inst_check.scalar_one_or_none() is not None

    return CaseProgressOut(
        case_id=case.id,
        client_id=case.client_id,
        client_name=client_name,
        case_name=(case.extra_metadata or {}).get("case_name"),
        current_stage=stage,
        status=case.status,
        overall_progress=round(case.percentage),
        questionnaire_pct=questionnaire_pct,
        documents_total=total_docs,
        documents_received=received,
        documents_approved=approved,
        products=[_build_product_track(cp) for cp in case.case_products],
        kyc_status=ctx.get("kyc_status"),
        escalated=escalated,
        is_institutional=is_institutional,
    )


@router.get("/{case_id}/account", response_model=list[ClientAccountOut])
async def get_case_account(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[ClientAccountOut]:
    """Return one account per product for a completed case."""
    case = await _get_case_or_404(case_id, db)
    _assert_case_access(case, current_user)

    result = await db.execute(
        select(ClientAccount).where(ClientAccount.case_id == case_id)
    )
    accounts = result.scalars().all()
    if not accounts:
        raise NotFoundError("ClientAccount", str(case_id))
    return [ClientAccountOut.model_validate(a) for a in accounts]


@router.get("/{case_id}/questionnaire-schema", response_model=QuestionnaireSchemaOut)
async def get_questionnaire_schema(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> QuestionnaireSchemaOut:
    """Return all questions for questionnaires that match the case's selected products."""
    # Verify case access and fetch selected products in one query
    case_row = await db.execute(
        select(OnboardingCase.client_id, OnboardingCase.selected_products)
        .where(OnboardingCase.id == case_id)
    )
    row = case_row.one_or_none()
    if row is None:
        raise NotFoundError("OnboardingCase", str(case_id))
    client_id, selected_products = row
    if current_user.get("role") == "client" and str(client_id) != current_user["sub"]:
        raise NotFoundError("OnboardingCase", str(case_id))

    # Resolve product codes → product IDs
    product_ids: list[UUID] = []
    if selected_products:
        prod_result = await db.execute(
            select(Product.id).where(Product.product_code.in_(selected_products))
        )
        product_ids = list(prod_result.scalars().all())

    # Find questionnaire IDs whose questions are linked to the selected products
    questionnaire_ids: list[UUID] = []
    if product_ids:
        q_id_result = await db.execute(
            select(OnboardingQuestion.questionnaire_id)
            .where(OnboardingQuestion.product_id.in_(product_ids))
            .distinct()
        )
        questionnaire_ids = list(q_id_result.scalars().all())

    # Fall back to session-linked questionnaire, then first active questionnaire
    if not questionnaire_ids:
        session_row = await db.execute(
            select(OnboardingQuestionSession.questionnaire_id)
            .where(OnboardingQuestionSession.case_id == case_id)
            .limit(1)
        )
        fallback_id = session_row.scalar_one_or_none()
        if fallback_id is None:
            q_row = await db.execute(
                select(OnboardingQuestionnaire.id)
                .where(OnboardingQuestionnaire.is_active.is_(True))
                .limit(1)
            )
            fallback_id = q_row.scalar_one_or_none()
        if fallback_id:
            questionnaire_ids = [fallback_id]

    if not questionnaire_ids:
        return QuestionnaireSchemaOut(fields=[])

    oq_result = await db.execute(
        select(OnboardingQuestion)
        .where(OnboardingQuestion.questionnaire_id.in_(questionnaire_ids))
        .order_by(OnboardingQuestion.order_index)
    )
    questions = oq_result.scalars().all()

    _DB_TYPE_MAP = {
        "text": "text", "number": "number", "date": "date",
        "select": "choice", "multi_select": "multi_choice",
        "boolean": "choice", "currency": "number",
    }

    # Deduplicate on (question_key, section): the same question in the same
    # section across multiple product questionnaires is shown only once.
    # A question_key that appears in different sections across products is kept
    # in each of its sections independently.
    seen: set[tuple[str, str]] = set()
    fields: list[QuestionSchemaItem] = []

    for q in questions:
        dedup_key = (q.question_key, q.section)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        label = q.question_text or (q.extra_metadata or {}).get("label") or _fmt_key(q.question_key)
        field_type = _DB_TYPE_MAP.get(q.question_type, "text")
        options = list(q.options) if q.options else None
        if q.question_type == "boolean":
            options = ["Yes", "No"]

        fields.append(QuestionSchemaItem(
            question_key=q.question_key,
            section=q.section,
            label=label,
            question_text=q.question_text,
            order_index=q.order_index,
            field_type=field_type,
            options=options,
            validation_rules=dict(q.validation_rules) if q.validation_rules else None,
            show_if=dict(q.show_if) if q.show_if else None,
        ))

    return QuestionnaireSchemaOut(fields=fields)


def _fmt_key(key: str) -> str:
    """snake_case → Title Case Words, strip common prefixes."""
    return key.replace("_", " ").strip().title()


@router.get("/{case_id}/collected-fields", response_model=CollectedFieldsOut)
async def get_collected_fields(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CollectedFieldsOut:
    result = await db.execute(
        select(OnboardingCase.shared_context, OnboardingCase.client_id).where(OnboardingCase.id == case_id)
    )
    row = result.one_or_none()
    if row is None:
        raise NotFoundError("OnboardingCase", str(case_id))
    shared_ctx, client_id = row
    if current_user.get("role") == "client" and str(client_id) != current_user["sub"]:
        raise NotFoundError("OnboardingCase", str(case_id))
    client_data = (shared_ctx or {}).get("client_data", {})
    return CollectedFieldsOut(client_data=client_data)


@router.patch("/{case_id}/collected-fields", response_model=CollectedFieldsOut)
async def update_collected_field(
    case_id: UUID,
    body: UpdateCollectedFieldRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CollectedFieldsOut:
    result = await db.execute(
        select(
            OnboardingCase.client_id,
            OnboardingCase.shared_context,
            OnboardingCase.current_stage,
            OnboardingCase.selected_products,
        ).where(OnboardingCase.id == case_id)
    )
    row = result.one_or_none()
    if row is None:
        raise NotFoundError("OnboardingCase", str(case_id))
    client_id, shared_ctx, current_stage, selected_products = row
    if current_user.get("role") == "client" and str(client_id) != current_user["sub"]:
        raise NotFoundError("OnboardingCase", str(case_id))

    shared_ctx = dict(shared_ctx or {})
    client_data = dict(shared_ctx.get("client_data", {}))
    client_data[body.question_key] = body.value
    shared_ctx["client_data"] = client_data

    await db.execute(
        sa_update(OnboardingCase)
        .where(OnboardingCase.id == case_id)
        .values(shared_context=shared_ctx)
    )
    await db.commit()

    return CollectedFieldsOut(client_data=client_data)


class PatchProductsRequest(BaseModel):
    selected_products: list[str]


class PatchProductsResponse(BaseModel):
    case_id: UUID
    selected_products: list[str]


@router.patch("/{case_id}/products", response_model=PatchProductsResponse)
async def patch_case_products(
    case_id: UUID,
    body: PatchProductsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PatchProductsResponse:
    case = await _get_case_or_404(case_id, db)
    _assert_case_access(case, current_user)

    if not body.selected_products:
        raise ConflictError("At least one product must be selected")

    product_rows = await db.execute(
        select(Product).where(Product.product_code.in_(body.selected_products))
    )
    products = product_rows.scalars().all()
    found_codes = {p.product_code for p in products}
    unknown = set(body.selected_products) - found_codes
    if unknown:
        raise ConflictError(f"Unknown product codes: {sorted(unknown)}")

    new_codes = set(body.selected_products)
    old_codes = set(case.selected_products)

    # Remove CaseProduct rows for de-selected products (only safe while PENDING)
    for cp in list(case.case_products):
        if cp.product_code not in new_codes and cp.status == "PENDING":
            await db.delete(cp)

    # Add CaseProduct rows for newly selected products
    existing_codes = {cp.product_code for cp in case.case_products if cp.product_code in new_codes}
    for product in products:
        if product.product_code not in existing_codes and product.product_code not in old_codes:
            db.add(CaseProduct(
                case_id=case.id,
                product_id=product.id,
                product_code=product.product_code,
            ))

    await db.execute(
        sa_update(OnboardingCase)
        .where(OnboardingCase.id == case_id)
        .values(selected_products=body.selected_products)
    )
    await db.commit()
    return PatchProductsResponse(case_id=case_id, selected_products=body.selected_products)


class PatchPercentageRequest(BaseModel):
    percentage: float


class PatchPercentageResponse(BaseModel):
    case_id: UUID
    percentage: float


@router.patch("/{case_id}/percentage", response_model=PatchPercentageResponse)
async def patch_case_percentage(
    case_id: UUID,
    body: PatchPercentageRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("client", "advisor", "admin", "sales_manager")),
) -> PatchPercentageResponse:
    await _get_case_or_404(case_id, db)
    await db.execute(
        sa_update(OnboardingCase)
        .where(OnboardingCase.id == case_id)
        .values(percentage=body.percentage)
    )
    await db.commit()
    return PatchPercentageResponse(case_id=case_id, percentage=body.percentage)


class PatchStatusRequest(BaseModel):
    status: str
    current_stage: str | None = None


class PatchStatusResponse(BaseModel):
    case_id: UUID
    status: str


@router.patch("/{case_id}/status", response_model=PatchStatusResponse)
async def patch_case_status(
    case_id: UUID,
    body: PatchStatusRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("client", "advisor", "admin", "sales_manager")),
) -> PatchStatusResponse:
    await _get_case_or_404(case_id, db)
    values: dict = {"status": body.status}
    if body.current_stage is not None:
        values["current_stage"] = body.current_stage
    await db.execute(
        sa_update(OnboardingCase)
        .where(OnboardingCase.id == case_id)
        .values(**values)
    )
    await db.commit()
    return PatchStatusResponse(case_id=case_id, status=body.status)


class SubmitIntakeResponse(BaseModel):
    case_id: UUID
    status: str
    current_stage: str


@router.post("/{case_id}/submit-intake", status_code=status.HTTP_200_OK, response_model=SubmitIntakeResponse)
async def submit_intake(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("client", "advisor", "admin", "sales_manager")),
) -> SubmitIntakeResponse:
    """Client submits their completed application (forms + documents).

    All cases advance to REVIEW (Advisor Review) so the advisor can verify
    documents before the workflow continues:
    - Institutional: REVIEW → SALES_REVIEW (once all docs approved)
    - Retail: REVIEW → KYC (once all docs approved)
    """
    case = await _get_case_or_404(case_id, db)
    _assert_case_access(case, current_user)

    selected = case.selected_products or []
    _sub_case_name = (case.extra_metadata or {}).get("case_name") or f"Case {str(case_id)[:8]}"
    _sub_products = ", ".join(p.replace("_", " ").title() for p in selected)

    # Resolve client info for notifications
    client_row = await db.execute(select(Client).where(Client.id == case.client_id))
    _sub_client = client_row.scalar_one_or_none()
    _sub_client_name = f"{_sub_client.first_name} {_sub_client.last_name}".strip() if _sub_client else "Client"

    # All cases go to Advisor Review first
    next_stage = "REVIEW"
    await db.execute(
        sa_update(OnboardingCase)
        .where(OnboardingCase.id == case_id)
        .values(status="REVIEW", current_stage="REVIEW", percentage=25)
    )
    await db.commit()

    # Emit WebSocket stage change
    await socket_emitter.case_stage_changed(case_id, {
        "case_id": str(case_id),
        "stage": next_stage,
        "triggered_by": "client_submitted_intake",
    })

    # ── Submission notifications (both paths) ─────────────────────────────────
    if _sub_client:
        for tmpl in ("case_submitted", "case_submitted_inapp"):
            asyncio.create_task(orchestration_service.publish_task(
                TaskPacket(
                    from_agent=AgentID.NOTIFICATION,
                    to_agent=AgentID.NOTIFICATION,
                    task_type=TaskType.SEND_NOTIFICATION,
                    case_id=case_id,
                    client_id=case.client_id,
                    priority="NORMAL",
                    payload={
                        "template": tmpl,
                        "case_name": _sub_case_name,
                        "client_name": _sub_client_name,
                        "selected_products": selected,
                        "recipient_email": _sub_client.email,
                    },
                )
            ))

    if case.assigned_advisor_id:
        await socket_emitter.notify_user(case.assigned_advisor_id, {
            "notification_id": "",
            "template_id": "advisor_case_submitted_inapp",
            "channel": "in_app",
            "subject": f"Case submitted — {_sub_case_name}",
            "body_preview": (
                f"{_sub_client_name} has submitted their application for "
                f"**{_sub_case_name}**. Products: {_sub_products}. "
                f"Next stage: {next_stage.replace('_', ' ').title()}."
            ),
            "priority": "NORMAL",
        })

    return SubmitIntakeResponse(case_id=case_id, status=next_stage, current_stage=next_stage)


async def _create_sales_review_background(
    case_id: UUID,
    client_id: UUID,
    case_name: str,
    client_name: str,
    selected_products: list[str],
) -> None:
    """Create the SalesManagerReview record in a background task (owns its own DB session)."""
    from app.database import AsyncSessionLocal
    from app.services.sales_review.sales_review_service import sales_review_service

    async with AsyncSessionLocal() as db:
        try:
            await sales_review_service.create_review(
                case_id=case_id,
                client_id=client_id,
                payload={
                    "case_name": case_name,
                    "client_name": client_name,
                    "selected_products": selected_products,
                },
                db=db,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(
                f"Failed to create SalesManagerReview for case {case_id}: {exc}"
            )


class AdvisorApproveResponse(BaseModel):
    case_id: UUID
    next_stage: str
    message: str


@router.post("/{case_id}/advisor-approve", status_code=status.HTTP_200_OK, response_model=AdvisorApproveResponse)
async def advisor_approve_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("advisor", "admin")),
) -> AdvisorApproveResponse:
    """Advisor advances the case out of the Advisor Review (REVIEW) stage.

    Requirements:
    - Case must be in REVIEW stage.
    - ALL documents must have status 'APPROVED'.

    Routing:
    - Institutional product → SALES_REVIEW (creates SalesManagerReview record).
    - Retail only → KYC (triggers KYC agent).
    """
    case = await _get_case_or_404(case_id, db)

    if case.current_stage != "REVIEW":
        raise ConflictError(
            f"Case is not in Advisor Review stage (current: {case.current_stage})"
        )

    # Verify every document is approved
    doc_result = await db.execute(
        select(Document.status).where(Document.case_id == case_id)
    )
    doc_statuses = doc_result.scalars().all()

    if not doc_statuses:
        raise ConflictError("No documents found. All documents must be uploaded and approved before advancing.")

    non_approved = [s for s in doc_statuses if (s or "").upper() != "APPROVED"]
    if non_approved:
        raise ConflictError(
            f"All documents must be approved before advancing. "
            f"{len(non_approved)} document(s) are not yet approved."
        )

    selected = case.selected_products or []
    _case_name = (case.extra_metadata or {}).get("case_name") or f"Case {str(case_id)[:8]}"

    client_row = await db.execute(select(Client).where(Client.id == case.client_id))
    _client = client_row.scalar_one_or_none()
    _client_name = f"{_client.first_name} {_client.last_name}".strip() if _client else "Client"

    # Determine institutional vs retail
    has_institutional = False
    if selected:
        inst_result = await db.execute(
            select(Product).where(
                Product.product_code.in_(selected),
                Product.product_type == "institutional",
            )
        )
        has_institutional = inst_result.scalar_one_or_none() is not None

    if has_institutional:
        # Institutional: REVIEW → SALES_REVIEW
        next_stage = "SALES_REVIEW"
        await db.execute(
            sa_update(OnboardingCase)
            .where(OnboardingCase.id == case_id)
            .values(status="SALES_REVIEW", current_stage="SALES_REVIEW", percentage=40)
        )
        await db.commit()

        asyncio.create_task(
            _create_sales_review_background(
                case_id=case_id,
                client_id=case.client_id,
                case_name=_case_name,
                client_name=_client_name,
                selected_products=selected,
            )
        )
        message = "All documents approved — case advanced to Sales Review."
    else:
        # Retail: REVIEW → KYC
        next_stage = "KYC"
        await db.execute(
            sa_update(OnboardingCase)
            .where(OnboardingCase.id == case_id)
            .values(status="KYC", current_stage="KYC", percentage=55)
        )
        await db.commit()

        asyncio.create_task(
            orchestration_service.publish_task(
                TaskPacket(
                    from_agent=AgentID.ORCHESTRATOR,
                    to_agent=AgentID.KYC_COMPLIANCE,
                    task_type=TaskType.RUN_KYC_CHECK,
                    case_id=case_id,
                    client_id=case.client_id,
                    priority="HIGH",
                    payload={
                        "selected_products": selected,
                        "case_name": _case_name,
                        "client_name": _client_name,
                    },
                )
            )
        )
        message = "All documents approved — case advanced to KYC."

    await socket_emitter.case_stage_changed(case_id, {
        "case_id": str(case_id),
        "stage": next_stage,
        "triggered_by": "advisor_approved",
    })

    return AdvisorApproveResponse(case_id=case_id, next_stage=next_stage, message=message)


@router.post("/{case_id}/resume", status_code=status.HTTP_202_ACCEPTED, response_model=ResumeResponse)
async def resume_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("advisor", "admin", "sales_manager")),
) -> ResumeResponse:
    case = await _get_case_or_404(case_id, db)
    asyncio.create_task(journey_resumption_service.resume_case(case_id=case.id))
    return ResumeResponse(
        case_id=case.id,
        message="Resume request accepted — JourneyResumptionService will restore state and re-spawn agents",
        stage=case.current_stage,
    )
