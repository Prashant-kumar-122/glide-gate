from __future__ import annotations

"""In-memory repository for checkpoint rules with DB-backed persistence.

Architecture: write-through cache.
- _rules list is the L1 in-memory cache (synchronous reads — zero latency).
- Every mutation also fires an async DB write so custom rules survive server restarts.
- load_from_db() is called once at application startup to warm the cache from DB.
- On a clean first start (no DB row) the cache retains _DEFAULT_RULES unchanged.
- reset() restores the cache to _DEFAULT_RULES and clears the DB row so the next
  startup also loads defaults (matches the "undo all customisation" intent).
"""

import asyncio
import uuid

from loguru import logger

from app.agents.kyc_compliance.checkpoint_rule_engine import CheckpointRule, _DEFAULT_RULES

_BUILTIN_IDS: frozenset[str] = frozenset(r.rule_id for r in _DEFAULT_RULES)

# L1 in-memory cache — full list of active rules (builtin + custom)
_rules: list[CheckpointRule] = list(_DEFAULT_RULES)


# ── Public synchronous read API ───────────────────────────────────────────────

def get_all() -> list[CheckpointRule]:
    return list(_rules)


def get(rule_id: str) -> CheckpointRule | None:
    for r in _rules:
        if r.rule_id == rule_id:
            return r
    return None


def is_builtin(rule_id: str) -> bool:
    return rule_id in _BUILTIN_IDS


def make_rule_id() -> str:
    return f"CUSTOM_{uuid.uuid4().hex[:8].upper()}"


# ── Public write API (updates cache + fires async DB write) ──────────────────

def add(rule: CheckpointRule) -> CheckpointRule:
    if any(r.rule_id == rule.rule_id for r in _rules):
        raise ValueError(f"Rule with id '{rule.rule_id}' already exists")
    _rules.append(rule)
    _fire_db_save()
    return rule


def update(rule_id: str, updated: CheckpointRule) -> CheckpointRule:
    for i, r in enumerate(_rules):
        if r.rule_id == rule_id:
            _rules[i] = updated
            _fire_db_save()
            return updated
    raise KeyError(rule_id)


def remove(rule_id: str) -> None:
    global _rules
    if rule_id in _BUILTIN_IDS:
        raise ValueError(f"Cannot delete built-in rule '{rule_id}'")
    before = len(_rules)
    _rules = [r for r in _rules if r.rule_id != rule_id]
    if len(_rules) == before:
        raise KeyError(rule_id)
    _fire_db_save()


def reset() -> list[CheckpointRule]:
    global _rules
    _rules = list(_DEFAULT_RULES)
    _fire_db_clear()
    return list(_rules)


# ── Startup loader ────────────────────────────────────────────────────────────

async def load_from_db() -> None:
    """Warm the in-memory cache from DB. Called once at application startup.

    If no DB row exists (clean first start), _rules stays as _DEFAULT_RULES.
    If a DB row exists, the persisted rule list replaces the defaults.
    """
    from app.services.admin.admin_config_repository import (
        NAMESPACE_CHECKPOINT_RULES,
        admin_config_repository,
    )
    data = await admin_config_repository.load(NAMESPACE_CHECKPOINT_RULES)
    raw_rules = data.get("rules")
    if not raw_rules:
        logger.info("[CheckpointRuleRepo] No persisted rules found — using defaults")
        return
    try:
        loaded = [CheckpointRule.model_validate(r) for r in raw_rules]
        global _rules
        _rules = loaded
        custom = sum(1 for r in loaded if r.rule_id not in _BUILTIN_IDS)
        logger.info(
            f"[CheckpointRuleRepo] Loaded {len(loaded)} rule(s) from DB "
            f"({custom} custom)"
        )
    except Exception as exc:
        logger.warning(f"[CheckpointRuleRepo] Failed to deserialise rules from DB: {exc} — using defaults")


# ── Internal async helpers ────────────────────────────────────────────────────

def _fire_db_save() -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_persist_all())
    except RuntimeError:
        pass  # no running loop (e.g. during tests); skip DB write


def _fire_db_clear() -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_persist_clear())
    except RuntimeError:
        pass


async def _persist_all() -> None:
    from app.services.admin.admin_config_repository import (
        NAMESPACE_CHECKPOINT_RULES,
        admin_config_repository,
    )
    payload = {"rules": [r.model_dump() for r in _rules]}
    await admin_config_repository.save(NAMESPACE_CHECKPOINT_RULES, payload)


async def _persist_clear() -> None:
    from app.services.admin.admin_config_repository import (
        NAMESPACE_CHECKPOINT_RULES,
        admin_config_repository,
    )
    await admin_config_repository.clear(NAMESPACE_CHECKPOINT_RULES)
