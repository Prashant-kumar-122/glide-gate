from __future__ import annotations

"""Human-in-the-Loop Review Service (BRD FR-13, Hackathon Criteria #5, #11).

Responsibilities:
- Create KYCCheck + HumanReview DB records when the orchestrator escalates a case.
- Emit ESCALATION_TRIGGERED socket event with evidence packet.
- Update OnboardingState.human_review_id so the case can resume.
- Handle reviewer decisions (APPROVED / REJECTED / MORE_INFO_REQUESTED).
- Emit REVIEW_DECIDED socket event and resume the workflow on approval.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.kyc_reviews import HumanReview, KYCCheck
from app.models.cases import OnboardingCase
from app.services.audit.audit_log_service import audit_log_service
from app.services.compliance.compliance_decision_logger import compliance_decision_logger
from app.services.compliance.evidence_packet_assembler import evidence_packet_assembler
from app.services.context_store.context_store_service import context_store
from app.websocket.socket_emitter import socket_emitter


class HumanReviewService:
    """Manages the full lifecycle of an escalated KYC human review."""

    # ── Create review ─────────────────────────────────────────────────────────

    async def create_review(
        self,
        case_id: UUID,
        client_id: UUID,
        escalation_reason: str,
        kyc_payload: dict[str, Any],
        db: AsyncSession,
    ) -> HumanReview:
        """
        Persist KYCCheck + HumanReview records, update shared context, and
        emit ESCALATION_TRIGGERED.  Called from the orchestrator on ESCALATE.
        """
        # 1. Persist KYCCheck
        kyc_check = KYCCheck(
            id=uuid4(),
            case_id=case_id,
            client_id=client_id,
            identity_score=kyc_payload.get("identity_score"),
            aml_score=kyc_payload.get("aml_score"),
            profile_score=kyc_payload.get("profile_score"),
            composite_score=kyc_payload.get("composite_score"),
            risk_band=kyc_payload.get("risk_band"),
            identity_verification_result=kyc_payload.get("verification_result", {}),
            aml_check_result={"aml_risk_level": kyc_payload.get("aml_risk_level", "UNKNOWN")},
            sanctions_check_result={"sanctions_match": kyc_payload.get("sanctions_match", False)},
            checkpoint_rules_applied=kyc_payload.get("checkpoint_rules_applied", []),
            status="ESCALATED",
        )
        db.add(kyc_check)
        await db.flush()  # get kyc_check.id

        # 2. Assemble evidence packet from DB + payload
        evidence_packet = await evidence_packet_assembler.assemble(
            case_id=case_id,
            client_id=client_id,
            kyc_result=kyc_payload,
            db=db,
        )

        # 3. Persist HumanReview
        review = HumanReview(
            id=uuid4(),
            case_id=case_id,
            kyc_check_id=kyc_check.id,
            status="PENDING",
            evidence_packet=evidence_packet,
            escalation_reason=escalation_reason,
            assigned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(review)
        await db.flush()

        # 4. Stamp case with review reference
        result = await db.execute(
            select(OnboardingCase).where(OnboardingCase.id == case_id)
        )
        case = result.scalar_one_or_none()
        if case is not None:
            ctx = case.shared_context or {}
            ctx["human_review_id"] = str(review.id)
            ctx["current_stage"] = "ESCALATED"
            case.shared_context = ctx
            case.current_stage = "ESCALATED"
            case.status = "ESCALATED"

        await db.commit()

        # 5. Update shared in-memory context
        try:
            state = await context_store.get(case_id)
            if state is not None:
                await context_store.update(
                    case_id,
                    {"human_review_id": review.id, "escalation_reason": escalation_reason},
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[HumanReviewService] context update failed: {exc}")

        # 6. Audit log
        await audit_log_service.log_review_created(
            review_id=review.id,
            case_id=case_id,
            client_id=client_id,
            escalation_reason=escalation_reason,
            risk_band=kyc_payload.get("risk_band"),
            composite_score=kyc_payload.get("composite_score"),
            db=db,
        )

        # 7. Emit socket event
        await socket_emitter.escalation_triggered(case_id, {
            "review_id": str(review.id),
            "case_id": str(case_id),
            "reason": escalation_reason,
            "risk_band": kyc_payload.get("risk_band"),
            "composite_score": kyc_payload.get("composite_score"),
        })

        logger.info(
            f"[HumanReviewService] Review created review_id={review.id} case={case_id} "
            f"reason={escalation_reason!r}"
        )
        return review

    # ── Handle decision ───────────────────────────────────────────────────────

    async def decide(
        self,
        review_id: UUID,
        decision: str,
        decision_notes: str | None,
        reviewer_role: str | None,
        db: AsyncSession,
    ) -> HumanReview:
        """
        Record the reviewer decision and resume or terminate the workflow.

        APPROVED   → resumes workflow at PARALLEL_PRODUCTS stage
        REJECTED   → marks case REJECTED, sends notification
        MORE_INFO_REQUESTED → stays ESCALATED, sends notification to client
        """
        result = await db.execute(
            select(HumanReview).where(HumanReview.id == review_id)
        )
        review = result.scalar_one_or_none()
        if review is None:
            raise ValueError(f"HumanReview {review_id} not found")
        if review.status != "PENDING":
            raise ValueError(
                f"Review {review_id} already decided (status={review.status})"
            )

        review.status = decision
        review.decision = decision
        review.decision_notes = decision_notes
        review.reviewer_role = reviewer_role
        review.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        # Audit log — specific review event
        await audit_log_service.log_review_decided(
            review_id=review_id,
            case_id=review.case_id,
            decision=decision,
            reviewer_role=reviewer_role,
            notes=decision_notes,
        )

        # Compliance decision log — COMPLIANCE_DECISION event for 100% audit coverage
        kyc_result = (review.evidence_packet or {}).get("kyc_result", {})
        await compliance_decision_logger.log_human_review_decision(
            review_id=review_id,
            case_id=review.case_id,
            client_id=None,
            decision=decision,
            reviewer_role=reviewer_role,
            decision_notes=decision_notes,
            risk_band=kyc_result.get("risk_band"),
            composite_score=kyc_result.get("composite_score"),
        )

        # Emit socket event
        await socket_emitter.review_decided(review.case_id, {
            "review_id": str(review_id),
            "case_id": str(review.case_id),
            "decision": decision,
            "decided_at": review.decided_at.isoformat(),
        })

        # Resume / terminate workflow in background (needs own session)
        import asyncio
        asyncio.create_task(
            self._post_decision_workflow(
                review_id=review_id,
                case_id=review.case_id,
                decision=decision,
            )
        )

        logger.info(
            f"[HumanReviewService] Decision recorded review_id={review_id} "
            f"decision={decision}"
        )
        return review

    # ── Post-decision workflow ─────────────────────────────────────────────────

    async def _post_decision_workflow(
        self, review_id: UUID, case_id: UUID, decision: str
    ) -> None:
        """Background task that resumes or terminates the workflow after a decision."""
        async with AsyncSessionLocal() as db:
            try:
                # Load shared context to get selected_products + client_id
                result = await db.execute(
                    select(OnboardingCase).where(OnboardingCase.id == case_id)
                )
                case = result.scalar_one_or_none()
                if case is None:
                    logger.warning(
                        f"[HumanReviewService] case {case_id} not found for post-decision"
                    )
                    return

                selected_products: list[str] = (
                    case.selected_products or []
                )
                client_id: UUID = case.client_id

                if decision == "APPROVED":
                    await self._resume_after_approval(
                        case_id=case_id,
                        client_id=client_id,
                        selected_products=selected_products,
                        case=case,
                        db=db,
                    )
                elif decision == "REJECTED":
                    await self._terminate_after_rejection(case_id, case, db)
                elif decision == "MORE_INFO_REQUESTED":
                    await self._request_more_info(case_id, case, db)

            except Exception as exc:  # noqa: BLE001
                logger.error(
                    f"[HumanReviewService] post_decision_workflow error case={case_id}: {exc}"
                )

    async def _resume_after_approval(
        self,
        case_id: UUID,
        client_id: UUID,
        selected_products: list[str],
        case: OnboardingCase,
        db: AsyncSession,
    ) -> None:
        from app.services.orchestration.agent_orchestration_service import (
            orchestration_service,
        )

        case.current_stage = "PARALLEL_PRODUCTS"
        case.status = "IN_PROGRESS"
        ctx = case.shared_context or {}
        ctx["current_stage"] = "PARALLEL_PRODUCTS"
        case.shared_context = ctx
        await db.commit()

        # Advance in shared context
        try:
            state = await context_store.get(case_id)
            if state is not None:
                await context_store.update(case_id, {"stage": "PARALLEL_PRODUCTS"})
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[HumanReviewService] context stage update failed: {exc}")

        # Kick off product onboarding via orchestration service
        await orchestration_service.start_product_onboarding(
            case_id=case_id,
            client_id=client_id,
            selected_products=selected_products,
        )

        await socket_emitter.case_stage_changed(case_id, {
            "case_id": str(case_id),
            "stage": "PARALLEL_PRODUCTS",
            "triggered_by": "human_review_approved",
        })
        logger.info(f"[HumanReviewService] Workflow resumed case={case_id}")

    async def _terminate_after_rejection(
        self, case_id: UUID, case: OnboardingCase, db: AsyncSession
    ) -> None:
        case.current_stage = "COMPLETE"
        case.status = "REJECTED"
        ctx = case.shared_context or {}
        ctx["current_stage"] = "COMPLETE"
        case.shared_context = ctx
        await db.commit()

        await socket_emitter.case_stage_changed(case_id, {
            "case_id": str(case_id),
            "stage": "REJECTED",
            "triggered_by": "human_review_rejected",
        })
        logger.info(f"[HumanReviewService] Case rejected case={case_id}")

    async def _request_more_info(
        self, case_id: UUID, case: OnboardingCase, db: AsyncSession
    ) -> None:
        # Stays ESCALATED — notify client
        await socket_emitter.case_stage_changed(case_id, {
            "case_id": str(case_id),
            "stage": "ESCALATED",
            "triggered_by": "more_info_requested",
        })
        logger.info(f"[HumanReviewService] More info requested case={case_id}")


# Module-level singleton
human_review_service = HumanReviewService()
