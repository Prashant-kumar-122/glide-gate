from __future__ import annotations

import asyncio
from uuid import UUID

from loguru import logger

from app.agents.base.a2a_types import AgentID, OnboardingStage, TaskPacket, TaskType
from app.agents.base.agent_event_bus import AgentEventBus
from app.agents.collaboration.collaboration_agent import CollaborationAgent
from app.agents.contact_centre.contact_centre_agent import ContactCentreAgent
from app.agents.customer_service.customer_service_agent import CustomerServiceAgent
from app.agents.document_intelligence.document_intelligence_agent import DocumentIntelligenceAgent
from app.agents.kyc_compliance.kyc_compliance_agent import KYCComplianceAgent
from app.agents.notification.notification_agent import NotificationAgent
from app.agents.orchestrator.orchestrator_agent import OrchestratorAgent
from app.services.context_store.context_store_service import context_store
from app.services.orchestration.agent_registry import AgentRegistry
from app.services.orchestration.parallel_product_launcher import ParallelProductLauncher
from app.websocket.socket_emitter import socket_emitter


class AgentOrchestrationService:
    """Singleton service that boots the entire CADF agent network.

    Responsibilities:
    - Instantiate all 8 agents and wire them to a shared AgentEventBus.
    - Start per-agent dispatch loops (asyncio.Tasks) on application startup.
    - Provide `start_onboarding` and `resume_onboarding` entry points called
      by the REST API layer.
    - Use ParallelProductLauncher for the ProductOnboarding queue so that
      multiple product tracks run truly in parallel (asyncio.gather).

    The ProductOnboardingAgent is deliberately NOT registered in the event
    bus in the standard way — the ParallelProductLauncher owns that queue's
    dispatch loop and creates one fresh agent instance per product task.
    """

    def __init__(self) -> None:
        self._bus = AgentEventBus()
        self._registry = AgentRegistry()
        self._launcher = ParallelProductLauncher(self._bus)
        self._dispatch_tasks: list[asyncio.Task] = []
        self._active_cases: set[UUID] = set()
        self._started = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Initialise all agents, wire the event bus, and start dispatch loops.

        Safe to call multiple times — subsequent calls are no-ops.
        """
        if self._started:
            return

        self._build_agents()

        # Start standard dispatch loops for every agent except ProductOnboarding
        # (which is handled by ParallelProductLauncher).
        self._dispatch_tasks = await self._bus.start_all()

        # Add the parallel dispatch loop for ProductOnboarding.
        parallel_task = await self._launcher.start_dispatch_loop()
        self._dispatch_tasks.append(parallel_task)

        self._started = True
        logger.info(
            f"AgentOrchestrationService started — "
            f"{len(self._registry)} agents registered, "
            f"{len(self._dispatch_tasks)} dispatch loops running"
        )

    async def stop(self) -> None:
        """Cancel all dispatch loops and clean up."""
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
    ) -> None:
        """Kick off a new onboarding workflow.

        1. Initialises shared OnboardingState in the ContextStoreService.
        2. Emits CASE_STAGE_CHANGED (INTAKE) over WebSocket.
        3. Publishes START_ONBOARDING to the Orchestrator queue.

        The Orchestrator then fans out to CustomerServiceAgent to begin
        the data-collection conversation.
        """
        if not self._started:
            logger.warning("AgentOrchestrationService.start_onboarding called before start()")
            await self.start()

        try:
            await context_store.initialise(case_id, client_id, selected_products)
        except Exception as exc:
            logger.warning(
                f"ContextStore initialise failed for case {case_id} "
                f"(continuing without persistent state): {exc}"
            )

        await socket_emitter.case_stage_changed(
            case_id,
            {
                "case_id": str(case_id),
                "stage": OnboardingStage.INTAKE,
                "selected_products": selected_products,
            },
        )

        await self._bus.publish(
            TaskPacket(
                from_agent=AgentID.ORCHESTRATOR,
                to_agent=AgentID.ORCHESTRATOR,
                task_type=TaskType.START_ONBOARDING,
                case_id=case_id,
                client_id=client_id,
                priority="NORMAL",
                payload={"selected_products": selected_products},
            )
        )

        self._active_cases.add(case_id)
        logger.info(
            f"Onboarding started: case={case_id} "
            f"client={client_id} products={selected_products}"
        )

    async def start_product_onboarding(
        self,
        case_id: UUID,
        client_id: UUID,
        selected_products: list[str],
    ) -> None:
        """Resume a case directly at the PARALLEL_PRODUCTS stage.

        Called by HumanReviewService after a review is APPROVED.
        Bypasses the standard FSM advance and directly fans out to
        ProductOnboardingAgent for each selected product.
        """
        if not self._started:
            await self.start()

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

        self._active_cases.add(case_id)
        logger.info(
            f"Product onboarding started (post-review): case={case_id} "
            f"products={selected_products}"
        )

    async def resume_onboarding(self, case_id: UUID) -> None:
        """Resume a paused onboarding case.

        Loads persisted OnboardingState from the ContextStoreService,
        emits a CASE_STAGE_CHANGED event, and publishes RESUME_ONBOARDING
        to the Orchestrator which re-routes to the correct stage.
        """
        if not self._started:
            logger.warning("AgentOrchestrationService.resume_onboarding called before start()")
            await self.start()

        try:
            state = await context_store.get(case_id)
        except KeyError:
            logger.error(f"Cannot resume: no state found for case {case_id}")
            return

        await socket_emitter.case_stage_changed(
            case_id,
            {
                "case_id": str(case_id),
                "stage": state.stage,
                "event": "JOURNEY_RESUMED",
            },
        )

        await self._bus.publish(
            TaskPacket(
                from_agent=AgentID.ORCHESTRATOR,
                to_agent=AgentID.ORCHESTRATOR,
                task_type=TaskType.RESUME_ONBOARDING,
                case_id=case_id,
                client_id=state.client_id,
                priority="HIGH",
                payload={
                    "stage": state.stage,
                    "selected_products": state.selected_products,
                    "client_data": state.client_data,
                },
            )
        )

        self._active_cases.add(case_id)
        logger.info(f"Onboarding resumed: case={case_id} stage={state.stage}")

    # ── Introspection ─────────────────────────────────────────────────────────

    @property
    def active_cases(self) -> set[UUID]:
        return frozenset(self._active_cases)

    @property
    def registry(self) -> AgentRegistry:
        return self._registry

    @property
    def is_started(self) -> bool:
        return self._started

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_agents(self) -> None:
        """Instantiate all agents and register them on the event bus.

        ProductOnboardingAgent is registered on the bus so the queue
        exists, but its dispatch loop is replaced by ParallelProductLauncher.
        """
        from app.agents.product_onboarding.product_onboarding_agent import ProductOnboardingAgent

        agents_to_register = [
            OrchestratorAgent(),
            CustomerServiceAgent(),
            KYCComplianceAgent(),
            DocumentIntelligenceAgent(),
            CollaborationAgent(),
            ContactCentreAgent(),
            NotificationAgent(),
        ]

        for agent in agents_to_register:
            self._bus.register(agent)
            self._registry.register(agent)

        # Register a placeholder ProductOnboardingAgent solely to create the
        # queue; ParallelProductLauncher will create fresh instances per task.
        placeholder = ProductOnboardingAgent()
        self._bus.register(placeholder)
        # Do NOT add to registry — launcher creates its own instances.


# Process-level singleton — imported by main.py, routers, and services.
orchestration_service = AgentOrchestrationService()
