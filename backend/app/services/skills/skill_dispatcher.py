"""SkillDispatcher — loads domain_agent_skills bindings and dispatches to skill singletons.

No agent knows at code time which skill it calls; the binding is data.
Agents look up their skill bindings via get_binding(), then call invoke_skill().
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from app.agents.skills.base_skill import BaseSkill


def _registry() -> dict[str, "BaseSkill"]:
    """Lazy import to avoid circular imports at module load time."""
    from app.agents.skills import (
        clarification,
        decision_reasoning,
        escalation,
        information_extraction,
        product_suitability,
        status_summarisation,
    )
    return {
        "information_extraction": information_extraction,
        "decision_reasoning": decision_reasoning,
        "status_summarisation": status_summarisation,
        "clarification": clarification,
        "escalation": escalation,
        "product_suitability": product_suitability,
    }


class SkillDispatcher:
    """Dispatches skill invocations driven by domain_agent_skills DB rows."""

    async def get_binding(
        self,
        agent_id: str,
        skill_id: str,
        domain_code: str = "wealth_management",
    ) -> dict[str, Any] | None:
        """Return bound_parameters for (agent_id, skill_id), or None if not configured."""
        try:
            from app.database import AsyncSessionLocal
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                row = await session.execute(text(
                    """
                    SELECT s.bound_parameters
                    FROM domain_agent_skills s
                    JOIN domains d ON d.id = s.domain_id
                    WHERE d.domain_code = :domain_code
                      AND s.agent_id    = :agent_id
                      AND s.skill_id    = :skill_id
                    LIMIT 1
                    """
                ), {"domain_code": domain_code, "agent_id": agent_id, "skill_id": skill_id})
                result = row.fetchone()
                return dict(result[0]) if result and result[0] else {}
        except Exception as exc:
            logger.warning(f"SkillDispatcher.get_binding({agent_id!r}, {skill_id!r}) failed: {exc}")
            return None

    async def invoke_skill(
        self,
        skill_id: str,
        agent_id: str,
        domain_code: str = "wealth_management",
        **runtime_kwargs: Any,
    ) -> dict[str, Any]:
        """Invoke a skill, merging DB-configured bound_parameters with runtime kwargs.

        Runtime kwargs take precedence over bound_parameters so callers can override.
        """
        reg = _registry()
        skill = reg.get(skill_id)
        if skill is None:
            raise ValueError(
                f"Unknown skill_id {skill_id!r}. Available: {sorted(reg)}"
            )

        bound = await self.get_binding(agent_id, skill_id, domain_code) or {}
        merged = {**bound, **runtime_kwargs}
        return await skill.invoke(agent_id=agent_id, **merged)


skill_dispatcher = SkillDispatcher()
