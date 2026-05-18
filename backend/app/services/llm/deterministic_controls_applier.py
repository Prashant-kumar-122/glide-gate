from __future__ import annotations

"""Runtime LLM configuration overrides set via the admin API.

Architecture: write-through cache.
- _active_overrides is the L1 in-memory cache (synchronous reads — zero latency).
- Every mutation also fires an async DB write so settings survive server restarts.
- load_from_db() is called once at application startup to warm the cache from DB.
"""

import asyncio
from typing import Any

from loguru import logger

from app.config import settings
from app.services.llm.llm_provider import LLMRequest

# L1 in-memory cache — keyed by config param name
_active_overrides: dict[str, Any] = {}


class DeterministicControlsApplier:
    """
    Merges .env defaults with live admin overrides and stamps them onto
    an LLMRequest copy. Covers 5 deterministic control parameters:
    temperature, top_p, seed, frequency_penalty, presence_penalty.
    """

    def get_effective_params(self) -> dict[str, Any]:
        return {
            "temperature": _active_overrides.get("temperature", settings.LLM_TEMPERATURE),
            "top_p": _active_overrides.get("top_p", settings.LLM_TOP_P),
            "seed": _active_overrides.get("seed", settings.LLM_SEED),
            "frequency_penalty": _active_overrides.get(
                "frequency_penalty", settings.LLM_FREQUENCY_PENALTY
            ),
            "presence_penalty": _active_overrides.get(
                "presence_penalty", settings.LLM_PRESENCE_PENALTY
            ),
        }

    def apply(self, request: LLMRequest) -> LLMRequest:
        """Return a copy of *request* with effective deterministic controls stamped in."""
        return request.model_copy(update=self.get_effective_params())


# ── Public write API (updates cache + fires async DB write) ──────────────────

def set_overrides(updates: dict[str, Any]) -> None:
    _active_overrides.update(updates)
    _fire_db_patch(updates)


def clear_overrides() -> None:
    _active_overrides.clear()
    _fire_db_clear()


def get_all_overrides() -> dict[str, Any]:
    return dict(_active_overrides)


# ── Startup loader ────────────────────────────────────────────────────────────

async def load_from_db() -> None:
    """Warm the in-memory cache from DB. Called once at application startup."""
    from app.services.admin.admin_config_repository import (
        NAMESPACE_LLM_CONFIG,
        admin_config_repository,
    )
    data = await admin_config_repository.load(NAMESPACE_LLM_CONFIG)
    _active_overrides.clear()
    _active_overrides.update(data)
    logger.info(
        f"[DeterministicControls] Loaded {len(data)} override(s) from DB: "
        f"{list(data.keys()) or 'none'}"
    )


# ── Internal async helpers ────────────────────────────────────────────────────

def _fire_db_patch(updates: dict[str, Any]) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_persist_patch(updates))
    except RuntimeError:
        pass


def _fire_db_clear() -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_persist_clear())
    except RuntimeError:
        pass


async def _persist_patch(updates: dict[str, Any]) -> None:
    from app.services.admin.admin_config_repository import (
        NAMESPACE_LLM_CONFIG,
        admin_config_repository,
    )
    await admin_config_repository.patch(NAMESPACE_LLM_CONFIG, updates)


async def _persist_clear() -> None:
    from app.services.admin.admin_config_repository import (
        NAMESPACE_LLM_CONFIG,
        admin_config_repository,
    )
    await admin_config_repository.clear(NAMESPACE_LLM_CONFIG)


controls_applier = DeterministicControlsApplier()
