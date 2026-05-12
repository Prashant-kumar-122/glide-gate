from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any
from uuid import UUID

from loguru import logger

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskResponse

if TYPE_CHECKING:
    from app.agents.base.agent_event_bus import AgentEventBus


class BaseAgent(ABC):
    """Abstract base for all CADF agents."""

    agent_id: AgentID
    _bus: AgentEventBus | None = None

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.logger = logger.bind(agent=self.agent_id)

    def attach_bus(self, bus: AgentEventBus) -> None:
        self._bus = bus

    @property
    def bus(self) -> AgentEventBus:
        if self._bus is None:
            raise RuntimeError(f"Agent {self.agent_id} has no event bus attached")
        return self._bus

    @abstractmethod
    async def process(self, task: TaskPacket) -> TaskResponse:
        """Execute an incoming task and return a typed response."""
        ...

    async def send_task(self, packet: TaskPacket) -> None:
        await self.bus.publish(packet)

    async def timed_process(self, task: TaskPacket) -> TaskResponse:
        start = time.monotonic()
        try:
            response = await self.process(task)
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            self.logger.error(f"Task {task.id} ({task.task_type}) failed: {exc}")
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=[str(exc)],
                duration_ms=elapsed,
            )
        response.duration_ms = int((time.monotonic() - start) * 1000)
        return response

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} agent_id={self.agent_id}>"
