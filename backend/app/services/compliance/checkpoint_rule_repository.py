from __future__ import annotations

import uuid

from app.agents.kyc_compliance.checkpoint_rule_engine import CheckpointRule, _DEFAULT_RULES

_BUILTIN_IDS: frozenset[str] = frozenset(r.rule_id for r in _DEFAULT_RULES)

# In-memory store initialised with defaults; replaced by DB-backed store in a
# future phase if persistence across restarts is needed.
_rules: list[CheckpointRule] = list(_DEFAULT_RULES)


def get_all() -> list[CheckpointRule]:
    return list(_rules)


def get(rule_id: str) -> CheckpointRule | None:
    for r in _rules:
        if r.rule_id == rule_id:
            return r
    return None


def add(rule: CheckpointRule) -> CheckpointRule:
    if any(r.rule_id == rule.rule_id for r in _rules):
        raise ValueError(f"Rule with id '{rule.rule_id}' already exists")
    _rules.append(rule)
    return rule


def update(rule_id: str, updated: CheckpointRule) -> CheckpointRule:
    for i, r in enumerate(_rules):
        if r.rule_id == rule_id:
            _rules[i] = updated
            return updated
    raise KeyError(rule_id)


def remove(rule_id: str) -> None:
    if rule_id in _BUILTIN_IDS:
        raise ValueError(f"Cannot delete built-in rule '{rule_id}'")
    global _rules
    before = len(_rules)
    _rules = [r for r in _rules if r.rule_id != rule_id]
    if len(_rules) == before:
        raise KeyError(rule_id)


def reset() -> list[CheckpointRule]:
    global _rules
    _rules = list(_DEFAULT_RULES)
    return list(_rules)


def is_builtin(rule_id: str) -> bool:
    return rule_id in _BUILTIN_IDS


def make_rule_id() -> str:
    return f"CUSTOM_{uuid.uuid4().hex[:8].upper()}"
