from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal, TypedDict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


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
    from_agent: str
    to_agent: str
    task_type: str
    case_id: UUID
    client_id: UUID
    priority: Literal["LOW", "NORMAL", "HIGH", "CRITICAL"] = "NORMAL"
    payload: dict[str, Any] = Field(default_factory=dict)
    expected_schema: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ttl: int = 300  # seconds


class TaskResponse(BaseModel):
    task_id: UUID
    from_agent: str
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


_WEALTH_EXTENSION_FIELDS = frozenset({
    "kyc_status", "kyc_risk_score",
    "sales_review_id", "sales_review_decision",
    "escalation_reason", "human_review_id",
})


class OnboardingState(BaseModel):
    """Shared context object passed between all CADF agents via the ContextStoreService.

    Generic typed core holds domain-agnostic fields.  Domain-specific data (e.g.
    KYC outcome, sales review) lives in `extra` and is accessed via WealthExtension.
    """

    # ── Generic typed core ──────────────────────────────────────────────────────
    case_id: UUID
    client_id: UUID
    stage: str = OnboardingStage.INTAKE
    selected_products: list[str] = Field(default_factory=list)
    product_tracks: dict[str, ProductTrackState] = Field(default_factory=dict)
    priority_tier: str = "standard"

    # Data collected by the Customer Service Agent
    client_data: dict[str, Any] = Field(default_factory=dict)
    documents_required: list[str] = Field(default_factory=list)
    documents_received: list[str] = Field(default_factory=list)

    # Optimistic-lock version for the ContextStoreService
    version: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ── Extension bag: domain-specific fields (wealth: KYC, sales review, etc.) ─
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _migrate_flat_wealth_fields(cls, data: Any) -> Any:
        """Migrate old flat wealth extension fields into the extra bag.

        Old shared_context JSONB rows had kyc_status etc. at top level.
        This validator migrates them transparently on load so pre-Phase-2
        records continue to work without a data migration.
        """
        if not isinstance(data, dict):
            return data
        flat = {k: v for k, v in data.items() if k in _WEALTH_EXTENSION_FIELDS}
        if not flat:
            return data
        extra: dict[str, Any] = dict(data.get("extra") or {})
        for k, v in flat.items():
            if k not in extra:  # extra wins when both present
                extra[k] = v
        data = {k: v for k, v in data.items() if k not in _WEALTH_EXTENSION_FIELDS}
        data["extra"] = extra
        return data


class WealthExtension:
    """Typed accessor for wealth-management-specific fields stored in OnboardingState.extra."""

    __slots__ = ("_extra",)

    def __init__(self, extra: dict[str, Any]) -> None:
        self._extra = extra

    @classmethod
    def from_state(cls, state: OnboardingState) -> "WealthExtension":
        return cls(state.extra)

    @property
    def kyc_status(self) -> str:
        return self._extra.get("kyc_status", "PENDING")

    @property
    def kyc_risk_score(self) -> float | None:
        return self._extra.get("kyc_risk_score")

    @property
    def sales_review_id(self) -> UUID | None:
        val = self._extra.get("sales_review_id")
        return UUID(str(val)) if val else None

    @property
    def sales_review_decision(self) -> str:
        return self._extra.get("sales_review_decision", "PENDING")

    @property
    def escalation_reason(self) -> str | None:
        return self._extra.get("escalation_reason")

    @property
    def human_review_id(self) -> UUID | None:
        val = self._extra.get("human_review_id")
        return UUID(str(val)) if val else None


class OnboardingStateDict(TypedDict, total=False):
    """LangGraph-compatible TypedDict mirroring OnboardingState.

    UUIDs and datetimes serialised as strings for Temporal payload compatibility.
    Used as the state type for all LangGraph StateGraph instances in Phase 0.5+.

    Wealth-specific fields (kyc_status, sales_review_decision, etc.) are no longer
    top-level keys — they live in `extra` (Phase 2).  _product_code and
    _product_track_status are Temporal routing hints and must stay in the typed core
    (Temporal's payload codec strips undeclared TypedDict keys).
    """

    case_id: str
    client_id: str
    stage: str
    selected_products: list[str]
    product_tracks: dict[str, dict[str, Any]]
    priority_tier: str
    client_data: dict[str, Any]
    documents_required: list[str]
    documents_received: list[str]
    version: int
    created_at: str
    updated_at: str
    # Activity-level routing hint set by graph terminal nodes
    next_stage: str | None
    # Set by OnboardingWorkflow when dispatching ProductOnboardingWorkflow child workflows
    _product_code: str
    _product_track_status: str
    # Domain-specific extension bag (wealth: kyc_status, sales_review_decision, etc.)
    extra: dict[str, Any]


# ── Temporal signal / workflow I/O models ─────────────────────────────────────

class StageAdvanceSignal(BaseModel):
    """Sent to OnboardingWorkflow.advance_stage signal handler."""

    to_stage: str
    payload: dict[str, Any] = Field(default_factory=dict)


class HumanReviewSignal(BaseModel):
    """Sent to OnboardingWorkflow.human_review_completed when human acts."""

    decision: str  # APPROVED | REJECTED | MORE_INFO_REQUESTED
    reviewer_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class OnboardingWorkflowInput(BaseModel):
    case_id: str
    client_id: str
    selected_products: list[str] = Field(default_factory=list)
    client_name: str = ""
    client_email: str = ""
    case_name: str = ""


class OnboardingWorkflowResult(BaseModel):
    final_stage: str
    case_id: str
