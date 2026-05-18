"""Seed admin_config table — initialise all three namespace rows.

Creates one row per namespace with an empty config blob so:
  - The admin_config table is never empty after a fresh install.
  - The startup loaders (load_from_db) find existing rows and log cleanly.
  - All three admin config areas start with their in-code defaults active
    (no overrides), which is the correct initial state.

Namespaces seeded:
  validation_prompts  →  {}   (file-based defaults from prompts/validation_defaults/)
  llm_config          →  {}   (settings from .env)
  checkpoint_rules    →  {}   (_DEFAULT_RULES from checkpoint_rule_engine.py)
"""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.admin_config import AdminConfig
from app.services.admin.admin_config_repository import (
    NAMESPACE_CHECKPOINT_RULES,
    NAMESPACE_LLM_CONFIG,
    NAMESPACE_VALIDATION_PROMPTS,
)

_NAMESPACES = [
    NAMESPACE_VALIDATION_PROMPTS,
    NAMESPACE_LLM_CONFIG,
    NAMESPACE_CHECKPOINT_RULES,
]


async def seed(session: AsyncSession) -> None:
    for ns in _NAMESPACES:
        existing = await session.get(AdminConfig, ns)
        if existing is not None:
            print(f"  skip  admin_config[{ns}] (already exists)")
            continue
        session.add(AdminConfig(namespace=ns, config={}))
        print(f"  seed  admin_config[{ns}]")

    await session.commit()
    print("  Admin config namespaces initialised.")


if __name__ == "__main__":
    async def main() -> None:
        async with AsyncSessionLocal() as session:
            await seed(session)

    asyncio.run(main())
