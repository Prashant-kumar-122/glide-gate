from __future__ import annotations

import json
from typing import Any

from app.agents.skills.base_skill import BaseSkill
from app.services.llm import LLMMessage, LLMRequest, controls_applier, llm_fallback_chain

_SYSTEM = (
    "You are a data extraction assistant for a wealth management onboarding platform. "
    "Extract the requested fields from the provided text and return a JSON object. "
    "If a field is not present in the text, set its value to null. "
    "Return only valid JSON — no extra text."
)


class InformationExtractionSkill(BaseSkill):
    """Extract structured field values from unstructured text using an LLM."""

    skill_name = "information_extraction"

    async def _execute(
        self,
        *,
        text: str,
        fields: list[str],
        context: str = "",
    ) -> dict[str, Any]:
        field_list = "\n".join(f"- {f}" for f in fields)
        user_content = (
            f"{f'Context: {context}\n\n' if context else ''}"
            f"Text to extract from:\n{text}\n\n"
            f"Fields to extract:\n{field_list}\n\n"
            "Return a JSON object with exactly these keys."
        )
        request = LLMRequest(
            system_prompt=_SYSTEM,
            messages=[LLMMessage(role="user", content=user_content)],
            max_tokens=512,
        )
        response = await llm_fallback_chain.complete(controls_applier.apply(request))
        raw = _strip_fences(response.text)
        extracted: dict[str, Any] = json.loads(raw)
        return {"extracted": extracted, "provider": response.provider, "model": response.model}


def _strip_fences(text: str) -> str:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()
