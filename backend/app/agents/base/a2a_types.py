from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentID(StrEnum):
    ORCHESTRATOR = "orchestrator"
    CUSTOMER_SERVICE = "customer_service"
    KYC_COMPLIANCE = "kyc_compliance"
    DOCUMENT_INTELLIGENCE = "document_intelligence"
    PRODUCT_ONBOARDING = "product_onboarding"
    COLLABORATION = "collaboration"
    CONTACT_CENTRE = "contact_centre"
    NOTIFICATION = "notification"
    SALES_MANAGER = "sales_manager"


class TaskType(StrEnum):
    # Orchestrator
    START_ONBOARDING = "start_onboarding"
    RESUME_ONBOARDING = "resume_onboarding"
    ADVANCE_STAGE = "advance_stage"
    # Customer Service
    COLLECT_CLIENT_DATA = "collect_client_data"
    CONTINUE_CONVERSATION = "continue_conversation"
    # KYC
    RUN_KYC_CHECK = "run_kyc_check"
    VERIFY_IDENTITY = "verify_identity"
    # Document Intelligence
    CLASSIFY_DOCUMENT = "classify_document"
    VALIDATE_DOCUMENT = "validate_document"
    EXTRACT_OCR = "extract_ocr"
    COMPUTE_DIFF = "compute_diff"
    # Product Onboarding
    ONBOARD_PRODUCT = "onboard_product"
    ASSESS_SUITABILITY = "assess_suitability"
    PRODUCT_TRACK_COMPLETE = "product_track_complete"
    # Collaboration
    CREATE_COLLABORATION_ROOM = "create_collaboration_room"
    ADD_COMMENT = "add_comment"
    # Contact Centre
    SUMMARISE_CALL = "summarise_call"
    GET_CLIENT_STATUS = "get_client_status"
    # Notification
    SEND_NOTIFICATION = "send_notification"
    SEND_ESCALATION_ALERT = "send_escalation_alert"
    # Sales Manager
    SALES_MANAGER_REVIEW = "sales_manager_review"
    SALES_MANAGER_DECIDE = "sales_manager_decide"
    # Generic
    ESCALATE = "escalate"
    HEALTH_CHECK = "health_check"


class OnboardingStage(StrEnum):
    INTAKE = "INTAKE"
    SALES_REVIEW = "SALES_REVIEW"
    KYC = "KYC"
    PARALLEL_PRODUCTS = "PARALLEL_PRODUCTS"
    REVIEW = "REVIEW"
    COMPLETE = "COMPLETE"
    ESCALATED = "ESCALATED"


class TaskPacket(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    from_agent: AgentID
    to_agent: AgentID
    task_type: TaskType
    case_id: UUID
    client_id: UUID
    priority: Literal["LOW", "NORMAL", "HIGH", "CRITICAL"] = "NORMAL"
    payload: dict[str, Any] = Field(default_factory=dict)
    expected_schema: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl: int = 300  # seconds


class TaskResponse(BaseModel):
    task_id: UUID
    from_agent: AgentID
    status: Literal["SUCCESS", "PARTIAL", "FAILED", "ESCALATED"]
    result: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] | None = None
    duration_ms: int = 0


class ProductTrackState(BaseModel):
    product_code: str
    stage: str = "PENDING"
    step: int = 0
    total_steps: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class OnboardingState(BaseModel):
    """Shared context object passed between all CADF agents via the ContextStoreService."""

    case_id: UUID
    client_id: UUID
    stage: OnboardingStage = OnboardingStage.INTAKE
    selected_products: list[str] = Field(default_factory=list)
    product_tracks: dict[str, ProductTrackState] = Field(default_factory=dict)

    # Data collected by the Customer Service Agent
    client_data: dict[str, Any] = Field(default_factory=dict)
    documents_required: list[str] = Field(default_factory=list)
    documents_received: list[str] = Field(default_factory=list)

    # KYC outcome
    kyc_status: Literal["PENDING", "PASSED", "FAILED", "ESCALATED"] = "PENDING"
    kyc_risk_score: float | None = None

    # Sales Manager review (institutional products only)
    sales_review_id: UUID | None = None
    sales_review_decision: Literal["PENDING", "APPROVED", "REJECTED", "MORE_INFO_REQUESTED"] = "PENDING"

    # Escalation / human review
    escalation_reason: str | None = None
    human_review_id: UUID | None = None

    # Optimistic-lock version for the ContextStoreService
    version: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
