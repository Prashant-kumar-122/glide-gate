from __future__ import annotations

import json
from typing import Any

from app.agents.skills.base_skill import BaseSkill
from app.services.llm import LLMMessage, LLMRequest, controls_applier, llm_fallback_chain

_SYSTEM = (
    "You are a client onboarding assistant for a wealth management firm. "
    "Generate targeted, professional clarification questions for missing or ambiguous data. "
    'Return a JSON object: {"questions": [{"field": "<field_name>", '
    '"question": "<client-friendly question>", "rationale": "<why this field matters>"}, ...]} '
    "Return only valid JSON. Generate at most 5 questions, prioritising the most important gaps."
)


class ClarificationSkill(BaseSkill):
    """Generate targeted clarification questions for missing or ambiguous client data."""

    skill_name = "clarification"

    async def _execute(
        self,
        *,
        collected_data: dict[str, Any],
        missing_fields: list[str],
        ambiguous_fields: list[dict[str, Any]] | None = None,
        context: str = "",
    ) -> dict[str, Any]:
        ambiguous_text = ""
        if ambiguous_fields:
            ambiguous_text = "\nAmbiguous fields:\n" + json.dumps(ambiguous_fields, indent=2)
        user_content = (
            f"{f'Context: {context}\n\n' if context else ''}"
            f"Already collected:\n{json.dumps(collected_data, indent=2)}\n\n"
            f"Missing fields: {', '.join(missing_fields)}"
            f"{ambiguous_text}\n\n"
            "Generate professional clarification questions."
        )
        request = LLMRequest(
            system_prompt=_SYSTEM,
            messages=[LLMMessage(role="user", content=user_content)],
            max_tokens=500,
        )
        response = await llm_fallback_chain.complete(controls_applier.apply(request))
        result: dict[str, Any] = json.loads(_strip_fences(response.text))
        result["provider"] = response.provider
        result["model"] = response.model
        return result


def _strip_fences(text: str) -> str:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()
