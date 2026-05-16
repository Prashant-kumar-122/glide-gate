from __future__ import annotations

"""JourneyResumptionService — resume a paused onboarding workflow (BRD FR-12).

Entry point: resume_case(case_id)
  1. Load OnboardingCase + CaseProduct steps from DB.
  2. Restore OnboardingState into the ContextStoreService (evict stale cache first).
  3. Determine the current FSM stage and re-publish the appropriate agent task(s).
  4. Log a JOURNEY_RESUMED audit event.
  5. Emit CASE_STAGE_CHANGED WebSocket event.

ProductOnboardingAgent resumption: for each CaseProduct that is PENDING or
IN_PROGRESS, the payload includes `resume_from_step` (the step_index of the
first non-complete step from case_product_steps) so the agent can skip already-
completed steps rather than replaying them from the beginning.
"""

from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.base.a2a_types import AgentID, OnboardingStage, TaskPacket, TaskType
from app.database import AsyncSessionLocal
from app.models.cases import CaseProduct, CaseProductStep, OnboardingCase
from app.services.audit.audit_event_types import AuditEventCategory, AuditEventType
from app.services.audit.audit_log_service import audit_log_service
from app.services.context_store.context_store_service import context_store
from app.websocket.socket_emitter import socket_emitter


class JourneyResumptionService:
    """Resume a paused onboarding journey from its last known DB state."""

    async def resume_case(self, case_id: UUID) -> None:
        """Load, restore context, log, emit, and re-spawn agents for a paused case."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(OnboardingCase)
                .options(
                    selectinload(OnboardingCase.case_products).selectinload(CaseProduct.steps),
                )
                .where(OnboardingCase.id == case_id)
            )
            case = result.scalar_one_or_none()

        if case is None:
            logger.error(f"JourneyResumptionService: case {case_id} not found")
            return

        client_id = case.client_id
        selected_products: list[str] = case.selected_products or []

        try:
            stage = OnboardingStage(case.current_stage)
        except ValueError:
            logger.warning(
                f"JourneyResumptionService: unknown stage {case.current_stage!r} "
                f"for case {case_id}, defaulting to INTAKE"
            )
            stage = OnboardingStage.INTAKE

        # 1. Restore context into ContextStoreService
        await self._restore_context(case_id, client_id, stage, selected_products, case)

        # 2. Log JOURNEY_RESUMED audit event (fire-and-forget)
        await audit_log_service.log(
            event_type=AuditEventType.JOURNEY_RESUMED,
            event_category=AuditEventCategory.AGENT_ACTION,
            case_id=case_id,
            client_id=client_id,
            actor_id="system",
            actor_role="system",
            payload={
                "case_id": str(case_id),
                "stage": stage,
                "selected_products": selected_products,
            },
        )

        # 3. Emit WebSocket notification so connected UIs update immediately
        await socket_emitter.case_stage_changed(
            case_id,
            {
                "case_id": str(case_id),
                "stage": stage,
                "event": "JOURNEY_RESUMED",
            },
        )

        # 4. Re-spawn agents for the current stage
        await self._respawn_agents(
            case_id=case_id,
            client_id=client_id,
            stage=stage,
            selected_products=selected_products,
            case_products=case.case_products,
        )

        logger.info(f"JourneyResumptionService: case {case_id} resumed at stage={stage}")

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _restore_context(
        self,
        case_id: UUID,
        client_id: UUID,
        stage: OnboardingStage,
        selected_products: list[str],
        case: OnboardingCase,
    ) -> None:
        """Restore or re-initialise the ContextStoreService entry for this case."""
        shared_ctx = case.shared_context or {}
        if shared_ctx:
            try:
                # Evict stale in-memory cache so next get() forces a fresh DB read
                context_store.evict(case_id)
                await context_store.get(case_id)
                logger.debug(f"JourneyResumptionService: context restored for case {case_id}")
                return
            except Exception as exc:
                logger.warning(
                    f"JourneyResumptionService: could not restore context for case {case_id} "
                    f"— re-initialising. Reason: {exc}"
                )

        # Fallback: build a fresh state from DB columns
        try:
            existing = await context_store.get(case_id)
            # Update stage to match DB
            await context_store.update(case_id, {"stage": stage})
        except KeyError:
            await context_store.initialise(case_id, client_id, selected_products)
            await context_store.update(case_id, {"stage": stage})

    async def _respawn_agents(
        self,
        case_id: UUID,
        client_id: UUID,
        stage: OnboardingStage,
        selected_products: list[str],
        case_products: list[CaseProduct],
    ) -> None:
        """Publish the appropriate task packet(s) based on the current stage."""
        # Late import avoids a circular dependency at module load time
        from app.services.orchestration.agent_orchestration_service import orchestration_service

        if stage == OnboardingStage.INTAKE:
            await orchestration_service.publish_task(
                TaskPacket(
                    from_agent=AgentID.ORCHESTRATOR,
                    to_agent=AgentID.CUSTOMER_SERVICE,
                    task_type=TaskType.COLLECT_CLIENT_DATA,
                    case_id=case_id,
                    client_id=client_id,
                    priority="NORMAL",
                    payload={"selected_products": selected_products},
                )
            )
            logger.debug(f"JourneyResumptionService: re-spawned CustomerServiceAgent for case {case_id}")

        elif stage == OnboardingStage.KYC:
            await orchestration_service.publish_task(
                TaskPacket(
                    from_agent=AgentID.ORCHESTRATOR,
                    to_agent=AgentID.KYC_COMPLIANCE,
                    task_type=TaskType.RUN_KYC_CHECK,
                    case_id=case_id,
                    client_id=client_id,
                    priority="HIGH",
                    payload={"selected_products": selected_products},
                )
            )
            logger.debug(f"JourneyResumptionService: re-spawned KYCComplianceAgent for case {case_id}")

        elif stage == OnboardingStage.PARALLEL_PRODUCTS:
            await self._resume_product_onboarding(
                case_id, client_id, selected_products, case_products
            )

        elif stage == OnboardingStage.REVIEW:
            await orchestration_service.publish_task(
                TaskPacket(
                    from_agent=AgentID.ORCHESTRATOR,
                    to_agent=AgentID.COLLABORATION,
                    task_type=TaskType.CREATE_COLLABORATION_ROOM,
                    case_id=case_id,
                    client_id=client_id,
                    priority="NORMAL",
                    payload={"selected_products": selected_products},
                )
            )
            logger.debug(f"JourneyResumptionService: re-spawned CollaborationAgent for case {case_id}")

        elif stage == OnboardingStage.ESCALATED:
            # Human review is still pending — socket event is sufficient.
            logger.info(
                f"JourneyResumptionService: case {case_id} is ESCALATED — "
                "awaiting human review, no agents re-spawned"
            )

        elif stage == OnboardingStage.COMPLETE:
            logger.info(
                f"JourneyResumptionService: case {case_id} is already COMPLETE — nothing to resume"
            )

    async def _resume_product_onboarding(
        self,
        case_id: UUID,
        client_id: UUID,
        selected_products: list[str],
        case_products: list[CaseProduct],
    ) -> None:
        """Re-spawn ProductOnboardingAgent for each incomplete product track."""
        from app.services.orchestration.agent_orchestration_service import orchestration_service

        resumable = [cp for cp in case_products if cp.status in ("PENDING", "IN_PROGRESS")]

        if not resumable:
            # All products done — advance to REVIEW stage
            logger.info(
                f"JourneyResumptionService: all products complete for case {case_id}, "
                "advancing to REVIEW"
            )
            await orchestration_service.publish_task(
                TaskPacket(
                    from_agent=AgentID.ORCHESTRATOR,
                    to_agent=AgentID.ORCHESTRATOR,
                    task_type=TaskType.ADVANCE_STAGE,
                    case_id=case_id,
                    client_id=client_id,
                    priority="NORMAL",
                    payload={
                        "to_stage": OnboardingStage.REVIEW,
                        "selected_products": selected_products,
                    },
                )
            )
            return

        for cp in resumable:
            resume_step = self._find_resume_step(cp.steps)
            await orchestration_service.publish_task(
                TaskPacket(
                    from_agent=AgentID.ORCHESTRATOR,
                    to_agent=AgentID.PRODUCT_ONBOARDING,
                    task_type=TaskType.ONBOARD_PRODUCT,
                    case_id=case_id,
                    client_id=client_id,
                    priority="NORMAL",
                    payload={
                        "product_code": cp.product_code,
                        "selected_products": selected_products,
                        "resume_from_step": resume_step,
                        "case_product_id": str(cp.id),
                    },
                )
            )
            logger.info(
                f"JourneyResumptionService: re-spawned ProductOnboardingAgent for "
                f"case={case_id} product={cp.product_code} resume_from_step={resume_step}"
            )

    @staticmethod
    def _find_resume_step(steps: list[CaseProductStep]) -> int:
        """Return the step_index of the first non-COMPLETE/SKIPPED step.

        Returns 0 when there are no steps (fresh start),
        or len(steps) when all steps are already complete.
        """
        if not steps:
            return 0
        incomplete = [s for s in steps if s.status not in ("COMPLETE", "SKIPPED")]
        if not incomplete:
            return len(steps)
        return min(s.step_index for s in incomplete)


# Module-level singleton
journey_resumption_service = JourneyResumptionService()
