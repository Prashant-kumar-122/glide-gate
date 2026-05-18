from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from loguru import logger

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskResponse, TaskType

if TYPE_CHECKING:
    from app.agents.base.base_agent import BaseAgent


class AgentEventBus:
    """
    asyncio.Queue-based A2A message bus.

    Each registered agent gets its own FIFO queue. Tasks are routed by
    `to_agent`. The design mirrors Redis Streams semantics so the backend
    can be swapped to Redis without changing agent code: just replace
    `publish` / `next_task` with stream XADD / XREAD calls.
    """

    def __init__(self) -> None:
        self._queues: dict[AgentID, asyncio.Queue[TaskPacket]] = {}
        self._agents: dict[AgentID, BaseAgent] = {}
        self._subscribers: dict[TaskType, list[AgentID]] = defaultdict(list)

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.agent_id] = agent
        self._queues[agent.agent_id] = asyncio.Queue()
        agent.attach_bus(self)
        logger.debug(f"[EventBus] Registered {agent.agent_id}")

    def subscribe(self, agent_id: AgentID, *task_types: TaskType) -> None:
        for tt in task_types:
            if agent_id not in self._subscribers[tt]:
                self._subscribers[tt].append(agent_id)

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def publish(self, packet: TaskPacket) -> None:
        target = packet.to_agent
        if target not in self._queues:
            logger.warning(
                f"[EventBus] No queue for {target}; dropping task {packet.id}"
            )
            return
        await self._queues[target].put(packet)
        logger.debug(
            f"[EventBus] {packet.from_agent} → {target} "
            f"task_type={packet.task_type} id={packet.id}"
        )

    async def next_task(self, agent_id: AgentID) -> TaskPacket:
        return await self._queues[agent_id].get()

    def task_done(self, agent_id: AgentID) -> None:
        self._queues[agent_id].task_done()

    # ── DB persistence helpers ────────────────────────────────────────────────

    async def _save_task_in_progress(self, packet: TaskPacket, started_at: datetime) -> None:
        """Write an IN_PROGRESS AgentTask row when a task is dequeued."""
        from app.database import AsyncSessionLocal
        from app.models.agents import AgentTask as AgentTaskRow
        try:
            async with AsyncSessionLocal() as db:
                db.add(AgentTaskRow(
                    id=packet.id,
                    from_agent=str(packet.from_agent),
                    to_agent=str(packet.to_agent),
                    task_type=str(packet.task_type),
                    case_id=packet.case_id,
                    client_id=packet.client_id,
                    priority=packet.priority,
                    payload=packet.payload,
                    expected_schema=packet.expected_schema or "",
                    status="IN_PROGRESS",
                    result={},
                    errors=[],
                    created_at=packet.created_at,
                    started_at=started_at,
                ))
                await db.commit()
        except Exception as exc:
            logger.warning(f"[EventBus] Failed to persist task {packet.id} IN_PROGRESS: {exc}")

    async def _update_task_completed(self, task_id: UUID, response: TaskResponse) -> None:
        """Update an existing AgentTask row with final status, result, and duration."""
        from sqlalchemy import update
        from app.database import AsyncSessionLocal
        from app.models.agents import AgentTask as AgentTaskRow
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(AgentTaskRow)
                    .where(AgentTaskRow.id == task_id)
                    .values(
                        status=response.status,
                        result=response.result,
                        errors=response.errors or [],
                        duration_ms=response.duration_ms,
                        completed_at=datetime.utcnow(),
                    )
                )
                await db.commit()
        except Exception as exc:
            logger.warning(f"[EventBus] Failed to update task {task_id} completed: {exc}")

    # ── Dispatch loops ────────────────────────────────────────────────────────

    async def dispatch_loop(self, agent_id: AgentID) -> None:
        """Consume and process tasks for a single agent (runs as asyncio.Task)."""
        agent = self._agents[agent_id]
        queue = self._queues[agent_id]
        logger.info(f"[EventBus] Dispatch loop started: {agent_id}")
        while True:
            packet = await queue.get()
            started_at = datetime.utcnow()
            await self._save_task_in_progress(packet, started_at)
            try:
                response = await agent.timed_process(packet)
                logger.info(
                    f"[EventBus] {agent_id} {packet.task_type} → "
                    f"{response.status} ({response.duration_ms}ms)"
                )
            except Exception as exc:
                logger.error(f"[EventBus] Unhandled error in {agent_id}: {exc}")
                response = TaskResponse(
                    task_id=packet.id,
                    from_agent=agent_id,
                    status="FAILED",
                    result={},
                    errors=[str(exc)],
                    duration_ms=0,
                )
            finally:
                queue.task_done()
            await self._update_task_completed(packet.id, response)

    async def start_all(self) -> list[asyncio.Task]:
        """Start dispatch loops for every registered agent and return the tasks."""
        tasks = [
            asyncio.create_task(
                self.dispatch_loop(agent_id), name=f"bus-{agent_id}"
            )
            for agent_id in self._agents
        ]
        return tasks
