from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from app.agents.base.a2a_types import (
    AgentID,
    OnboardingStage,
    OnboardingState,
    ProductTrackState,
    TaskPacket,
    TaskResponse,
    TaskType,
)
from app.agents.base.base_agent import BaseAgent
from app.agents.orchestrator.workflow_state_machine import (
    InvalidTransitionError,
    WorkflowStateMachine,
)


async def _persist_case_stage(case_id: UUID, stage: str) -> None:
    """Write status + current_stage to the DB from a background task."""
    from sqlalchemy import update as sa_update
    from app.database import AsyncSessionLocal
    from app.models.cases import OnboardingCase

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_update(OnboardingCase)
            .where(OnboardingCase.id == case_id)
            .values(status=stage, current_stage=stage)
        )
        await db.commit()


class OrchestratorAgent(BaseAgent):
    """
    Central workflow controller.

    Owns one WorkflowStateMachine per case and routes TaskPackets to
    specialised agents as the FSM advances through stages.
    """

    agent_id = AgentID.ORCHESTRATOR

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._fsms: dict[UUID, WorkflowStateMachine] = {}
        self._states: dict[UUID, OnboardingState] = {}

    # ── FSM helpers ───────────────────────────────────────────────────────────

    def _get_or_create_fsm(
        self,
        case_id: UUID,
        initial: OnboardingStage = OnboardingStage.INTAKE,
    ) -> WorkflowStateMachine:
        if case_id not in self._fsms:
            fsm = WorkflowStateMachine(case_id, initial)
            fsm.on_transition(lambda stage: self._sync_state_stage(case_id, stage))
            self._fsms[case_id] = fsm
        return self._fsms[case_id]

    def _sync_state_stage(self, case_id: UUID, stage: OnboardingStage) -> None:
        if case_id in self._states:
            self._states[case_id].stage = stage
        self.logger.info(f"case={case_id} → {stage}")

    # ── Task dispatch ─────────────────────────────────────────────────────────

    async def process(self, task: TaskPacket) -> TaskResponse:
        handlers = {
            TaskType.START_ONBOARDING: self._handle_start,
            TaskType.RESUME_ONBOARDING: self._handle_resume,
            TaskType.ADVANCE_STAGE: self._handle_advance,
            TaskType.PRODUCT_TRACK_COMPLETE: self._handle_product_track_complete,
            TaskType.ESCALATE: self._handle_escalate,
            TaskType.HEALTH_CHECK: self._handle_health_check,
        }
        handler = handlers.get(task.task_type)
        if handler is None:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=[f"Unrecognised task_type: {task.task_type}"],
            )
        return await handler(task)

    # ── Handlers ──────────────────────────────────────────────────────────────

    async def _handle_start(self, task: TaskPacket) -> TaskResponse:
        case_id = task.case_id
        selected_products: list[str] = task.payload.get("selected_products", [])

        state = OnboardingState(
            case_id=case_id,
            client_id=task.client_id,
            selected_products=selected_products,
        )
        self._states[case_id] = state
        fsm = self._get_or_create_fsm(case_id)

        await self.send_task(
            TaskPacket(
                from_agent=self.agent_id,
                to_agent=AgentID.CUSTOMER_SERVICE,
                task_type=TaskType.COLLECT_CLIENT_DATA,
                case_id=case_id,
                client_id=task.client_id,
                priority="NORMAL",
                payload={"selected_products": selected_products},
            )
        )
        self.logger.info(f"Started onboarding case={case_id} products={selected_products}")
        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={"stage": fsm.stage, "case_id": str(case_id)},
        )

    async def _handle_resume(self, task: TaskPacket) -> TaskResponse:
        case_id = task.case_id
        raw_stage: str = task.payload.get("stage", OnboardingStage.INTAKE)
        try:
            persisted_stage = OnboardingStage(raw_stage)
        except ValueError:
            persisted_stage = OnboardingStage.INTAKE

        fsm = self._get_or_create_fsm(case_id)
        fsm.restore(persisted_stage)

        _resume_routing: dict[OnboardingStage, tuple[AgentID, TaskType]] = {
            OnboardingStage.INTAKE: (AgentID.CUSTOMER_SERVICE, TaskType.COLLECT_CLIENT_DATA),
            OnboardingStage.KYC: (AgentID.KYC_COMPLIANCE, TaskType.RUN_KYC_CHECK),
            OnboardingStage.PARALLEL_PRODUCTS: (AgentID.PRODUCT_ONBOARDING, TaskType.ONBOARD_PRODUCT),
        }
        routing = _resume_routing.get(persisted_stage)
        if routing:
            target_agent, task_type = routing
            await self.send_task(
                TaskPacket(
                    from_agent=self.agent_id,
                    to_agent=target_agent,
                    task_type=task_type,
                    case_id=case_id,
                    client_id=task.client_id,
                    priority="NORMAL",
                    payload=task.payload,
                )
            )
        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={"stage": fsm.stage, "resumed": True},
        )

    async def _handle_advance(self, task: TaskPacket) -> TaskResponse:
        case_id = task.case_id
        raw_stage: str = task.payload.get("to_stage", "")
        try:
            to_stage = OnboardingStage(raw_stage)
        except ValueError:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=[f"Unknown target stage: {raw_stage!r}"],
            )

        fsm = self._get_or_create_fsm(case_id)
        try:
            fsm.transition(to_stage)
        except InvalidTransitionError as exc:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=[str(exc)],
            )

        await self._route_to_stage(task, to_stage)
        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={"stage": to_stage},
        )

    async def _handle_product_track_complete(self, task: TaskPacket) -> TaskResponse:
        case_id = task.case_id
        product_code: str = task.payload.get("product_code", "")
        track_status: str = task.payload.get("track_status", "COMPLETE")

        state = self._states.get(case_id)
        if state is None:
            self.logger.warning(
                f"No in-memory state for case={case_id} on PRODUCT_TRACK_COMPLETE; ignoring"
            )
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="SUCCESS",
                result={"acknowledged": True},
            )

        # Cold-start: track may be absent if the orchestrator restarted mid-flow
        if product_code not in state.product_tracks:
            state.product_tracks[product_code] = ProductTrackState(
                product_code=product_code,
                stage=track_status,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
        else:
            state.product_tracks[product_code].stage = track_status
            state.product_tracks[product_code].completed_at = datetime.utcnow()

        terminal = {"COMPLETE", "UNSUITABLE", "FAILED"}
        problematic = {"UNSUITABLE", "FAILED"}
        expected = set(state.selected_products)
        settled = {
            code
            for code, track in state.product_tracks.items()
            if track.stage in terminal
        }

        self.logger.info(
            f"Product track settled: case={case_id} product={product_code} "
            f"status={track_status} settled={len(settled)}/{len(expected)}"
        )

        if expected and expected <= settled:
            has_issues = any(
                state.product_tracks[code].stage in problematic for code in expected
            )
            target_stage = OnboardingStage.REVIEW if has_issues else OnboardingStage.COMPLETE

            self.logger.info(
                f"All {len(expected)} product tracks settled for case={case_id}, "
                f"advancing to {target_stage} (has_issues={has_issues})"
            )
            fsm = self._get_or_create_fsm(case_id)
            try:
                fsm.transition(target_stage)
            except InvalidTransitionError as exc:
                self.logger.warning(f"FSM transition skipped for case={case_id}: {exc}")

            asyncio.create_task(_persist_case_stage(case_id, target_stage.value))

            if has_issues:
                await self.send_task(
                    TaskPacket(
                        from_agent=self.agent_id,
                        to_agent=AgentID.COLLABORATION,
                        task_type=TaskType.CREATE_COLLABORATION_ROOM,
                        case_id=case_id,
                        client_id=task.client_id,
                        priority="NORMAL",
                        payload={
                            "selected_products": state.selected_products,
                            "client_data": state.client_data,
                            "product_tracks": {
                                k: v.model_dump() for k, v in state.product_tracks.items()
                            },
                        },
                    )
                )
            else:
                await self._route_to_stage(task, OnboardingStage.COMPLETE)

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={"product_code": product_code, "track_status": track_status},
        )

    async def _handle_escalate(self, task: TaskPacket) -> TaskResponse:
        import asyncio

        case_id = task.case_id
        reason: str = task.payload.get("reason", "Unspecified escalation")

        fsm = self._get_or_create_fsm(case_id)
        try:
            fsm.transition(OnboardingStage.ESCALATED)
        except InvalidTransitionError:
            pass  # already escalated — still notify

        if case_id in self._states:
            self._states[case_id].escalation_reason = reason

        await self.send_task(
            TaskPacket(
                from_agent=self.agent_id,
                to_agent=AgentID.NOTIFICATION,
                task_type=TaskType.SEND_ESCALATION_ALERT,
                case_id=case_id,
                client_id=task.client_id,
                priority="HIGH",
                payload={"reason": reason},
            )
        )

        # Notify Contact Centre so representatives have an AI-generated call
        # summary ready if the client phones in about the escalation.
        await self.send_task(
            TaskPacket(
                from_agent=self.agent_id,
                to_agent=AgentID.CONTACT_CENTRE,
                task_type=TaskType.SUMMARISE_CALL,
                case_id=case_id,
                client_id=task.client_id,
                priority="HIGH",
                payload={
                    "onboarding_state": {"stage": "ESCALATED", "escalation_reason": reason},
                    "client_data": task.payload.get("client_data", {}),
                },
            )
        )

        # Persist HumanReview record in background (owns its own DB session)
        asyncio.create_task(
            self._persist_human_review(case_id, task.client_id, reason, task.payload)
        )

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="ESCALATED",
            result={"reason": reason},
        )

    async def _persist_human_review(
        self,
        case_id: UUID,
        client_id: UUID,
        reason: str,
        payload: dict,
    ) -> None:
        from app.database import AsyncSessionLocal
        from app.services.compliance.human_review_service import human_review_service

        async with AsyncSessionLocal() as db:
            try:
                await human_review_service.create_review(
                    case_id=case_id,
                    client_id=client_id,
                    escalation_reason=reason,
                    kyc_payload=payload,
                    db=db,
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.error(
                    f"Failed to persist HumanReview for case={case_id}: {exc}"
                )

    async def _handle_health_check(self, task: TaskPacket) -> TaskResponse:
        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={"status": "healthy", "active_cases": len(self._fsms)},
        )

    # ── Stage routing ─────────────────────────────────────────────────────────

    async def _route_to_stage(self, task: TaskPacket, stage: OnboardingStage) -> None:
        selected_products: list[str] = task.payload.get("selected_products", [])

        if stage == OnboardingStage.KYC:
            await self.send_task(
                TaskPacket(
                    from_agent=self.agent_id,
                    to_agent=AgentID.KYC_COMPLIANCE,
                    task_type=TaskType.RUN_KYC_CHECK,
                    case_id=task.case_id,
                    client_id=task.client_id,
                    priority="HIGH",
                    payload=task.payload,
                )
            )

        elif stage == OnboardingStage.PARALLEL_PRODUCTS:
            if task.case_id in self._states:
                for product_code in selected_products:
                    self._states[task.case_id].product_tracks[product_code] = ProductTrackState(
                        product_code=product_code,
                        stage="IN_PROGRESS",
                        started_at=datetime.utcnow(),
                    )

            for product_code in selected_products:
                await self.send_task(
                    TaskPacket(
                        from_agent=self.agent_id,
                        to_agent=AgentID.PRODUCT_ONBOARDING,
                        task_type=TaskType.ONBOARD_PRODUCT,
                        case_id=task.case_id,
                        client_id=task.client_id,
                        priority="NORMAL",
                        payload={**task.payload, "product_code": product_code},
                    )
                )

        elif stage == OnboardingStage.REVIEW:
            await self.send_task(
                TaskPacket(
                    from_agent=self.agent_id,
                    to_agent=AgentID.COLLABORATION,
                    task_type=TaskType.CREATE_COLLABORATION_ROOM,
                    case_id=task.case_id,
                    client_id=task.client_id,
                    priority="NORMAL",
                    payload=task.payload,
                )
            )

        elif stage == OnboardingStage.COMPLETE:
            await self.send_task(
                TaskPacket(
                    from_agent=self.agent_id,
                    to_agent=AgentID.NOTIFICATION,
                    task_type=TaskType.SEND_NOTIFICATION,
                    case_id=task.case_id,
                    client_id=task.client_id,
                    priority="NORMAL",
                    payload={"type": "ONBOARDING_COMPLETE"},
                )
            )

            # Push a final status snapshot to the Contact Centre agent so
            # representatives have an up-to-date summary if the client calls.
            await self.send_task(
                TaskPacket(
                    from_agent=self.agent_id,
                    to_agent=AgentID.CONTACT_CENTRE,
                    task_type=TaskType.GET_CLIENT_STATUS,
                    case_id=task.case_id,
                    client_id=task.client_id,
                    priority="LOW",
                    payload={
                        "onboarding_state": {"stage": "COMPLETE"},
                        "client_data": task.payload.get("client_data", {}),
                    },
                )
            )
