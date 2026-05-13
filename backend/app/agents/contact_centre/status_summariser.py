from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CallSummary(BaseModel):
    case_id: str
    client_name: str
    current_stage: str
    kyc_status: str
    products: list[str]
    pending_actions: list[str]
    recommended_next_steps: list[str]
    escalation_flag: bool
    summary_text: str


_STAGE_LABELS: dict[str, str] = {
    "INTAKE": "initial information collection",
    "KYC": "identity and compliance verification",
    "PARALLEL_PRODUCTS": "product account setup",
    "REVIEW": "final review",
    "COMPLETE": "onboarding complete",
    "ESCALATED": "compliance escalation — awaiting human review",
}

_KYC_LABELS: dict[str, str] = {
    "PENDING": "identity check in progress",
    "PASSED": "identity verified",
    "FAILED": "identity check failed",
    "ESCALATED": "flagged for manual compliance review",
}


class StatusSummariser:
    """
    Generates human-readable call summaries for Contact Centre representatives.
    Operates without LLM when no client is available; AI-enhanced version
    is wired in STEP-27.
    """

    def summarise(
        self,
        case_id: str,
        client_data: dict[str, Any],
        onboarding_state: dict[str, Any],
    ) -> CallSummary:
        client_name: str = (
            client_data.get("full_name")
            or f"{client_data.get('first_name', '')} {client_data.get('last_name', '')}".strip()
            or "the client"
        )

        current_stage: str = onboarding_state.get("stage", "INTAKE")
        kyc_status: str = onboarding_state.get("kyc_status", "PENDING")
        products: list[str] = onboarding_state.get("selected_products", [])
        product_tracks: dict[str, Any] = onboarding_state.get("product_tracks", {})
        escalation_flag = current_stage == "ESCALATED" or kyc_status == "ESCALATED"

        stage_label = _STAGE_LABELS.get(current_stage, current_stage.lower().replace("_", " "))
        kyc_label = _KYC_LABELS.get(kyc_status, kyc_status.lower())

        pending_actions: list[str] = []
        recommended_next_steps: list[str] = []

        docs_required: list[str] = onboarding_state.get("documents_required", [])
        docs_received: list[str] = onboarding_state.get("documents_received", [])
        missing_docs = [d for d in docs_required if d not in docs_received]
        if missing_docs:
            pending_actions.append(f"Missing documents: {', '.join(missing_docs)}")
            recommended_next_steps.append(
                "Ask the client to upload the outstanding documents via the client portal."
            )

        if kyc_status == "FAILED":
            pending_actions.append("KYC verification failed — re-verification required.")
            recommended_next_steps.append(
                "Request the client provide a clearer copy of their identity document."
            )

        if escalation_flag and kyc_status != "ESCALATED":
            pending_actions.append("Case is pending compliance officer review.")
            recommended_next_steps.append(
                "Advise the client that a compliance review is underway and typical resolution is 1–2 business days."
            )

        for product_code, track in product_tracks.items():
            track_stage = track.get("stage", "PENDING") if isinstance(track, dict) else getattr(track, "stage", "PENDING")
            if track_stage not in ("COMPLETE",):
                pending_actions.append(f"{_format_product(product_code)} account setup in progress.")

        if current_stage == "COMPLETE":
            recommended_next_steps.append(
                "Congratulate the client — onboarding is complete and account(s) are active."
            )
        elif not recommended_next_steps:
            recommended_next_steps.append(
                "No immediate action required; monitor for incoming documents and system updates."
            )

        product_str = (
            " and ".join(_format_product(p) for p in products)
            if products else "no products selected yet"
        )

        summary_text = (
            f"{client_name} is currently in the {stage_label} stage of their GlideGate "
            f"onboarding journey. "
            f"They have applied for {product_str}. "
            f"KYC status: {kyc_label}. "
        )
        if pending_actions:
            summary_text += f"Pending items: {'; '.join(pending_actions)}. "
        if escalation_flag:
            summary_text += "This case has an active compliance escalation — handle with care. "

        return CallSummary(
            case_id=case_id,
            client_name=client_name,
            current_stage=current_stage,
            kyc_status=kyc_status,
            products=products,
            pending_actions=pending_actions,
            recommended_next_steps=recommended_next_steps,
            escalation_flag=escalation_flag,
            summary_text=summary_text.strip(),
        )


def _format_product(product_code: str) -> str:
    return {
        "cash_account": "Cash Account",
        "retirement_account": "Retirement Account",
    }.get(product_code, product_code.replace("_", " ").title())
