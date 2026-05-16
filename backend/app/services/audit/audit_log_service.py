from __future__ import annotations

"""AuditLogService — append-only writes to event_logs (BRD FR-14, Section 10.2).

Rules enforced at the service layer:
- No UPDATE or DELETE methods exist; every call produces a new immutable row.
- Every agent decision, human review, status change, and MCP call MUST flow
  through this service so the audit trail is 100% complete.
- Callers may pass an open AsyncSession (fire-and-forget inside a request) or
  omit it; the service acquires its own session automatically when needed.
"""

from typing import Any
from uuid import UUID, uuid4

from loguru import logger

from app.models.agents import EventLog
from app.services.audit.audit_event_types import AuditEventCategory, AuditEventType


class AuditLogService:
    """Append-only wrapper around the event_logs table."""

    # ── Core write ────────────────────────────────────────────────────────────

    async def log(
        self,
        event_type: str | AuditEventType,
        *,
        event_category: str | AuditEventCategory | None = None,
        case_id: UUID | None = None,
        client_id: UUID | None = None,
        agent_id: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        actor_id: str | None = None,
        actor_role: str | None = None,
        payload: dict[str, Any] | None = None,
        is_compliance_event: bool = False,
        ip_address: str | None = None,
        db=None,
    ) -> EventLog:
        """Write one immutable audit event row.

        If *db* (AsyncSession) is provided the record is added to that session
        but NOT committed — the caller controls the transaction.  When *db* is
        None the service acquires its own session and commits immediately.
        """
        record = EventLog(
            id=uuid4(),
            case_id=case_id,
            client_id=client_id,
            agent_id=agent_id,
            event_type=str(event_type),
            event_category=str(event_category) if event_category else None,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_role=actor_role,
            payload=payload or {},
            is_compliance_event=is_compliance_event,
            ip_address=ip_address,
        )

        if db is not None:
            db.add(record)
        else:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                session.add(record)
                await session.commit()

        return record

    # ── Typed convenience helpers ─────────────────────────────────────────────

    async def log_agent_task_completed(
        self,
        agent_id: str,
        task_type: str,
        case_id: UUID | None,
        client_id: UUID | None,
        duration_ms: int,
        status: str,
        db=None,
    ) -> EventLog:
        event_type = (
            AuditEventType.AGENT_TASK_COMPLETED
            if status in ("SUCCESS", "PARTIAL")
            else AuditEventType.AGENT_TASK_FAILED
        )
        return await self.log(
            event_type=event_type,
            event_category=AuditEventCategory.AGENT_ACTION,
            case_id=case_id,
            client_id=client_id,
            agent_id=agent_id,
            actor_id=agent_id,
            actor_role="system",
            payload={"task_type": task_type, "status": status, "duration_ms": duration_ms},
            db=db,
        )

    async def log_document_status_changed(
        self,
        document_id: UUID,
        case_id: UUID,
        old_status: str,
        new_status: str,
        category: str | None,
        actor_id: str | None = None,
        actor_role: str | None = None,
        db=None,
    ) -> EventLog:
        return await self.log(
            event_type=AuditEventType.DOCUMENT_STATUS_CHANGED,
            event_category=AuditEventCategory.DOCUMENT,
            case_id=case_id,
            entity_type="document",
            entity_id=document_id,
            actor_id=actor_id or "system",
            actor_role=actor_role or "system",
            payload={
                "document_id": str(document_id),
                "old_status": old_status,
                "new_status": new_status,
                "category": category,
            },
            db=db,
        )

    async def log_review_created(
        self,
        review_id: UUID,
        case_id: UUID,
        client_id: UUID,
        escalation_reason: str,
        risk_band: str | None,
        composite_score: float | None,
        db=None,
    ) -> EventLog:
        return await self.log(
            event_type=AuditEventType.REVIEW_CREATED,
            event_category=AuditEventCategory.COMPLIANCE,
            case_id=case_id,
            client_id=client_id,
            agent_id="kyc_compliance",
            entity_type="human_review",
            entity_id=review_id,
            actor_id="kyc_compliance",
            actor_role="system",
            payload={
                "review_id": str(review_id),
                "escalation_reason": escalation_reason,
                "risk_band": risk_band,
                "composite_score": composite_score,
            },
            is_compliance_event=True,
            db=db,
        )

    async def log_review_decided(
        self,
        review_id: UUID,
        case_id: UUID,
        decision: str,
        reviewer_role: str | None,
        notes: str | None,
        db=None,
    ) -> EventLog:
        decision_type_map = {
            "APPROVED": AuditEventType.REVIEW_APPROVED,
            "REJECTED": AuditEventType.REVIEW_REJECTED,
            "MORE_INFO_REQUESTED": AuditEventType.REVIEW_MORE_INFO_REQUESTED,
        }
        event_type = decision_type_map.get(decision, AuditEventType.REVIEW_DECIDED)
        return await self.log(
            event_type=event_type,
            event_category=AuditEventCategory.COMPLIANCE,
            case_id=case_id,
            entity_type="human_review",
            entity_id=review_id,
            actor_role=reviewer_role or "advisor",
            payload={
                "review_id": str(review_id),
                "decision": decision,
                "notes": notes,
            },
            is_compliance_event=True,
            db=db,
        )

    async def log_mcp_tool_called(
        self,
        connector: str,
        tool: str,
        agent_id: str,
        case_id: UUID | None,
        status: str,
        latency_ms: int | None,
        is_simulated: bool,
        db=None,
    ) -> EventLog:
        return await self.log(
            event_type=AuditEventType.MCP_TOOL_CALLED,
            event_category=AuditEventCategory.AGENT_ACTION,
            case_id=case_id,
            agent_id=agent_id,
            actor_id=agent_id,
            actor_role="system",
            payload={
                "connector": connector,
                "tool": tool,
                "status": status,
                "latency_ms": latency_ms,
                "is_simulated": is_simulated,
            },
            db=db,
        )

    async def log_compliance_decision(
        self,
        decision: str,
        decision_source: str,
        case_id: UUID | None,
        client_id: UUID | None,
        entity_type: str | None,
        entity_id: UUID | None,
        payload: dict[str, Any] | None = None,
        db=None,
    ) -> EventLog:
        return await self.log(
            event_type=AuditEventType.COMPLIANCE_DECISION,
            event_category=AuditEventCategory.COMPLIANCE,
            case_id=case_id,
            client_id=client_id,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=decision_source,
            actor_role="system",
            payload={"decision": decision, "decision_source": decision_source, **(payload or {})},
            is_compliance_event=True,
            db=db,
        )


# Module-level singleton
audit_log_service = AuditLogService()
