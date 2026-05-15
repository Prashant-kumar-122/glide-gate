from __future__ import annotations

import json
from typing import Any

from app.agents.skills.base_skill import BaseSkill
from app.services.llm import LLMMessage, LLMRequest, controls_applier, llm_fallback_chain

_SYSTEM = (
    "You are a compliance risk officer for a wealth management firm. "
    "Assess whether the current onboarding case warrants escalation to a human reviewer. "
    'Return a JSON object: {"should_escalate": <true|false>, '
    '"severity": "LOW"|"MEDIUM"|"HIGH"|"CRITICAL", "reason": "<concise reason>", '
    '"risk_factors": ["<factor>", ...], '
    '"recommended_action": "APPROVE"|"ESCALATE"|"REQUEST_MORE_INFO"|"REJECT"} '
    "Return only valid JSON. Err on the side of caution for high-risk indicators."
)


class EscalationSkill(BaseSkill):
    """Assess whether escalation to human review is warranted based on risk indicators."""

    skill_name = "escalation"

    async def _execute(
        self,
        *,
        risk_score: float,
        risk_band: str,
        kyc_flags: list[str] | None = None,
        client_profile: dict[str, Any] | None = None,
        escalation_threshold: float = 0.7,
    ) -> dict[str, Any]:
        flags = kyc_flags or []

        # Heuristic fast-path for scores at or above threshold
        if risk_score >= escalation_threshold:
            heuristic: dict[str, Any] = {
                "should_escalate": True,
                "severity": "CRITICAL" if risk_score >= 0.9 else "HIGH",
                "reason": (
                    f"Composite risk score {risk_score:.2f} exceeds escalation "
                    f"threshold {escalation_threshold}."
                ),
                "risk_factors": flags,
                "recommended_action": "ESCALATE",
            }
            if client_profile:
                return await self._llm_assess(risk_score, risk_band, flags, client_profile, heuristic)
            return heuristic

        # Below threshold — LLM assessment if profile is available
        if client_profile:
            return await self._llm_assess(risk_score, risk_band, flags, client_profile, None)

        return {
            "should_escalate": False,
            "severity": "LOW",
            "reason": f"Risk score {risk_score:.2f} is within acceptable limits.",
            "risk_factors": [],
            "recommended_action": "APPROVE",
        }

    async def _llm_assess(
        self,
        risk_score: float,
        risk_band: str,
        kyc_flags: list[str],
        client_profile: dict[str, Any],
        heuristic_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        context = json.dumps(
            {
                "risk_score": risk_score,
                "risk_band": risk_band,
                "kyc_flags": kyc_flags,
                "client_profile_summary": client_profile,
            },
            indent=2,
        )
        hint = (
            f"\nInitial heuristic assessment: {json.dumps(heuristic_result)}"
            if heuristic_result
            else ""
        )
        request = LLMRequest(
            system_prompt=_SYSTEM,
            messages=[LLMMessage(role="user", content=f"Case assessment:\n{context}{hint}")],
            max_tokens=400,
        )
        try:
            response = await llm_fallback_chain.complete(controls_applier.apply(request))
            result: dict[str, Any] = json.loads(_strip_fences(response.text))
            result["provider"] = response.provider
            return result
        except Exception:
            if heuristic_result:
                return heuristic_result
            return {
                "should_escalate": False,
                "severity": "LOW",
                "reason": "LLM assessment unavailable; heuristic used.",
                "risk_factors": kyc_flags,
                "recommended_action": "APPROVE",
            }


def _strip_fences(text: str) -> str:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()
