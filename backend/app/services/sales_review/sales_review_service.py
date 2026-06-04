from __future__ import annotations

"""Sales Manager Review Service.

Responsibilities:
- Create SalesManagerReview records when a case enters SALES_REVIEW stage.
- Generate an AI risk summary using the LLM provider.
- Handle SM decisions: APPROVED → KYC, REJECTED/MORE_INFO → REVIEW.
- Emit WebSocket events for real-time frontend updates.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.sales_reviews import SalesManagerReview
from app.models.cases import OnboardingCase
from app.services.audit.audit_log_service import audit_log_service
from app.websocket.socket_emitter import socket_emitter


class SalesReviewService:
    """Manages the full lifecycle of a Sales Manager review."""

    # ── Create review ─────────────────────────────────────────────────────────

    async def create_review(
        self,
        case_id: UUID,
        client_id: UUID,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> SalesManagerReview:
        """Persist SalesManagerReview, generate AI summary, emit socket event."""

        # Build case snapshot for the dashboard
        case_snapshot = await self._build_case_snapshot(case_id, payload, db)

        # Generate AI risk summary
        ai_summary, risk_score = await self._generate_risk_summary(case_snapshot)

        review = SalesManagerReview(
            id=uuid4(),
            case_id=case_id,
            status="PENDING",
            ai_risk_summary=ai_summary,
            risk_score=risk_score,
            case_snapshot=case_snapshot,
            assigned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(review)

        # Update case stage in DB
        result = await db.execute(
            select(OnboardingCase).where(OnboardingCase.id == case_id)
        )
        case = result.scalar_one_or_none()
        if case is not None:
            case.current_stage = "SALES_REVIEW"
            case.status = "SALES_REVIEW"
            ctx = case.shared_context or {}
            ctx["sales_review_id"] = str(review.id)
            ctx["current_stage"] = "SALES_REVIEW"
            case.shared_context = ctx

        await db.commit()
        await db.refresh(review)

        # Emit socket event so the SM's browser updates in real time
        await socket_emitter.sales_review_triggered(case_id, {
            "review_id": str(review.id),
            "case_id": str(case_id),
            "risk_score": risk_score,
            "ai_risk_summary": ai_summary,
            "stage": "SALES_REVIEW",
        })

        logger.info(
            f"[SalesReviewService] Review created review_id={review.id} "
            f"case={case_id} risk_score={risk_score}"
        )
        return review

    # ── Handle decision ───────────────────────────────────────────────────────

    async def decide(
        self,
        review_id: UUID,
        decision: str,
        decision_notes: str | None,
        reviewer_id: UUID | None,
        reviewer_role: str | None,
        db: AsyncSession,
    ) -> SalesManagerReview:
        """Record the SM decision and route the workflow accordingly.

        APPROVED          → advance case to KYC
        REJECTED          → move case to REVIEW (pending_info)
        MORE_INFO_REQUESTED → move case to REVIEW (pending_info)
        """
        result = await db.execute(
            select(SalesManagerReview).where(SalesManagerReview.id == review_id)
        )
        review = result.scalar_one_or_none()
        if review is None:
            raise ValueError(f"SalesManagerReview {review_id} not found")
        if review.status != "PENDING":
            raise ValueError(
                f"Review {review_id} already decided (status={review.status})"
            )

        review.status = decision
        review.decision = decision
        review.decision_notes = decision_notes
        review.reviewer_id = reviewer_id
        review.reviewer_role = reviewer_role
        review.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        # Emit decision event
        await socket_emitter.sales_review_decided(review.case_id, {
            "review_id": str(review_id),
            "case_id": str(review.case_id),
            "decision": decision,
            "decided_at": review.decided_at.isoformat(),
        })

        # Audit log
        await audit_log_service.log(
            event_type="SALES_REVIEW_DECIDED",
            event_category="compliance",
            case_id=review.case_id,
            entity_type="sales_manager_review",
            entity_id=review_id,
            actor_role=reviewer_role or "sales_manager",
            payload={
                "review_id": str(review_id),
                "decision": decision,
                "notes": decision_notes,
            },
            is_compliance_event=True,
        )

        # Resume or hold the workflow in a background task
        import asyncio
        asyncio.create_task(
            self._post_decision_workflow(
                review_id=review_id,
                case_id=review.case_id,
                decision=decision,
            )
        )

        logger.info(
            f"[SalesReviewService] Decision recorded review_id={review_id} "
            f"decision={decision}"
        )
        return review

    # ── Post-decision workflow ────────────────────────────────────────────────

    async def _post_decision_workflow(
        self, review_id: UUID, case_id: UUID, decision: str
    ) -> None:
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(OnboardingCase).where(OnboardingCase.id == case_id)
                )
                case = result.scalar_one_or_none()
                if case is None:
                    return

                if decision == "APPROVED":
                    await self._advance_to_kyc(case_id, case, db)
                else:
                    # REJECTED or MORE_INFO_REQUESTED → back to REVIEW
                    await self._move_to_review(case_id, case, db, decision)

            except Exception as exc:  # noqa: BLE001
                logger.error(
                    f"[SalesReviewService] post_decision_workflow error case={case_id}: {exc}"
                )

    async def _advance_to_kyc(
        self, case_id: UUID, case: OnboardingCase, db: AsyncSession
    ) -> None:
        from app.agents.base.a2a_types import AgentID, OnboardingStage, TaskPacket, TaskType
        from app.services.orchestration.agent_orchestration_service import orchestration_service

        case.current_stage = "KYC"
        case.status = "KYC"
        ctx = case.shared_context or {}
        ctx["current_stage"] = "KYC"
        case.shared_context = ctx
        await db.commit()

        # Publish KYC task directly
        await orchestration_service.publish_task(
            TaskPacket(
                from_agent=AgentID.SALES_MANAGER,
                to_agent=AgentID.KYC_COMPLIANCE,
                task_type=TaskType.RUN_KYC_CHECK,
                case_id=case_id,
                client_id=case.client_id,
                priority="HIGH",
                payload={
                    "selected_products": case.selected_products or [],
                    "sales_review_approved": True,
                },
            )
        )

        await socket_emitter.case_stage_changed(case_id, {
            "case_id": str(case_id),
            "stage": OnboardingStage.KYC,
            "triggered_by": "sales_review_approved",
        })
        logger.info(f"[SalesReviewService] Case advanced to KYC case={case_id}")

    async def _move_to_review(
        self,
        case_id: UUID,
        case: OnboardingCase,
        db: AsyncSession,
        decision: str,
    ) -> None:
        from app.agents.base.a2a_types import OnboardingStage

        case.current_stage = "REVIEW"
        case.status = "REVIEW"
        ctx = case.shared_context or {}
        ctx["current_stage"] = "REVIEW"
        ctx["sales_review_decision"] = decision
        case.shared_context = ctx
        await db.commit()

        await socket_emitter.case_stage_changed(case_id, {
            "case_id": str(case_id),
            "stage": OnboardingStage.REVIEW,
            "triggered_by": f"sales_review_{decision.lower()}",
        })
        logger.info(
            f"[SalesReviewService] Case moved to REVIEW case={case_id} reason={decision}"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _build_case_snapshot(
        self,
        case_id: UUID,
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Build structured snapshot shown on the SM review dashboard."""
        from sqlalchemy.orm import selectinload
        from app.models.documents import Document

        result = await db.execute(
            select(OnboardingCase)
            .options(selectinload(OnboardingCase.case_products))
            .where(OnboardingCase.id == case_id)
        )
        case = result.scalar_one_or_none()

        doc_result = await db.execute(
            select(Document).where(Document.case_id == case_id)
        )
        docs = doc_result.scalars().all()

        products = []
        if case and case.case_products:
            for cp in case.case_products:
                products.append({
                    "product_code": cp.product_code,
                    "status": cp.status,
                })

        return {
            "case_id": str(case_id),
            "selected_products": payload.get("selected_products", []),
            "client_name": payload.get("client_name", ""),
            "case_name": payload.get("case_name", ""),
            "client_data": payload.get("client_data", {}),
            "product_tracks": products,
            "documents": [
                {
                    "id": str(d.id),
                    "filename": d.original_filename or d.document_type,
                    "document_type": d.document_type,
                    "status": d.status,
                    "uploaded_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in docs
            ],
            "total_documents": len(docs),
            "approved_documents": sum(1 for d in docs if d.status == "approved"),
        }

    async def _generate_risk_summary(
        self, snapshot: dict[str, Any]
    ) -> tuple[str, float]:
        """Generate AI risk summary using LLM. Falls back to a rule-based summary."""
        products = snapshot.get("selected_products", [])
        client_name = snapshot.get("client_name", "Unknown Client")
        doc_count = snapshot.get("total_documents", 0)
        approved_docs = snapshot.get("approved_documents", 0)
        client_data = snapshot.get("client_data", {})
        doc_ratio = approved_docs / max(doc_count, 1)
        risk_score = round((1 - doc_ratio) * 50 + 25, 1)

        try:
            from app.services.llm.llm_provider_factory import llm_provider_factory
            from app.services.llm.llm_provider import LLMMessage, LLMRequest

            provider = llm_provider_factory.create()
            if not provider.is_available():
                raise RuntimeError("No LLM provider available")

            prompt = (
                f"You are a Risk Analyst preparing a briefing for the Sales Manager.\n\n"
                f"Client: {client_name}\n"
                f"Products: {', '.join(products)}\n"
                f"Documents: {approved_docs}/{doc_count} approved\n"
                f"Client data: {client_data}\n\n"
                f"Provide a concise risk assessment summary (3-4 sentences) covering:\n"
                f"1. Product suitability for this client profile\n"
                f"2. Document completeness\n"
                f"3. Key risk factors or concerns\n"
                f"4. Overall recommendation\n\n"
                f"Be objective and professional."
            )

            request = LLMRequest(
                messages=[LLMMessage(role="user", content=prompt)],
                system_prompt=(
                    "You are a senior risk analyst at a wealth management firm. "
                    "Provide clear, concise risk assessments for institutional onboarding cases."
                ),
                max_tokens=400,
                temperature=0.2,
            )
            response = await provider.complete(request)
            summary = response.text.strip()
            return summary, risk_score

        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[SalesReviewService] LLM risk summary failed: {exc}")
            # Rule-based fallback
            summary = (
                f"Institutional onboarding case for {client_name} "
                f"with products: {', '.join(products)}. "
                f"Documents: {approved_docs}/{doc_count} approved ({int(doc_ratio * 100)}% complete). "
                f"Manual review recommended before proceeding to KYC."
            )
            return summary, risk_score


# Module-level singleton
sales_review_service = SalesReviewService()
