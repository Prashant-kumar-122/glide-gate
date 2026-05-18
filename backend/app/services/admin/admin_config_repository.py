from __future__ import annotations

"""DB-backed persistence for admin configuration namespaces.

Callers treat this as a thin async layer over the admin_config table.
The two consumers (prompt_override_store and deterministic_controls_applier)
maintain their own in-memory caches and call this repository only on writes
and at startup.
"""

from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.admin_config import AdminConfig

# Known namespaces — add here if new admin config areas are introduced
NAMESPACE_VALIDATION_PROMPTS = "validation_prompts"
NAMESPACE_LLM_CONFIG = "llm_config"
NAMESPACE_CHECKPOINT_RULES = "checkpoint_rules"


class AdminConfigRepository:

    async def load(self, namespace: str) -> dict[str, Any]:
        """Return the stored config blob for *namespace*, or {} if not yet persisted."""
        try:
            async with AsyncSessionLocal() as db:
                row = await db.get(AdminConfig, namespace)
                return dict(row.config) if row else {}
        except Exception as exc:
            logger.warning(f"[AdminConfig] Failed to load namespace '{namespace}': {exc}")
            return {}

    async def save(self, namespace: str, config: dict[str, Any]) -> None:
        """Upsert the full config blob for *namespace*."""
        try:
            async with AsyncSessionLocal() as db:
                row = await db.get(AdminConfig, namespace)
                if row:
                    row.config = config
                    row.updated_at = datetime.utcnow()
                else:
                    db.add(AdminConfig(namespace=namespace, config=config))
                await db.commit()
        except Exception as exc:
            logger.warning(f"[AdminConfig] Failed to save namespace '{namespace}': {exc}")

    async def patch(self, namespace: str, updates: dict[str, Any]) -> None:
        """Merge *updates* into the stored blob for *namespace* (partial update)."""
        try:
            async with AsyncSessionLocal() as db:
                row = await db.get(AdminConfig, namespace)
                if row:
                    merged = dict(row.config)
                    merged.update(updates)
                    row.config = merged
                    row.updated_at = datetime.utcnow()
                else:
                    db.add(AdminConfig(namespace=namespace, config=updates))
                await db.commit()
        except Exception as exc:
            logger.warning(f"[AdminConfig] Failed to patch namespace '{namespace}': {exc}")

    async def delete_key(self, namespace: str, key: str) -> None:
        """Remove a single key from the stored blob, leaving other keys intact."""
        try:
            async with AsyncSessionLocal() as db:
                row = await db.get(AdminConfig, namespace)
                if row and key in row.config:
                    updated = {k: v for k, v in row.config.items() if k != key}
                    row.config = updated
                    row.updated_at = datetime.utcnow()
                    await db.commit()
        except Exception as exc:
            logger.warning(
                f"[AdminConfig] Failed to delete key '{key}' from namespace '{namespace}': {exc}"
            )

    async def clear(self, namespace: str) -> None:
        """Wipe all overrides for *namespace* (reset to defaults)."""
        try:
            async with AsyncSessionLocal() as db:
                row = await db.get(AdminConfig, namespace)
                if row:
                    row.config = {}
                    row.updated_at = datetime.utcnow()
                    await db.commit()
        except Exception as exc:
            logger.warning(f"[AdminConfig] Failed to clear namespace '{namespace}': {exc}")


admin_config_repository = AdminConfigRepository()
