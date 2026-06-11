"""AgentOrchestrationService — Temporal-backed orchestration (Phase 0.5).

Replaces the asyncio AgentEventBus dispatch loops with a self-hosted Temporal
worker. API entry points (start_onboarding, resume_onboarding, publish_task)
are preserved so no call-sites outside this module need to change.

The AgentEventBus and BaseAgent dispatch loops remain available for the
document-processing and conversation REST endpoints that call agents directly
without going through a Temporal workflow.
"""
from __future__ import annotations

import asyncio
from uuid import UUID

from loguru import logger

from app.agents.base.a2a_types import (
    AgentID,
    OnboardingStage,
    OnboardingWorkflowInput,
    StageAdvanceSignal,
    HumanReviewSignal,
    TaskPacket,
    TaskType,
)

# ── Temporal configuration ────────────────────────────────────────────────────

_TEMPORAL_HOST = "localhost:7233"
_TASK_QUEUE = "onboarding"

# ── Helpers ───────────────────────────────────────────────────────────────────


def _workflow_id(case_id: UUID) -> str:
    return f"onboarding-{case_id}"


# ── Service ───────────────────────────────────────────────────────────────────


class AgentOrchestrationService:
    """Singleton service that boots the Temporal worker on application startup.

    Responsibilities:
    - Connect to the self-hosted Temporal server.
    - Register all Temporal workflows and activities.
    - Start the Temporal worker as a background asyncio task.
    - Provide `start_onboarding`, `resume_onboarding`, and `publish_task`
      entry points called by the REST API layer.

    The legacy AgentEventBus is kept for direct agent calls (document
    processing, contact-centre queries) that are invoked per-request and do not
    need the durability of a long-running workflow.
    """

    def __init__(self) -> None:
        self._temporal_client = None
        self._worker = None
        self._worker_task: asyncio.Task | None = None
        self._active_cases: set[UUID] = set()
        self._started = False

        # Legacy event bus — kept for direct per-request agent calls.
        from app.agents.base.agent_event_bus import AgentEventBus
        from app.services.orchestration.agent_registry import AgentRegistry

        self._bus = AgentEventBus()
        self._registry = AgentRegistry()
        self._dispatch_tasks: list[asyncio.Task] = []

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Connect to Temporal and start the worker. Safe to call multiple times."""
        if self._started:
            return

        # 1. Build legacy agents for direct (non-workflow) calls.
        self._build_legacy_agents()

        # 2. Start legacy dispatch loops for non-workflow agent tasks.
        self._dispatch_tasks = await self._bus.start_all()

        # 3. Connect to Temporal and start the worker.
        try:
            await self._start_temporal_worker()
        except Exception as exc:
            logger.warning(
                f"Temporal worker failed to start (Temporal not available?): {exc}\n"
                "Stage-level orchestration will use legacy asyncio bus."
            )

        self._started = True
        logger.info("AgentOrchestrationService started (Temporal + legacy bus)")

    async def stop(self) -> None:
        """Cancel all background tasks and close Temporal connection."""
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

        if self._worker is not None:
            await self._worker.shutdown()
            self._worker = None

        for task in self._dispatch_tasks:
            task.cancel()
        if self._dispatch_tasks:
            await asyncio.gather(*self._dispatch_tasks, return_exceptions=True)
        self._dispatch_tasks = []

        self._started = False
        logger.info("AgentOrchestrationService stopped")

    # ── Onboarding entry points ───────────────────────────────────────────────

    async def start_onboarding(
        self,
        case_id: UUID,
        client_id: UUID,
        selected_products: list[str],
        client_name: str = "",
        client_email: str = "",
        case_name: str = "",
    ) -> None:
        """Start a new OnboardingWorkflow via Temporal (or fall back to legacy bus)."""
        if not self._started:
            await self.start()

        self._active_cases.add(case_id)

        if self._temporal_client is not None:
            try:
                from app.workflows.onboarding_workflow import OnboardingWorkflow

                await self._temporal_client.start_workflow(
                    OnboardingWorkflow.run,
                    OnboardingWorkflowInput(
                        case_id=str(case_id),
                        client_id=str(client_id),
                        selected_products=selected_products,
                        client_name=client_name,
                        client_email=client_email,
                        case_name=case_name,
                    ),
                    id=_workflow_id(case_id),
                    task_queue=_TASK_QUEUE,
                )
                logger.info(
                    f"OnboardingWorkflow started via Temporal: "
                    f"case={case_id} products={selected_products}"
                )
                return
            except Exception as exc:
                logger.warning(
                    f"Temporal start_workflow failed for case={case_id}: {exc}. "
                    "Falling back to legacy orchestration."
                )

        # Legacy fallback
        await self._legacy_start_onboarding(
            case_id, client_id, selected_products, client_name, client_email, case_name
        )

    async def resume_onboarding(self, case_id: UUID) -> None:
        """Signal an existing Temporal workflow to resume (or legacy bus)."""
        if not self._started:
            await self.start()

        self._active_cases.add(case_id)

        if self._temporal_client is not None:
            try:
                handle = self._temporal_client.get_workflow_handle(_workflow_id(case_id))
                # Load persisted stage to determine which signal to send
                try:
                    from app.services.context_store.context_store_service import context_store
                    state = await context_store.get(case_id)
                    stage = str(state.stage)
                except KeyError:
                    stage = OnboardingStage.INTAKE

                await handle.signal(
                    OnboardingWorkflow_advance_stage_name(),
                    StageAdvanceSignal(to_stage=stage),
                )
                logger.info(f"Signalled OnboardingWorkflow to resume: case={case_id} stage={stage}")
                return
            except Exception as exc:
                logger.warning(
                    f"Temporal signal failed for case={case_id}: {exc}. "
                    "Falling back to legacy resume."
                )

        # Legacy fallback
        await self._legacy_resume_onboarding(case_id)

    async def publish_task(self, task: TaskPacket) -> None:
        """Route a TaskPacket to Temporal (signal/activity) or legacy bus.

        Stage-advance and escalate packets become Temporal Signals.
        All other packets are dispatched via the legacy event bus.
        """
        if not self._started:
            await self.start()

        # Route orchestration and agent-trigger tasks through Temporal Signals.
        # RUN_KYC_CHECK and SALES_MANAGER_REVIEW kick off a new workflow stage.
        _TEMPORAL_SIGNAL_TYPES = {
            TaskType.ADVANCE_STAGE,
            TaskType.ESCALATE,
            TaskType.RESUME_ONBOARDING,
            TaskType.RUN_KYC_CHECK,
            TaskType.SALES_MANAGER_REVIEW,
        }
        if self._temporal_client is not None and task.task_type in _TEMPORAL_SIGNAL_TYPES:
            try:
                handle = self._temporal_client.get_workflow_handle(
                    _workflow_id(task.case_id)
                )
                if task.task_type == TaskType.ESCALATE:
                    signal = StageAdvanceSignal(
                        to_stage=OnboardingStage.ESCALATED,
                        payload={"escalation_reason": task.payload.get("reason", "")},
                    )
                elif task.task_type == TaskType.RUN_KYC_CHECK:
                    signal = StageAdvanceSignal(to_stage=OnboardingStage.KYC, payload=task.payload)
                elif task.task_type == TaskType.SALES_MANAGER_REVIEW:
                    signal = StageAdvanceSignal(to_stage=OnboardingStage.SALES_REVIEW, payload=task.payload)
                else:
                    signal = StageAdvanceSignal(
                        to_stage=task.payload.get("to_stage", ""),
                        payload=task.payload,
                    )
                await handle.signal("advance_stage", signal)
                return
            except Exception as exc:
                logger.warning(
                    f"Temporal signal failed for task {task.task_type} "
                    f"case={task.case_id}: {exc}. Using legacy bus."
                )

        # All other tasks (notifications, doc processing, etc.) go through the legacy bus.
        await self._bus.publish(task)

    async def start_product_onboarding(
        self,
        case_id: UUID,
        client_id: UUID,
        selected_products: list[str],
    ) -> None:
        """Signal the workflow to begin PARALLEL_PRODUCTS (called post human-review)."""
        if not self._started:
            await self.start()

        if self._temporal_client is not None:
            try:
                handle = self._temporal_client.get_workflow_handle(_workflow_id(case_id))
                await handle.signal(
                    "human_review_completed",
                    HumanReviewSignal(
                        decision="APPROVED",
                        reviewer_id="system",
                        payload={"selected_products": selected_products},
                    ),
                )
                return
            except Exception as exc:
                logger.warning(
                    f"Temporal signal for start_product_onboarding failed "
                    f"case={case_id}: {exc}. Falling back."
                )

        # Legacy fallback
        for product_code in selected_products:
            await self._bus.publish(
                TaskPacket(
                    from_agent=AgentID.ORCHESTRATOR,
                    to_agent=AgentID.PRODUCT_ONBOARDING,
                    task_type=TaskType.ONBOARD_PRODUCT,
                    case_id=case_id,
                    client_id=client_id,
                    priority="HIGH",
                    payload={"product_code": product_code, "selected_products": selected_products},
                )
            )

    # ── Temporal Signals (convenience helpers for API routers) ────────────────

    async def signal_stage_advance(
        self, case_id: UUID, to_stage: str, payload: dict | None = None
    ) -> None:
        """Send advance_stage signal to the running OnboardingWorkflow."""
        if self._temporal_client is None:
            logger.warning(
                f"Temporal not available; cannot signal advance_stage for case={case_id}"
            )
            return
        try:
            handle = self._temporal_client.get_workflow_handle(_workflow_id(case_id))
            await handle.signal(
                "advance_stage",
                StageAdvanceSignal(to_stage=to_stage, payload=payload or {}),
            )
        except Exception as exc:
            logger.warning(f"signal_stage_advance failed for case={case_id}: {exc}")

    async def signal_human_review(
        self,
        case_id: UUID,
        decision: str,
        reviewer_id: str,
        payload: dict | None = None,
    ) -> None:
        """Send human_review_completed signal to the running OnboardingWorkflow."""
        if self._temporal_client is None:
            logger.warning(
                f"Temporal not available; cannot signal human_review for case={case_id}"
            )
            return
        try:
            handle = self._temporal_client.get_workflow_handle(_workflow_id(case_id))
            await handle.signal(
                "human_review_completed",
                HumanReviewSignal(
                    decision=decision,
                    reviewer_id=reviewer_id,
                    payload=payload or {},
                ),
            )
        except Exception as exc:
            logger.warning(f"signal_human_review failed for case={case_id}: {exc}")

    # ── Introspection ─────────────────────────────────────────────────────────

    @property
    def active_cases(self) -> frozenset[UUID]:
        return frozenset(self._active_cases)

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def temporal_client(self):
        return self._temporal_client

    # ── Internal: Temporal worker ─────────────────────────────────────────────

    async def _start_temporal_worker(self) -> None:
        from temporalio.client import Client
        from temporalio.worker import Worker

        from app.workflows.onboarding_workflow import (
            OnboardingWorkflow,
            ProductOnboardingWorkflow,
            get_all_activities,
        )

        self._temporal_client = await Client.connect(_TEMPORAL_HOST)
        self._worker = Worker(
            self._temporal_client,
            task_queue=_TASK_QUEUE,
            workflows=[OnboardingWorkflow, ProductOnboardingWorkflow],
            activities=get_all_activities(),
        )
        self._worker_task = asyncio.create_task(
            self._worker.run(), name="temporal-worker"
        )
        logger.info(
            f"Temporal worker started: host={_TEMPORAL_HOST} queue={_TASK_QUEUE}"
        )

    # ── Internal: legacy bus agents ───────────────────────────────────────────

    def _build_legacy_agents(self) -> None:
        """Register non-workflow agents on the legacy event bus.

        These agents handle per-request tasks (notifications, document
        processing, collaboration) that arrive via publish_task() and do not
        need Temporal durability.
        """
        from app.agents.collaboration.collaboration_agent import CollaborationAgent
        from app.agents.contact_centre.contact_centre_agent import ContactCentreAgent
        from app.agents.document_intelligence.document_intelligence_agent import (
            DocumentIntelligenceAgent,
        )
        from app.agents.notification.notification_agent import NotificationAgent
        from app.agents.product_onboarding.product_onboarding_agent import ProductOnboardingAgent
        from app.agents.sales_manager.sales_manager_agent import SalesManagerAgent
        from app.services.orchestration.agent_registry import AgentRegistry
        from app.services.orchestration.parallel_product_launcher import ParallelProductLauncher

        self._registry = AgentRegistry()
        self._launcher = ParallelProductLauncher(self._bus)

        agents_to_register = [
            CollaborationAgent(),
            ContactCentreAgent(),
            DocumentIntelligenceAgent(),
            NotificationAgent(),
            SalesManagerAgent(),
        ]

        for agent in agents_to_register:
            self._bus.register(agent)
            self._registry.register(agent)

        # ProductOnboardingAgent placeholder for its bus queue.
        placeholder = ProductOnboardingAgent()
        self._bus.register(placeholder)

    # ── Internal: legacy fallback ─────────────────────────────────────────────

    async def _legacy_start_onboarding(
        self,
        case_id: UUID,
        client_id: UUID,
        selected_products: list[str],
        client_name: str,
        client_email: str,
        case_name: str,
    ) -> None:
        from app.services.context_store.context_store_service import context_store
        from app.websocket.socket_emitter import socket_emitter

        try:
            await context_store.initialise(case_id, client_id, selected_products)
        except Exception as exc:
            logger.warning(f"ContextStore initialise failed for case {case_id}: {exc}")

        await socket_emitter.case_stage_changed(
            case_id,
            {"case_id": str(case_id), "stage": OnboardingStage.INTAKE, "selected_products": selected_products},
        )

        # Legacy OrchestratorAgent still handles START_ONBOARDING on the bus.
        from app.agents.orchestrator.orchestrator_agent import OrchestratorAgent

        if AgentID.ORCHESTRATOR not in self._bus._queues:
            orchestrator = OrchestratorAgent()
            self._bus.register(orchestrator)
            self._registry.register(orchestrator)
            self._dispatch_tasks.append(
                asyncio.create_task(self._bus.dispatch_loop(AgentID.ORCHESTRATOR))
            )
            from app.agents.customer_service.customer_service_agent import CustomerServiceAgent
            cs = CustomerServiceAgent()
            self._bus.register(cs)
            self._registry.register(cs)
            self._dispatch_tasks.append(
                asyncio.create_task(self._bus.dispatch_loop(AgentID.CUSTOMER_SERVICE))
            )
            from app.agents.kyc_compliance.kyc_compliance_agent import KYCComplianceAgent
            kyc = KYCComplianceAgent()
            self._bus.register(kyc)
            self._registry.register(kyc)
            self._dispatch_tasks.append(
                asyncio.create_task(self._bus.dispatch_loop(AgentID.KYC_COMPLIANCE))
            )

        await self._bus.publish(
            TaskPacket(
                from_agent=AgentID.ORCHESTRATOR,
                to_agent=AgentID.ORCHESTRATOR,
                task_type=TaskType.START_ONBOARDING,
                case_id=case_id,
                client_id=client_id,
                priority="NORMAL",
                payload={
                    "selected_products": selected_products,
                    "client_name": client_name,
                    "client_email": client_email,
                    "case_name": case_name,
                },
            )
        )
        logger.info(
            f"[Legacy] Onboarding started: case={case_id} products={selected_products}"
        )

    async def _legacy_resume_onboarding(self, case_id: UUID) -> None:
        try:
            from app.services.context_store.context_store_service import context_store
            state = await context_store.get(case_id)
        except KeyError:
            logger.error(f"Cannot resume: no state found for case {case_id}")
            return

        from app.websocket.socket_emitter import socket_emitter
        await socket_emitter.case_stage_changed(
            case_id,
            {"case_id": str(case_id), "stage": state.stage, "event": "JOURNEY_RESUMED"},
        )
        await self._bus.publish(
            TaskPacket(
                from_agent=AgentID.ORCHESTRATOR,
                to_agent=AgentID.ORCHESTRATOR,
                task_type=TaskType.RESUME_ONBOARDING,
                case_id=case_id,
                client_id=state.client_id,
                priority="HIGH",
                payload={"stage": state.stage, "selected_products": state.selected_products},
            )
        )


def OnboardingWorkflow_advance_stage_name() -> str:
    return "advance_stage"


# Process-level singleton — imported by main.py, routers, and services.
orchestration_service = AgentOrchestrationService()
