"""LangGraph StateGraph for the Fraud Screening agent (Phase 4.6).

Runs concurrently with KYC (parallel Temporal Activities in _handle_kyc).

Scoring:
  - Device fingerprint velocity  — simulated account-creation velocity check
  - Synthetic-identity signals   — simulated name/SSN inconsistency check
  - Document tamper detection    — simulated image-forensics check

Each score is in [0, 1] where high = suspicious.  Any score above 0.85
triggers a FLAGGED result.

On FLAGGED:
  - Sets extra["fraud_screened"] = "FLAGGED"
  - Sets extra["escalation_reason"] = "Fraud screening flagged"
  - Sets next_stage = "ESCALATED"
  - Writes FRAUD_FLAGGED to decision_log (is_compliance_event=True)

On CLEARED:
  - Sets extra["fraud_screened"] = "CLEARED"
  - Writes FRAUD_CLEARED to decision_log

When activation.rego (or _evaluate_policy) evaluates activation criteria,
fraud_screened == "FLAGGED" is a hard blocking condition (same as KYC failure).
"""
from __future__ import annotations

import asyncio
import random
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base.a2a_types import OnboardingStateDict

# Threshold above which any score triggers a FLAGGED result.
_FRAUD_FLAG_THRESHOLD = 0.85


async def _fraud_screening_node(state: OnboardingStateDict) -> OnboardingStateDict:
    """Run three simulated fraud-signal checks and set extra['fraud_screened']."""
    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")

    # Simulate latency for three independent checks
    await asyncio.sleep(random.uniform(0.4, 1.2))

    # Seed with the case_id so results are reproducible per case — eliminates
    # the situation where a retry or re-run of the same case flips from CLEARED
    # to FLAGGED due to different random seeds.
    # Known test clients (client_id starts with "d0000000") always CLEAR so
    # that seeded dev data never burns into an escalation.
    _rng = random.Random(case_id_str)
    _is_test_client = client_id_str.startswith("d0000000")

    if _is_test_client:
        velocity_score = _rng.uniform(0.0, 0.6)
        synthetic_score = _rng.uniform(0.0, 0.6)
        tamper_score = _rng.uniform(0.0, 0.6)
    else:
        velocity_score = _rng.uniform(0.0, 1.0)
        synthetic_score = _rng.uniform(0.0, 1.0)
        tamper_score = _rng.uniform(0.0, 1.0)

    is_flagged = (
        velocity_score > _FRAUD_FLAG_THRESHOLD
        or synthetic_score > _FRAUD_FLAG_THRESHOLD
        or tamper_score > _FRAUD_FLAG_THRESHOLD
    )
    fraud_screened = "FLAGGED" if is_flagged else "CLEARED"

    payload: dict[str, Any] = {
        "fraud_screened": fraud_screened,
        "velocity_score": round(velocity_score, 3),
        "synthetic_score": round(synthetic_score, 3),
        "tamper_score": round(tamper_score, 3),
        "threshold": _FRAUD_FLAG_THRESHOLD,
    }

    # Write to decision_log
    try:
        from uuid import UUID
        from app.services.audit.audit_event_types import AuditEventType
        from app.services.audit.decision_log_service import DecisionLogEntry, decision_log_service

        event_type = AuditEventType.FRAUD_FLAGGED if is_flagged else AuditEventType.FRAUD_CLEARED
        await decision_log_service.append(
            DecisionLogEntry(
                agent_id="fraud_screening",
                event_type=event_type,
                case_id=UUID(case_id_str) if case_id_str else None,
                client_id=UUID(client_id_str) if client_id_str else None,
                payload=payload,
                is_compliance_event=True,
                is_regulatory_breach=False,
            )
        )
    except Exception as exc:
        from loguru import logger as _log
        _log.warning(f"fraud_screening decision_log write failed case={case_id_str}: {exc}")

    extra = dict(state.get("extra") or {})
    extra["fraud_screened"] = fraud_screened
    new_state: OnboardingStateDict = {**state, "extra": extra}

    if is_flagged:
        extra["escalation_reason"] = "Fraud screening flagged"
        new_state = {**new_state, "extra": extra, "next_stage": "ESCALATED"}

        # Emit socket event so the frontend can react immediately
        try:
            from uuid import UUID
            from app.websocket.socket_emitter import socket_emitter
            await socket_emitter.agent_message(UUID(case_id_str), {
                "from_agent": "fraud_screening",
                "to_agent": "orchestrator",
                "task_type": "fraud_flagged",
                "status": "FLAGGED",
            })
        except Exception:
            pass

    return new_state


def build_fraud_screening_graph() -> Any:
    graph: StateGraph = StateGraph(OnboardingStateDict)
    graph.add_node("fraud_screening", _fraud_screening_node)
    graph.add_edge("fraud_screening", END)
    graph.set_entry_point("fraud_screening")
    return graph.compile()
