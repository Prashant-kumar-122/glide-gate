from __future__ import annotations

import json
from typing import Any

from app.agents.skills.base_skill import BaseSkill
from app.services.llm import LLMMessage, LLMRequest, controls_applier, llm_fallback_chain

_SYSTEM = (
    "You are a decision-support assistant for a wealth management onboarding platform. "
    "Given context and a set of options, produce a structured decision with reasoning. "
    "Return a JSON object with this exact shape:\n"
    '{"decision": "<chosen option>", "reasoning": "<step-by-step reasoning>", '
    '"confidence": <0.0-1.0>, "key_factors": ["<factor>", ...]}\n'
    "Return only valid JSON."
)


class DecisionReasoningSkill(BaseSkill):
    """Produce a structured decision with chain-of-thought reasoning."""

    skill_name = "decision_reasoning"

    async def _execute(
        self,
        *,
        context: str,
        options: list[str],
        question: str = "What is the best course of action?",
        additional_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        extra = ""
        if additional_context:
            extra = "\nAdditional context:\n" + json.dumps(additional_context, indent=2)
        options_text = "\n".join(f"- {o}" for o in options)
        user_content = (
            f"Context:\n{context}{extra}\n\n"
            f"Question: {question}\n\n"
            f"Available options:\n{options_text}"
        )
        request = LLMRequest(
            system_prompt=_SYSTEM,
            messages=[LLMMessage(role="user", content=user_content)],
            max_tokens=600,
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
