"""DomainPromptStore — read-through cache for domain_agent_prompts table.

Skills and agents call get() to retrieve their system prompt from the domain
configuration, falling back to hardcoded constants when no row exists.
The admin portal (Phase 9) will write to domain_agent_prompts, and clear()
should be called to invalidate the cache after a write.
"""
from __future__ import annotations

from loguru import logger


class DomainPromptStore:
    """Lazy, per-process cache for domain-scoped agent system prompts."""

    def __init__(self) -> None:
        # (domain_code, agent_id, prompt_role) → prompt_text | None
        self._cache: dict[tuple[str, str, str], str | None] = {}

    async def get(
        self,
        domain_code: str,
        agent_id: str,
        prompt_role: str,
    ) -> str | None:
        """Return the configured prompt_text, or None to use the hardcoded default."""
        key = (domain_code, agent_id, prompt_role)
        if key in self._cache:
            return self._cache[key]

        try:
            from app.database import AsyncSessionLocal
            from sqlalchemy import text

            async with AsyncSessionLocal() as session:
                result = await session.scalar(text(
                    """
                    SELECT p.prompt_text
                    FROM domain_agent_prompts p
                    JOIN domains d ON d.id = p.domain_id
                    WHERE d.domain_code = :domain_code
                      AND p.agent_id    = :agent_id
                      AND p.prompt_role = :prompt_role
                    LIMIT 1
                    """
                ), {"domain_code": domain_code, "agent_id": agent_id, "prompt_role": prompt_role})

            value: str | None = str(result) if result else None
            self._cache[key] = value
            return value

        except Exception as exc:
            logger.warning(
                f"DomainPromptStore.get({domain_code!r}, {agent_id!r}, {prompt_role!r}) "
                f"failed: {exc}"
            )
            return None

    def invalidate(self, domain_code: str, agent_id: str, prompt_role: str) -> None:
        self._cache.pop((domain_code, agent_id, prompt_role), None)

    def clear(self) -> None:
        self._cache.clear()


domain_prompt_store = DomainPromptStore()
