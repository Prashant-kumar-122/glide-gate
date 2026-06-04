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


async def _persist_case_stage(
    case_id: UUID, stage: str, percentage: float | None = None
) -> None:
    """Write status + current_stage (and optionally percentage) to the DB."""
    from sqlalchemy import update as sa_update
    from app.database import AsyncSessionLocal
    from app.models.cases import OnboardingCase

    values: dict = {"status": stage, "current_stage": stage}
    if percentage is not None:
        values["percentage"] = percentage

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_update(OnboardingCase)
            .where(OnboardingCase.id == case_id)
            .values(**values)
        )
        await db.commit()


async def _persist_accounts(
    case_id: UUID, client_id: UUID, products: list[str]
) -> None:
    """Generate one account number per product for a completed case."""
    from app.database import AsyncSessionLocal
    from app.services.accounts.account_service import AccountService

    async with AsyncSessionLocal() as db:
        await AccountService.ensure_created(
            session=db,
            case_id=case_id,
            client_id=client_id,
            products=products,
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

        client_name = task.payload.get("client_name", "")
        client_email = task.payload.get("client_email", "")
        case_name = task.payload.get("case_name", "")

        # Email notification — sent to client's inbox
        await self.send_task(
            TaskPacket(
                from_agent=self.agent_id,
                to_agent=AgentID.NOTIFICATION,
                task_type=TaskType.SEND_NOTIFICATION,
                case_id=case_id,
                client_id=task.client_id,
                priority="NORMAL",
                payload={
                    "template": "onboarding_started",
                    "selected_products": selected_products,
                    "client_name": client_name,
                    "case_name": case_name,
                    "recipient_email": client_email,
                },
            )
        )

        # In-app notification — direct to client user room
        await self.send_task(
            TaskPacket(
                from_agent=self.agent_id,
                to_agent=AgentID.NOTIFICATION,
                task_type=TaskType.SEND_NOTIFICATION,
                case_id=case_id,
                client_id=task.client_id,
                priority="NORMAL",
                payload={
                    "template": "case_created_inapp",
                    "selected_products": selected_products,
                    "client_name": client_name,
                    "case_name": case_name,
                },
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
            OnboardingStage.SALES_REVIEW: (AgentID.SALES_MANAGER, TaskType.SALES_MANAGER_REVIEW),
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

        # The in-memory FSM can drift out of sync when the DB stage was updated
        # directly (e.g. submit-intake sets DB to REVIEW without going through the
        # FSM).  If the transition is not reachable from the current FSM state,
        # reload from the DB and retry once before giving up.
        if not fsm.can_transition(to_stage):
            db_stage = await self._load_stage_from_db(case_id)
            if db_stage and db_stage != fsm.stage:
                self.logger.info(
                    f"[FSM] case={case_id} syncing from DB: "
                    f"{fsm.stage} → {db_stage} (then will attempt → {to_stage})"
                )
                fsm.restore(db_stage)

        try:
            fsm.transition(to_stage)
        except InvalidTransitionError as exc:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=[str(exc)],
            )

        # Persist to DB so any downstream stage checks (e.g. doc-approval trigger)
        # see the correct current_stage immediately.
        asyncio.create_task(_persist_case_stage(case_id, to_stage.value))

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

            pct = 100.0 if target_stage == OnboardingStage.COMPLETE else None
            asyncio.create_task(_persist_case_stage(case_id, target_stage.value, pct))

            if target_stage == OnboardingStage.COMPLETE:
                # Await so account numbers are in DB before the completion notification queries them
                await _persist_accounts(case_id, task.client_id, list(state.selected_products))

            if has_issues:
                from app.websocket.socket_emitter import socket_emitter as _se
                await _se.case_stage_changed(case_id, {
                    "case_id": str(case_id),
                    "stage": OnboardingStage.REVIEW.value,
                    "triggered_by": "product_track_complete",
                })
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
                from app.websocket.socket_emitter import socket_emitter
                await socket_emitter.case_stage_changed(case_id, {
                    "case_id": str(case_id),
                    "stage": OnboardingStage.COMPLETE.value,
                    "triggered_by": "product_track_complete",
                })
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

    # ── DB helpers ────────────────────────────────────────────────────────────

    async def _load_stage_from_db(self, case_id: UUID) -> OnboardingStage | None:
        """Return the persisted current_stage for a case, or None on error."""
        try:
            from sqlalchemy import select as _select
            from app.database import AsyncSessionLocal
            from app.models.cases import OnboardingCase
            async with AsyncSessionLocal() as db:
                row = await db.execute(
                    _select(OnboardingCase.current_stage).where(OnboardingCase.id == case_id)
                )
                raw = row.scalar_one_or_none()
                return OnboardingStage(raw) if raw else None
        except Exception as exc:
            self.logger.warning(f"[FSM] Could not load DB stage for case={case_id}: {exc}")
            return None

    # ── Institutional check ───────────────────────────────────────────────────

    async def _has_institutional_product(
        self, case_id: UUID, payload: dict
    ) -> bool:
        """Return True if any selected product in the case is institutional type."""
        selected: list[str] = payload.get("selected_products", [])
        if not selected:
            # Fall back to DB if payload doesn't carry products
            try:
                from app.database import AsyncSessionLocal
                from app.models.cases import OnboardingCase
                from sqlalchemy import select as _select
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        _select(OnboardingCase).where(OnboardingCase.id == case_id)
                    )
                    case = result.scalar_one_or_none()
                    if case:
                        selected = case.selected_products or []
            except Exception as exc:
                self.logger.warning(
                    f"Could not load products for institutional check: {exc}"
                )
                return False

        if not selected:
            return False

        try:
            from app.database import AsyncSessionLocal
            from app.models.cases import Product
            from sqlalchemy import select as _select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    _select(Product).where(
                        Product.product_code.in_(selected),
                        Product.product_type == "institutional",
                    )
                )
                return result.scalar_one_or_none() is not None
        except Exception as exc:
            self.logger.warning(f"Institutional product check failed: {exc}")
            return False

    # ── Stage routing ─────────────────────────────────────────────────────────

    async def _route_to_stage(self, task: TaskPacket, stage: OnboardingStage) -> None:
        selected_products: list[str] = task.payload.get("selected_products", [])

        if stage == OnboardingStage.SALES_REVIEW:
            await self.send_task(
                TaskPacket(
                    from_agent=self.agent_id,
                    to_agent=AgentID.SALES_MANAGER,
                    task_type=TaskType.SALES_MANAGER_REVIEW,
                    case_id=task.case_id,
                    client_id=task.client_id,
                    priority="HIGH",
                    payload=task.payload,
                )
            )
            from app.websocket.socket_emitter import socket_emitter as _se
            await _se.case_stage_changed(task.case_id, {
                "case_id": str(task.case_id),
                "stage": OnboardingStage.SALES_REVIEW.value,
                "triggered_by": "institutional_product_detected",
            })

        elif stage == OnboardingStage.KYC:
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
            state = self._states.get(task.case_id)
            _client_data = state.client_data if state else {}
            _client_name = (
                _client_data.get("full_name")
                or f"{_client_data.get('first_name', '')} {_client_data.get('last_name', '')}".strip()
                or task.payload.get("client_name", "")
            )
            _client_email = (
                _client_data.get("email")
                or _client_data.get("email_address", "")
                or task.payload.get("client_email", "")
            )
            # client_data is never populated in orchestrator state — fall back to DB
            _case_name = task.payload.get("case_name", "")
            _account_numbers = ""
            if not _client_email or not _client_name or not _case_name or not _account_numbers:
                from app.database import AsyncSessionLocal
                from app.models.users import User
                from app.models.cases import OnboardingCase
                from app.models.accounts import ClientAccount
                from sqlalchemy import select as _select
                try:
                    async with AsyncSessionLocal() as _db:
                        if not _client_email or not _client_name:
                            _user = await _db.get(User, task.client_id)
                            if _user:
                                _client_name = _client_name or _user.full_name or f"{_user.first_name} {_user.last_name}".strip()
                                _client_email = _client_email or _user.email
                        if not _case_name:
                            _case = await _db.get(OnboardingCase, task.case_id)
                            if _case:
                                _case_name = (_case.extra_metadata or {}).get("case_name", "")
                        _accts = await _db.execute(
                            _select(ClientAccount).where(ClientAccount.case_id == task.case_id)
                        )
                        _account_numbers = ", ".join(
                            a.account_number for a in _accts.scalars().all()
                        ) or "—"
                except Exception as _exc:
                    self.logger.warning(f"Could not fetch client/accounts for COMPLETE notification: {_exc}")
            _products = list(state.selected_products) if state else task.payload.get("selected_products", [])

            for _tmpl in ("onboarding_complete", "onboarding_complete_inapp"):
                await self.send_task(
                    TaskPacket(
                        from_agent=self.agent_id,
                        to_agent=AgentID.NOTIFICATION,
                        task_type=TaskType.SEND_NOTIFICATION,
                        case_id=task.case_id,
                        client_id=task.client_id,
                        priority="NORMAL",
                        payload={
                            "template": _tmpl,
                            "client_name": _client_name,
                            "case_name": _case_name,
                            "selected_products": _products,
                            "recipient_email": _client_email,
                            "account_numbers": _account_numbers,
                        },
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
