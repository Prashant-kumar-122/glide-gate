from __future__ import annotations

"""Shared in-memory store for admin validation prompt overrides.

Both the admin router (validation_prompts.py) and the validation
prompt repository import from here so the router never needs to be
imported from a service (inverted direction).
"""

from typing import Any

# Keyed by category name ("identity", "financial", etc.)
_prompt_overrides: dict[str, dict[str, Any]] = {}


def set_prompt_override(category: str, goal: str, factors: list[str]) -> None:
    _prompt_overrides[category] = {"goal": goal, "factors": factors}


def get_prompt_override(category: str) -> dict[str, Any] | None:
    return _prompt_overrides.get(category)


def reset_prompt_override(category: str) -> None:
    _prompt_overrides.pop(category, None)


def is_overridden(category: str) -> bool:
    return category in _prompt_overrides
