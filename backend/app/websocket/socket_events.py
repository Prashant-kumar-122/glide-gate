from __future__ import annotations

from enum import StrEnum


class SocketEvent(StrEnum):
    # Agent-to-agent communication visible to frontend
    AGENT_MESSAGE = "agent_message"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETE = "task_complete"

    # Document lifecycle
    DOCUMENT_STATUS_CHANGED = "document_status_changed"
    DOCUMENT_UPLOADED = "document_uploaded"

    # KYC / compliance
    KYC_RESULT = "kyc_result"
    ESCALATION_TRIGGERED = "escalation_triggered"
    REVIEW_DECIDED = "review_decided"

    # Sales Manager review
    SALES_REVIEW_TRIGGERED = "sales_review_triggered"
    SALES_REVIEW_DECIDED = "sales_review_decided"

    # Product tracks
    PRODUCT_TRACK_UPDATE = "product_track_update"

    # Notifications & progress
    NOTIFICATION_SENT = "notification_sent"
    CASE_STAGE_CHANGED = "case_stage_changed"
    PROGRESS_UPDATE = "progress_update"

    # Workspace tasks
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"

    # Connection management
    JOIN_CASE_ROOM = "join_case_room"
    LEAVE_CASE_ROOM = "leave_case_room"
    ERROR = "error"
