from __future__ import annotations

"""Shared store for admin validation prompt overrides.

Architecture: write-through cache.
- _prompt_overrides is the L1 in-memory cache (synchronous reads — zero latency).
- Every mutation also fires an async DB write so overrides survive server restarts.
- load_from_db() is called once at application startup to warm the cache from DB.

Both the admin router (validation_prompts.py) and validation_prompt_repository
import from here; the import direction is always toward this module.
"""

import asyncio
from typing import Any

from loguru import logger

# L1 in-memory cache — keyed by category ("identity", "financial", etc.)
_prompt_overrides: dict[str, dict[str, Any]] = {}


# ── Public synchronous read API (unchanged callers) ───────────────────────────

def get_prompt_override(category: str) -> dict[str, Any] | None:
    return _prompt_overrides.get(category)


def is_overridden(category: str) -> bool:
    return category in _prompt_overrides


# ── Public write API (updates cache + fires async DB write) ──────────────────

def set_prompt_override(category: str, goal: str, factors: list[str]) -> None:
    _prompt_overrides[category] = {"goal": goal, "factors": factors}
    _fire_db_save()


def reset_prompt_override(category: str) -> None:
    _prompt_overrides.pop(category, None)
    _fire_db_delete(category)


# ── Startup loader ────────────────────────────────────────────────────────────

async def load_from_db() -> None:
    """Warm the in-memory cache from DB. Called once at application startup."""
    from app.services.admin.admin_config_repository import (
        NAMESPACE_VALIDATION_PROMPTS,
        admin_config_repository,
    )
    data = await admin_config_repository.load(NAMESPACE_VALIDATION_PROMPTS)
    _prompt_overrides.clear()
    _prompt_overrides.update(data)
    logger.info(
        f"[PromptOverrideStore] Loaded {len(data)} override(s) from DB: "
        f"{list(data.keys()) or 'none'}"
    )


# ── Internal async helpers ────────────────────────────────────────────────────

def _fire_db_save() -> None:
    """Schedule a DB upsert of the full cache blob (fire-and-forget)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_persist_all())
    except RuntimeError:
        pass  # no running loop (e.g. during tests); skip DB write


def _fire_db_delete(category: str) -> None:
    """Schedule removal of a single category key from the DB blob."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_delete_one(category))
    except RuntimeError:
        pass


async def _persist_all() -> None:
    from app.services.admin.admin_config_repository import (
        NAMESPACE_VALIDATION_PROMPTS,
        admin_config_repository,
    )
    await admin_config_repository.save(NAMESPACE_VALIDATION_PROMPTS, dict(_prompt_overrides))


async def _delete_one(category: str) -> None:
    from app.services.admin.admin_config_repository import (
        NAMESPACE_VALIDATION_PROMPTS,
        admin_config_repository,
    )
    await admin_config_repository.delete_key(NAMESPACE_VALIDATION_PROMPTS, category)
