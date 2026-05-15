from __future__ import annotations

from typing import Any

from app.config import settings
from app.services.llm.llm_provider import LLMRequest

# Single source of truth for all runtime LLM config overrides (set via admin API).
_active_overrides: dict[str, Any] = {}


class DeterministicControlsApplier:
    """
    Merges .env defaults with live admin overrides and stamps them onto
    an LLMRequest copy.  Covers the 5 deterministic control parameters:
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


def set_overrides(updates: dict[str, Any]) -> None:
    _active_overrides.update(updates)


def clear_overrides() -> None:
    _active_overrides.clear()


def get_all_overrides() -> dict[str, Any]:
    return dict(_active_overrides)


controls_applier = DeterministicControlsApplier()
