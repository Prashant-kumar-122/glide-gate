from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskResponse


class BaseAgent(ABC):
    """Abstract base for all CADF agents."""

    agent_id: AgentID

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.logger = logger.bind(agent=self.agent_id)

    @abstractmethod
    async def process(self, task: TaskPacket) -> TaskResponse:
        """Execute an incoming task and return a typed response."""
        ...

    async def send_task(self, packet: TaskPacket) -> None:
        """Dispatch a task through Temporal (non-blocking — starts a DirectTaskWorkflow)."""
        import asyncio
        from app.services.orchestration.agent_orchestration_service import orchestration_service
        asyncio.create_task(orchestration_service.publish_task(packet))

    async def timed_process(self, task: TaskPacket) -> TaskResponse:
        import asyncio
        from app.services.audit.audit_log_service import audit_log_service

        start = time.monotonic()
        try:
            response = await self.process(task)
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            self.logger.error(f"Task {task.id} ({task.task_type}) failed: {exc}")
            response = TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=[str(exc)],
                duration_ms=elapsed,
            )
            asyncio.create_task(self._persist_agent_task(task, response, elapsed))
            asyncio.create_task(
                audit_log_service.log_agent_task_completed(
                    agent_id=str(self.agent_id),
                    task_type=str(task.task_type),
                    case_id=task.case_id,
                    client_id=task.client_id,
                    duration_ms=elapsed,
                    status="FAILED",
                )
            )
            return response
        response.duration_ms = int((time.monotonic() - start) * 1000)
        asyncio.create_task(self._persist_agent_task(task, response, response.duration_ms))
        asyncio.create_task(
            audit_log_service.log_agent_task_completed(
                agent_id=str(self.agent_id),
                task_type=str(task.task_type),
                case_id=task.case_id,
                client_id=task.client_id,
                duration_ms=response.duration_ms,
                status=response.status,
            )
        )
        return response

    async def _persist_agent_task(
        self, task: TaskPacket, response: TaskResponse, duration_ms: int
    ) -> None:
        from datetime import datetime, timezone
        from app.database import AsyncSessionLocal
        from app.models.agents import AgentTask

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            async with AsyncSessionLocal() as db:
                db.add(AgentTask(
                    id=task.id,
                    from_agent=str(task.from_agent),
                    to_agent=str(task.to_agent),
                    task_type=str(task.task_type),
                    case_id=task.case_id,
                    client_id=task.client_id,
                    priority=task.priority,
                    payload=task.payload,
                    expected_schema=task.expected_schema or None,
                    status=response.status,
                    result=response.result,
                    errors=response.errors or [],
                    duration_ms=duration_ms,
                    ttl=task.ttl,
                    started_at=now,
                    completed_at=now,
                ))
                await db.commit()
        except Exception as exc:
            self.logger.warning(f"AgentTask persist failed task={task.id}: {exc}")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} agent_id={self.agent_id}>"
