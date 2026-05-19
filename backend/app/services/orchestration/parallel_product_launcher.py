from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from loguru import logger

from app.agents.base.a2a_types import AgentID, OnboardingStage, TaskPacket, TaskResponse, TaskType
from app.agents.product_onboarding.product_onboarding_agent import ProductOnboardingAgent
from app.websocket.socket_emitter import socket_emitter

if TYPE_CHECKING:
    from app.agents.base.agent_event_bus import AgentEventBus


class ParallelProductLauncher:
    """Custom dispatch layer for the ProductOnboarding agent queue.

    Instead of running a single serial dispatch loop, this launcher:
    1. Drains all pending ONBOARD_PRODUCT tasks from the bus queue.
    2. Groups them by case_id.
    3. For each case, runs one ProductOnboardingAgent per product in
       parallel via asyncio.gather, ensuring independent product tracks
       never block each other (BRD FR-01, Section 7.1, Criterion #3).

    A fresh ProductOnboardingAgent instance is created per product task
    so that each has isolated state. All instances share the same event
    bus reference so they can signal the Orchestrator on completion.
    """

    def __init__(self, bus: AgentEventBus) -> None:
        self._bus = bus

    # ── Public API ────────────────────────────────────────────────────────────

    async def start_dispatch_loop(self) -> asyncio.Task:
        """Create and return the asyncio Task for the parallel dispatch loop."""
        task = asyncio.create_task(
            self._dispatch_loop(), name="bus-product_onboarding-parallel"
        )
        return task

    async def launch_for_case(
        self,
        case_id: UUID,
        client_id: UUID,
        selected_products: list[str],
        client_data: dict | None = None,
    ) -> list[TaskResponse]:
        """Directly launch product onboarding for all products in parallel.

        This is the preferred entry point when the AgentOrchestrationService
        has already routed the workflow to PARALLEL_PRODUCTS and wants to
        bypass the queue for immediate parallel execution.
        """
        tasks = [
            TaskPacket(
                from_agent=AgentID.ORCHESTRATOR,
                to_agent=AgentID.PRODUCT_ONBOARDING,
                task_type=TaskType.ONBOARD_PRODUCT,
                case_id=case_id,
                client_id=client_id,
                priority="NORMAL",
                payload={
                    "product_code": product_code,
                    "client_data": client_data or {},
                },
            )
            for product_code in selected_products
        ]
        return await self._run_parallel(case_id, tasks)

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _dispatch_loop(self) -> None:
        """Watch the ProductOnboarding queue and batch-parallelise tasks."""
        queue = self._bus._queues.get(AgentID.PRODUCT_ONBOARDING)
        if queue is None:
            logger.error("[ParallelLauncher] No ProductOnboarding queue on bus")
            return

        logger.info("[ParallelLauncher] Parallel dispatch loop started")
        while True:
            # Block until at least one product task arrives.
            first = await queue.get()
            batch = [first]

            # Drain any tasks that arrived concurrently (same fan-out burst).
            await asyncio.sleep(0)  # yield to let sibling tasks land
            try:
                while True:
                    batch.append(queue.get_nowait())
            except asyncio.QueueEmpty:
                pass

            # Group by case so we can parallelise per-case independently.
            by_case: dict[UUID, list[TaskPacket]] = defaultdict(list)
            for pkt in batch:
                by_case[pkt.case_id].append(pkt)

            for case_id, pkts in by_case.items():
                asyncio.create_task(
                    self._run_parallel_and_ack(case_id, pkts, queue, len(pkts))
                )

    async def _run_parallel_and_ack(
        self,
        case_id: UUID,
        packets: list[TaskPacket],
        queue: asyncio.Queue,
        count: int,
    ) -> None:
        try:
            await self._run_parallel(case_id, packets)
        finally:
            for _ in range(count):
                queue.task_done()

    async def _run_parallel(
        self,
        case_id: UUID,
        packets: list[TaskPacket],
    ) -> list[TaskResponse]:
        """Instantiate one agent per product and run them with asyncio.gather."""
        agents: list[ProductOnboardingAgent] = []
        for _ in packets:
            agent = ProductOnboardingAgent()
            agent.attach_bus(self._bus)
            agents.append(agent)

        product_codes = [p.payload.get("product_code", "?") for p in packets]
        logger.info(
            f"[ParallelLauncher] Launching {len(packets)} product tracks in parallel "
            f"case={case_id} products={product_codes}"
        )

        await socket_emitter.progress_update(
            case_id,
            {
                "case_id": str(case_id),
                "event": "parallel_products_started",
                "products": product_codes,
            },
        )

        # Persist each product task as IN_PROGRESS before running, mirroring the
        # standard dispatch_loop so these tasks appear in the agent_tasks table.
        started_at = datetime.utcnow()
        for pkt in packets:
            await self._bus._save_task_in_progress(pkt, started_at)

        raw = await asyncio.gather(
            *[agent.timed_process(pkt) for agent, pkt in zip(agents, packets)],
            return_exceptions=True,
        )

        results: list[TaskResponse] = []
        any_critical_failure = False
        for pkt, product_code, outcome in zip(packets, product_codes, raw):
            if isinstance(outcome, Exception):
                logger.error(
                    f"[ParallelLauncher] {product_code} raised exception: {outcome}"
                )
                any_critical_failure = True
                failed = TaskResponse(
                    task_id=pkt.id,
                    from_agent=AgentID.PRODUCT_ONBOARDING,
                    status="FAILED",
                    errors=[str(outcome)],
                    duration_ms=0,
                )
                await self._bus._update_task_completed(pkt.id, failed)
            else:
                results.append(outcome)
                await self._bus._update_task_completed(pkt.id, outcome)
                logger.info(
                    f"[ParallelLauncher] {product_code} → {outcome.status} "
                    f"({outcome.duration_ms}ms)"
                )

        await socket_emitter.progress_update(
            case_id,
            {
                "case_id": str(case_id),
                "event": "parallel_products_complete",
                "products": product_codes,
                "results": [
                    {
                        "product_code": r.result.get("product_code"),
                        "status": r.result.get("status"),
                    }
                    for r in results
                ],
            },
        )

        # Once all product tracks have settled, advance the workflow.
        # A critical exception escalates; otherwise move to REVIEW so the
        # CollaborationAgent can open the multi-party review room.
        if packets:
            first = packets[0]
            next_stage = (
                OnboardingStage.ESCALATED if any_critical_failure else OnboardingStage.REVIEW
            )
            await self._bus.publish(TaskPacket(
                from_agent=AgentID.PRODUCT_ONBOARDING,
                to_agent=AgentID.ORCHESTRATOR,
                task_type=TaskType.ADVANCE_STAGE,
                case_id=first.case_id,
                client_id=first.client_id,
                priority="NORMAL",
                payload={
                    "to_stage": next_stage,
                    "product_codes": product_codes,
                    "all_tracks_done": True,
                },
            ))

        return results
