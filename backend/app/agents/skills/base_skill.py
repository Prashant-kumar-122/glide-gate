from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from loguru import logger

from app.database import AsyncSessionLocal
from app.models.agents import EventLog


class BaseSkill(ABC):
    """Abstract base for all CADF composable skills.

    Subclasses implement ``_execute(**kwargs)`` and set a unique ``skill_name``.
    ``invoke()`` wraps execution with timing and appends to ``event_logs``.
    """

    skill_name: str = "base_skill"

    async def invoke(
        self,
        agent_id: str,
        case_id: UUID | None = None,
        client_id: UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        start = time.monotonic()
        error: str | None = None
        result: dict[str, Any] = {}
        try:
            result = await self._execute(**kwargs)
        except Exception as exc:
            error = str(exc)
            logger.error(f"Skill {self.skill_name} raised: {exc}")
            result = {"error": error}
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            await self._log_invocation(agent_id, case_id, client_id, duration_ms, error)
        return result

    @abstractmethod
    async def _execute(self, **kwargs: Any) -> dict[str, Any]: ...

    async def _log_invocation(
        self,
        agent_id: str,
        case_id: UUID | None,
        client_id: UUID | None,
        duration_ms: int,
        error: str | None,
    ) -> None:
        try:
            async with AsyncSessionLocal() as session:
                log = EventLog(
                    case_id=case_id,
                    client_id=client_id,
                    agent_id=agent_id,
                    event_type="SKILL_INVOKED",
                    event_category="skill",
                    actor_id=agent_id,
                    payload={
                        "skill_name": self.skill_name,
                        "duration_ms": duration_ms,
                        "success": error is None,
                        "error": error,
                    },
                )
                session.add(log)
                await session.commit()
        except Exception as exc:
            logger.warning(f"Skill log write failed (non-fatal): {exc}")
