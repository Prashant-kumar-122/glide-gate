from __future__ import annotations

"""ComplianceDecisionLogger — typed logging for all compliance decision points.

Logs COMPLIANCE_DECISION audit events (BRD FR-14, Section 10.2, Hackathon Criterion #11) for:
- Automated KYC decisions (PASSED / ESCALATED / FAILED) from the KYC compliance agent
- Human reviewer decisions (APPROVED / REJECTED / MORE_INFO_REQUESTED)

Every decision that affects case flow MUST produce a COMPLIANCE_DECISION event to satisfy
the 100% decision audit trail requirement.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from loguru import logger

from app.services.audit.audit_log_service import audit_log_service


class ComplianceDecisionLogger:
    """Typed wrapper around AuditLogService for compliance-critical decisions."""

    # ── Automated KYC decisions ───────────────────────────────────────────────

    async def log_automated_kyc_decision(
        self,
        *,
        case_id: UUID,
        client_id: UUID,
        kyc_status: str,
        risk_band: str,
        composite_score: float,
        identity_score: float,
        aml_score: float,
        profile_score: float,
        escalation_reasons: list[str] | None = None,
        required_documents: list[str] | None = None,
        evidence_packet_id: str | None = None,
        db: Any = None,
    ) -> None:
        """Log an automated KYC engine decision.

        Called by KYCComplianceAgent for every run outcome — whether the case
        passes, escalates, or is rejected.  The db param is optional; when omitted
        the service acquires its own session and commits immediately.
        """
        decision_map = {
            "PASSED": "KYC_APPROVED_AUTOMATED",
            "ESCALATED": "KYC_ESCALATED_FOR_REVIEW",
            "FAILED": "KYC_REJECTED_AUTOMATED",
        }
        decision = decision_map.get(kyc_status, f"KYC_{kyc_status}_AUTOMATED")

        try:
            await audit_log_service.log_compliance_decision(
                decision=decision,
                decision_source="kyc_compliance_agent",
                case_id=case_id,
                client_id=client_id,
                entity_type="kyc_check",
                entity_id=None,
                payload={
                    "kyc_status": kyc_status,
                    "risk_band": risk_band,
                    "composite_score": composite_score,
                    "identity_score": identity_score,
                    "aml_score": aml_score,
                    "profile_score": profile_score,
                    "escalation_reasons": escalation_reasons or [],
                    "required_documents": required_documents or [],
                    "evidence_packet_id": evidence_packet_id,
                    "decided_at": datetime.now(timezone.utc).isoformat(),
                    "decision_type": "AUTOMATED",
                },
                db=db,
            )
            logger.info(
                f"[ComplianceDecisionLogger] Automated KYC decision logged: "
                f"{decision} case={case_id} risk_band={risk_band} "
                f"composite={composite_score:.2f}"
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"[ComplianceDecisionLogger] Failed to log automated KYC decision "
                f"for case={case_id}: {exc}"
            )

    # ── Human reviewer decisions ──────────────────────────────────────────────

    async def log_human_review_decision(
        self,
        *,
        review_id: UUID,
        case_id: UUID,
        client_id: UUID | None,
        decision: str,
        reviewer_role: str | None,
        decision_notes: str | None,
        risk_band: str | None = None,
        composite_score: float | None = None,
        db: Any = None,
    ) -> None:
        """Log a human reviewer compliance decision.

        Called by HumanReviewService.decide() for every reviewer action.
        Produces a COMPLIANCE_DECISION event in addition to the specific
        REVIEW_APPROVED / REVIEW_REJECTED / REVIEW_MORE_INFO_REQUESTED events
        already emitted by audit_log_service.log_review_decided().
        """
        decision_map = {
            "APPROVED": "REVIEW_APPROVED_BY_HUMAN",
            "REJECTED": "REVIEW_REJECTED_BY_HUMAN",
            "MORE_INFO_REQUESTED": "REVIEW_MORE_INFO_REQUESTED_BY_HUMAN",
        }
        compliance_decision = decision_map.get(decision, f"REVIEW_{decision}_BY_HUMAN")

        try:
            await audit_log_service.log_compliance_decision(
                decision=compliance_decision,
                decision_source=reviewer_role or "advisor",
                case_id=case_id,
                client_id=client_id,
                entity_type="human_review",
                entity_id=review_id,
                payload={
                    "review_id": str(review_id),
                    "decision": decision,
                    "reviewer_role": reviewer_role,
                    "decision_notes": decision_notes,
                    "risk_band": risk_band,
                    "composite_score": composite_score,
                    "decided_at": datetime.now(timezone.utc).isoformat(),
                    "decision_type": "HUMAN",
                },
                db=db,
            )
            logger.info(
                f"[ComplianceDecisionLogger] Human review decision logged: "
                f"{compliance_decision} review={review_id} by {reviewer_role}"
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"[ComplianceDecisionLogger] Failed to log human review decision "
                f"for review={review_id}: {exc}"
            )


# Module-level singleton
compliance_decision_logger = ComplianceDecisionLogger()
