from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncGenerator
from uuid import UUID

from loguru import logger

from app.config import settings

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


class DemoModeService:
    """
    Intercepts LLM calls and agent decisions when DEMO_MODE=True (config).

    Provides three categories of pre-canned responses:
      - Conversation turns  → `stream_canned_turn(case_id)`
      - Document validation → `get_validation_findings(category)`
      - KYC results         → `get_kyc_result(case_id)` / `set_kyc_scenario(case_id, scenario)`

    The default KYC scenario is "passing". Set a case to "high_risk" to trigger
    the escalation path (Scenario B demo).
    """

    def __init__(self) -> None:
        self._conversation_turns: list[str] = []
        self._validation_findings: dict[str, dict[str, Any]] = {}
        self._kyc_fixtures: dict[str, dict[str, Any]] = {}
        # Per-case state
        self._case_turn_index: dict[str, int] = {}
        self._case_kyc_scenario: dict[str, str] = {}  # default: "passing"
        self._loaded = False

    # ── Feature gate ──────────────────────────────────────────────────────────

    def is_enabled(self) -> bool:
        return settings.DEMO_MODE

    # ── Fixture loading ───────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            raw = (_FIXTURES_DIR / "conversation_turns.json").read_text(encoding="utf-8")
            turns = json.loads(raw)
            self._conversation_turns = [t if isinstance(t, str) else t.get("content", "") for t in turns]
            logger.debug(f"DemoModeService: loaded {len(self._conversation_turns)} conversation turns")
        except Exception as exc:
            logger.warning(f"DemoModeService: failed to load conversation_turns.json: {exc}")

        try:
            raw = (_FIXTURES_DIR / "validation_findings.json").read_text(encoding="utf-8")
            self._validation_findings = json.loads(raw)
            logger.debug(f"DemoModeService: loaded validation findings for {list(self._validation_findings)}")
        except Exception as exc:
            logger.warning(f"DemoModeService: failed to load validation_findings.json: {exc}")

        try:
            raw = (_FIXTURES_DIR / "kyc_high_risk.json").read_text(encoding="utf-8")
            self._kyc_fixtures = json.loads(raw)
            logger.debug(f"DemoModeService: loaded KYC fixtures: {list(self._kyc_fixtures)}")
        except Exception as exc:
            logger.warning(f"DemoModeService: failed to load kyc_high_risk.json: {exc}")

        self._loaded = True

    # ── Conversation turns ────────────────────────────────────────────────────

    def peek_turn(self, case_id: UUID) -> str | None:
        """Return the next pre-canned turn text without advancing the index."""
        self._ensure_loaded()
        idx = self._case_turn_index.get(str(case_id), 0)
        if idx < len(self._conversation_turns):
            return self._conversation_turns[idx]
        return None

    def advance_turn(self, case_id: UUID) -> None:
        """Advance the turn counter for this case."""
        key = str(case_id)
        self._case_turn_index[key] = self._case_turn_index.get(key, 0) + 1

    def reset_case(self, case_id: UUID) -> None:
        """Reset turn counter and scenario for a case (useful for re-running demos)."""
        key = str(case_id)
        self._case_turn_index.pop(key, None)
        self._case_kyc_scenario.pop(key, None)

    async def stream_canned_turn(
        self,
        case_id: UUID,
        *,
        fallback: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        Stream the next pre-canned conversation turn for this case as SSE tokens.
        Advances the internal turn counter after yielding.
        Falls back to `fallback` text when all pre-scripted turns are exhausted.
        """
        from app.services.conversation.streaming_response_service import _sse

        self._ensure_loaded()
        text = self.peek_turn(case_id) or fallback or "Thank you. Let's continue."
        self.advance_turn(case_id)

        yield _sse({"type": "start"})
        for word in text.split():
            yield _sse({"type": "token", "token": word + " "})
            await asyncio.sleep(0.025)  # ~25 ms per word → realistic cadence
        yield _sse({"type": "end", "input_tokens": 0, "output_tokens": 0})

    # ── Document validation ───────────────────────────────────────────────────

    def get_validation_findings(self, category: str) -> dict[str, Any] | None:
        """
        Return pre-canned validation findings dict for the given document category.
        Shape: { overall_status, completeness_pct, findings: [FindingResult-compatible dicts] }
        """
        self._ensure_loaded()
        return self._validation_findings.get(category)

    # ── KYC results ───────────────────────────────────────────────────────────

    def set_kyc_scenario(self, case_id: UUID, scenario: str) -> None:
        """
        Pin a KYC scenario for a specific case.
        scenario: "passing" (default) | "high_risk"
        """
        valid = {"passing", "high_risk"}
        if scenario not in valid:
            raise ValueError(f"Unknown KYC scenario '{scenario}'. Must be one of {valid}.")
        self._case_kyc_scenario[str(case_id)] = scenario
        logger.info(f"DemoModeService: case {case_id} KYC scenario set to '{scenario}'")

    def get_kyc_scenario(self, case_id: UUID) -> str:
        return self._case_kyc_scenario.get(str(case_id), "passing")

    def get_kyc_result(self, case_id: UUID) -> dict[str, Any] | None:
        """
        Return the pre-canned KYC verification result for this case.
        Uses the scenario pinned via set_kyc_scenario(); defaults to "passing".
        """
        self._ensure_loaded()
        scenario = self.get_kyc_scenario(case_id)
        fixture = self._kyc_fixtures.get(scenario)
        if fixture is None:
            logger.warning(f"DemoModeService: no KYC fixture for scenario '{scenario}'")
            return None
        return dict(fixture)  # shallow copy so callers can't mutate the fixture

    # ── Admin status ──────────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Return a summary of the current demo mode state (used by admin endpoint)."""
        self._ensure_loaded()
        return {
            "demo_mode_enabled": self.is_enabled(),
            "conversation_turns_loaded": len(self._conversation_turns),
            "validation_categories_loaded": list(self._validation_findings.keys()),
            "kyc_scenarios_available": list(self._kyc_fixtures.keys()),
            "active_cases": {
                cid: {
                    "turn_index": self._case_turn_index.get(cid, 0),
                    "kyc_scenario": self._case_kyc_scenario.get(cid, "passing"),
                }
                for cid in set(self._case_turn_index) | set(self._case_kyc_scenario)
            },
        }


demo_mode_service = DemoModeService()
