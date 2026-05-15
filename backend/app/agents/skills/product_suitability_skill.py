from __future__ import annotations

import json
from typing import Any

from app.agents.skills.base_skill import BaseSkill
from app.services.llm import LLMMessage, LLMRequest, controls_applier, llm_fallback_chain

_SYSTEM = (
    "You are a product suitability analyst for a wealth management firm. "
    "Assess whether a financial product is suitable for the given client profile. "
    'Return a JSON object: {"suitable": <true|false>, "score": <0.0-1.0>, '
    '"reasoning": "<concise suitability reasoning>", "concerns": ["<concern>", ...], '
    '"conditions": ["<condition if conditionally suitable>", ...]} '
    "Return only valid JSON. Consider risk tolerance, investment horizon, income, and age."
)

_RISK_ORDER = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]


class ProductSuitabilitySkill(BaseSkill):
    """Assess whether a financial product is suitable for a client profile."""

    skill_name = "product_suitability"

    async def _execute(
        self,
        *,
        product_code: str,
        product_config: dict[str, Any],
        client_profile: dict[str, Any],
    ) -> dict[str, Any]:
        user_content = (
            f"Product: {product_code}\n"
            f"Product configuration:\n{json.dumps(product_config, indent=2)}\n\n"
            f"Client profile:\n{json.dumps(client_profile, indent=2)}"
        )
        request = LLMRequest(
            system_prompt=_SYSTEM,
            messages=[LLMMessage(role="user", content=user_content)],
            max_tokens=500,
        )
        try:
            response = await llm_fallback_chain.complete(controls_applier.apply(request))
            result: dict[str, Any] = json.loads(_strip_fences(response.text))
            result["provider"] = response.provider
            result["model"] = response.model
            return result
        except Exception:
            return _heuristic_suitability(product_config, client_profile)


def _heuristic_suitability(
    product_config: dict[str, Any],
    client_profile: dict[str, Any],
) -> dict[str, Any]:
    client_risk = client_profile.get("risk_tolerance", "MEDIUM").upper()
    product_risk = product_config.get("risk_level", "MEDIUM").upper()
    client_idx = _RISK_ORDER.index(client_risk) if client_risk in _RISK_ORDER else 1
    product_idx = _RISK_ORDER.index(product_risk) if product_risk in _RISK_ORDER else 1
    suitable = client_idx >= product_idx
    return {
        "suitable": suitable,
        "score": 0.7 if suitable else 0.3,
        "reasoning": "Heuristic: client risk tolerance vs product risk level alignment.",
        "concerns": [] if suitable else ["Client risk tolerance below product risk level"],
        "conditions": [],
    }


def _strip_fences(text: str) -> str:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()
