from __future__ import annotations

import json
from typing import Any

from app.agents.base.a2a_types import OnboardingStage, OnboardingState
from app.agents.skills.base_skill import BaseSkill
from app.services.llm import LLMMessage, LLMRequest, controls_applier, llm_fallback_chain

_STAGE_LABELS: dict[str, str] = {
    OnboardingStage.INTAKE: "Getting Started",
    OnboardingStage.KYC: "Identity Verification",
    OnboardingStage.PARALLEL_PRODUCTS: "Account Setup",
    OnboardingStage.REVIEW: "Final Review",
    OnboardingStage.COMPLETE: "Complete",
    OnboardingStage.ESCALATED: "Under Review",
}

_STAGE_PROGRESS: dict[str, int] = {
    OnboardingStage.INTAKE: 10,
    OnboardingStage.KYC: 30,
    OnboardingStage.PARALLEL_PRODUCTS: 60,
    OnboardingStage.REVIEW: 85,
    OnboardingStage.COMPLETE: 100,
    OnboardingStage.ESCALATED: 50,
}

_SYSTEM = (
    "You are a helpful assistant for a wealth management onboarding platform. "
    "Produce a concise, client-friendly summary of the current onboarding status. "
    'Return a JSON object: {"summary": "<2-3 sentence summary>", '
    '"key_points": ["<point>", ...], "recommended_actions": ["<action>", ...]} '
    "Return only valid JSON."
)


class StatusSummarisationSkill(BaseSkill):
    """Summarise current onboarding state as a human-readable status update."""

    skill_name = "status_summarisation"

    async def _execute(
        self,
        *,
        state: OnboardingState | dict[str, Any],
        use_llm: bool = True,
    ) -> dict[str, Any]:
        if isinstance(state, dict):
            state = OnboardingState(**state)

        stage = str(state.stage)
        stage_label = _STAGE_LABELS.get(stage, stage)
        completion_percent = _STAGE_PROGRESS.get(stage, 0)
        docs_total = len(state.documents_required)
        docs_received = len(state.documents_received)

        base: dict[str, Any] = {
            "stage": stage,
            "stage_label": stage_label,
            "completion_percent": completion_percent,
            "kyc_status": state.kyc_status,
            "documents_received": docs_received,
            "documents_total": docs_total,
            "selected_products": state.selected_products,
            "escalated": stage == str(OnboardingStage.ESCALATED),
        }

        if not use_llm:
            base["summary"] = (
                f"Onboarding is at the '{stage_label}' stage ({completion_percent}% complete). "
                f"{docs_received}/{docs_total} documents received. KYC: {state.kyc_status}."
            )
            base["key_points"] = []
            base["recommended_actions"] = []
            return base

        context_payload = json.dumps(
            {
                "stage": stage_label,
                "progress": f"{completion_percent}%",
                "kyc_status": state.kyc_status,
                "documents": f"{docs_received}/{docs_total} received",
                "products": state.selected_products,
                "escalated": base["escalated"],
            },
            indent=2,
        )
        request = LLMRequest(
            system_prompt=_SYSTEM,
            messages=[LLMMessage(role="user", content=f"Current onboarding status:\n{context_payload}")],
            max_tokens=400,
        )
        try:
            response = await llm_fallback_chain.complete(controls_applier.apply(request))
            llm_result: dict[str, Any] = json.loads(_strip_fences(response.text))
            base.update(llm_result)
            base["provider"] = response.provider
        except Exception:
            base["summary"] = (
                f"Onboarding is at the '{stage_label}' stage ({completion_percent}% complete). "
                f"{docs_received}/{docs_total} documents received."
            )
            base["key_points"] = []
            base["recommended_actions"] = []
        return base


def _strip_fences(text: str) -> str:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()
