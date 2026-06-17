from __future__ import annotations

from enum import StrEnum


class AuditEventType(StrEnum):
    # ── Case lifecycle ────────────────────────────────────────────────────────
    CASE_INITIATED = "CASE_INITIATED"
    STAGE_ADVANCED = "STAGE_ADVANCED"
    CASE_COMPLETED = "CASE_COMPLETED"
    CASE_REJECTED = "CASE_REJECTED"
    JOURNEY_PAUSED = "JOURNEY_PAUSED"
    JOURNEY_RESUMED = "JOURNEY_RESUMED"

    # ── Client ────────────────────────────────────────────────────────────────
    CLIENT_CREATED = "CLIENT_CREATED"
    CLIENT_UPDATED = "CLIENT_UPDATED"

    # ── Data collection ───────────────────────────────────────────────────────
    DATA_COLLECTION_STARTED = "DATA_COLLECTION_STARTED"
    DATA_COLLECTED = "DATA_COLLECTED"
    DATA_COLLECTION_COMPLETE = "DATA_COLLECTION_COMPLETE"

    # ── KYC ───────────────────────────────────────────────────────────────────
    KYC_CHECK_STARTED = "KYC_CHECK_STARTED"
    KYC_RISK_SCORED = "KYC_RISK_SCORED"
    KYC_PASSED = "KYC_PASSED"
    KYC_ESCALATED = "KYC_ESCALATED"

    # ── Document ─────────────────────────────────────────────────────────────
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_STATUS_CHANGED = "DOCUMENT_STATUS_CHANGED"
    DOCUMENT_VALIDATION_STARTED = "DOCUMENT_VALIDATION_STARTED"
    DOCUMENT_VALIDATED = "DOCUMENT_VALIDATED"
    DOCUMENT_DIFF_COMPUTED = "DOCUMENT_DIFF_COMPUTED"

    # ── Product onboarding ────────────────────────────────────────────────────
    PRODUCT_ONBOARDING_STARTED = "PRODUCT_ONBOARDING_STARTED"
    PRODUCT_ONBOARDING_COMPLETE = "PRODUCT_ONBOARDING_COMPLETE"
    SUITABILITY_ASSESSED = "SUITABILITY_ASSESSED"

    # ── Human review ─────────────────────────────────────────────────────────
    REVIEW_CREATED = "REVIEW_CREATED"
    REVIEW_DECIDED = "REVIEW_DECIDED"
    REVIEW_APPROVED = "REVIEW_APPROVED"
    REVIEW_REJECTED = "REVIEW_REJECTED"
    REVIEW_MORE_INFO_REQUESTED = "REVIEW_MORE_INFO_REQUESTED"

    # ── Compliance ───────────────────────────────────────────────────────────
    COMPLIANCE_DECISION = "COMPLIANCE_DECISION"
    CHECKPOINT_RULE_APPLIED = "CHECKPOINT_RULE_APPLIED"
    CHECKPOINT_RULE_CREATED = "CHECKPOINT_RULE_CREATED"
    CHECKPOINT_RULE_UPDATED = "CHECKPOINT_RULE_UPDATED"
    CHECKPOINT_RULE_DELETED = "CHECKPOINT_RULE_DELETED"
    CHECKPOINT_RULES_RESET = "CHECKPOINT_RULES_RESET"

    # ── Agent task ───────────────────────────────────────────────────────────
    AGENT_TASK_ASSIGNED = "AGENT_TASK_ASSIGNED"
    AGENT_TASK_COMPLETED = "AGENT_TASK_COMPLETED"
    AGENT_TASK_FAILED = "AGENT_TASK_FAILED"
    SKILL_INVOKED = "SKILL_INVOKED"

    # ── MCP ───────────────────────────────────────────────────────────────────
    MCP_TOOL_CALLED = "MCP_TOOL_CALLED"

    # ── Notification ─────────────────────────────────────────────────────────
    NOTIFICATION_SENT = "NOTIFICATION_SENT"

    # ── Auth ──────────────────────────────────────────────────────────────────
    USER_SIGNED_UP = "USER_SIGNED_UP"
    USER_LOGGED_IN = "USER_LOGGED_IN"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"

    # ── Admin / LLM config ────────────────────────────────────────────────────
    LLM_CONFIG_UPDATED = "LLM_CONFIG_UPDATED"
    VALIDATION_PROMPT_UPDATED = "VALIDATION_PROMPT_UPDATED"
    VALIDATION_PROMPT_RESET = "VALIDATION_PROMPT_RESET"
    CONFIG_CHANGE = "CONFIG_CHANGE"

    # ── SLA (Phase 5) ─────────────────────────────────────────────────────────
    SLA_WARNING = "SLA_WARNING"
    SLA_BREACH = "SLA_BREACH"

    # ── Product activation / decline (Phase 4.6) ─────────────────────────────
    PRODUCT_ACTIVATED = "PRODUCT_ACTIVATED"
    PRODUCT_DECLINED = "PRODUCT_DECLINED"

    # ── Fraud screening (Phase 4.6) ───────────────────────────────────────────
    FRAUD_FLAGGED = "FRAUD_FLAGGED"
    FRAUD_CLEARED = "FRAUD_CLEARED"

    # ── Document scope (Phase 4.5) ────────────────────────────────────────────
    DOCUMENT_SCOPE_ASSIGNED = "DOCUMENT_SCOPE_ASSIGNED"


class AuditEventCategory(StrEnum):
    AGENT_ACTION = "AGENT_ACTION"
    KYC = "KYC"
    DOCUMENT = "DOCUMENT"
    COMPLIANCE = "COMPLIANCE"
    NOTIFICATION = "NOTIFICATION"
    AUTH = "AUTH"
    ADMIN = "ADMIN"
