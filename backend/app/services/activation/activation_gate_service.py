"""ActivationGateService — first-to-complete product activation gate (Phase 4.6).

FR-GL-01/02/03 require that each product independently activates once its
activation criteria are met, without waiting for other products.  ADR-006
requires a strong-consistency criteria read (never from cache).

Policy evaluation is performed in-process as a Python function that mirrors
the OPA policy in policies/activation.rego.  For production deployments that
require an external OPA server, replace _evaluate_policy() with an OPA HTTP
call using the same input/output contract.

State machine:  PENDING → CRITERIA_MET → ACTIVATED
                                       └→ DECLINED
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


# ── Policy evaluation (mirrors policies/activation.rego) ──────────────────────


def _evaluate_policy(
    case_context: dict[str, Any],
    activation_criteria: dict[str, Any],
    track_status: str,
) -> tuple[bool, str | None, bool]:
    """Return (allow, decline_reason, is_adverse_action).

    allow               — True iff all criteria pass
    decline_reason      — human-readable reason when allow=False; None otherwise
    is_adverse_action   — True when the decline is credit-related (ECOA FR-AU-04)
    """
    # Pipeline must have completed successfully
    if track_status != "COMPLETE":
        return False, f"Product pipeline did not complete (status={track_status})", False

    extra: dict[str, Any] = case_context.get("extra") or case_context.get("shared_context") or {}

    # KYC must have passed (hard gate)
    kyc_status = extra.get("kyc_status", "PENDING")
    if kyc_status != "PASSED":
        is_credit = activation_criteria.get("is_credit_product", False)
        return False, f"KYC not passed (status={kyc_status})", bool(is_credit)

    # Fraud screening must not be flagged
    fraud_screened = extra.get("fraud_screened", "PENDING")
    if fraud_screened == "FLAGGED":
        return False, "Fraud screening flagged", False

    # Product-specific criteria from domain_products.activation_criteria
    if activation_criteria:
        min_risk_level = activation_criteria.get("min_risk_level")
        if min_risk_level:
            risk_map = {"low": 1, "medium": 2, "high": 3}
            client_risk = extra.get("kyc_risk_band", "low").lower()
            required_min = risk_map.get(min_risk_level.lower(), 1)
            actual = risk_map.get(client_risk, 1)
            if actual < required_min:
                is_credit = activation_criteria.get("is_credit_product", False)
                return (
                    False,
                    f"Risk level {client_risk!r} below minimum {min_risk_level!r}",
                    bool(is_credit),
                )

    return True, None, False


# ── ActivationGateService ─────────────────────────────────────────────────────


class ActivationGateService:
    """Evaluate and persist per-product activation decisions.

    Public API (called from _activation_gate_node in product_onboarding/graph.py):

        result = await service.evaluate(case_id, product_code, track_status)
        # result: {"activation_state": "ACTIVATED"|"DECLINED", "account_number": str|None,
        #          "decline_reason": str|None, "is_adverse_action": bool}
    """

    async def evaluate(
        self,
        case_id: UUID,
        product_code: str,
        track_status: str,
        domain_code: str = "wealth_management",
        extra_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate activation criteria and persist result to product_activation.

        Performs a strong-consistency DB read of the case context (ADR-006).
        Returns a dict with the final activation_state and account_number.

        The product_activation write and the decision_log write use separate DB
        sessions so that a decision_log failure (e.g. concurrent hash-chain
        serialization contention) never rolls back the activation state write.
        """
        from loguru import logger as _log

        from app.database import AsyncSessionLocal
        from app.models.activation import ProductActivation
        from app.models.cases import OnboardingCase
        from app.models.domain import Domain, DomainProduct
        from app.services.audit.audit_event_types import AuditEventType
        from app.services.audit.decision_log_service import (
            DecisionLogEntry,
            decision_log_service,
        )
        from sqlalchemy import select

        # ── Session 1: read context + evaluate policy + persist activation ────
        async with AsyncSessionLocal() as db:
            # Strong-consistency read of case context (ADR-006)
            case_row = await db.get(OnboardingCase, case_id)
            case_context: dict[str, Any] = {}
            if case_row:
                # shared_context stores the full LangGraph state dict; kyc_status lives
                # inside shared_context["extra"], not at the top level.
                _sc = case_row.shared_context or {}
                _db_extra = _sc.get("extra") or {}
                # Prefer caller-supplied extra_override (from Temporal state, always current)
                # over the DB snapshot, which may lag behind when persist_stage_activity
                # only writes current_stage/status and not the full extra bag.
                merged_extra = {**_db_extra, **(extra_override or {})}
                case_context = {
                    "extra": merged_extra,
                    "selected_products": case_row.selected_products or [],
                }

            # Load product activation criteria from domain_products
            activation_criteria: dict[str, Any] = {}
            domain_id = await db.scalar(
                select(Domain.id).where(Domain.domain_code == domain_code)
            )
            if domain_id:
                criteria_val = await db.scalar(
                    select(DomainProduct.activation_criteria).where(
                        DomainProduct.domain_id == domain_id,
                        DomainProduct.product_code == product_code,
                    )
                )
                if criteria_val:
                    activation_criteria = dict(criteria_val)

            # Evaluate policy (Python in-process, mirrors activation.rego)
            allowed, decline_reason, is_adverse_action = _evaluate_policy(
                case_context, activation_criteria, track_status
            )

            _log.info(
                f"activation_gate policy: case={case_id} product={product_code} "
                f"track={track_status} kyc={case_context.get('extra', {}).get('kyc_status')} "
                f"fraud={case_context.get('extra', {}).get('fraud_screened')} "
                f"allowed={allowed} reason={decline_reason!r}"
            )

            now = datetime.now(timezone.utc).replace(tzinfo=None)

            # Upsert product_activation row
            existing = await db.scalar(
                select(ProductActivation).where(
                    ProductActivation.case_id == case_id,
                    ProductActivation.product_code == product_code,
                )
            )
            if existing is None:
                existing = ProductActivation(
                    case_id=case_id,
                    product_code=product_code,
                    state="PENDING",
                )
                db.add(existing)

            account_number: str | None = None
            event_type: str

            if allowed:
                account_number = (
                    f"GG-{product_code[:3].upper()}-{str(_uuid.uuid4())[:8].upper()}"
                )
                existing.state = "ACTIVATED"
                existing.criteria_met_at = now
                existing.activated_at = now
                existing.account_number = account_number
                event_type = AuditEventType.PRODUCT_ACTIVATED
                is_regulatory_breach = False
            else:
                existing.state = "DECLINED"
                existing.declined_at = now
                existing.decline_reason = decline_reason
                existing.is_adverse_action = is_adverse_action
                if is_adverse_action:
                    existing.adverse_action_reason = decline_reason
                event_type = AuditEventType.PRODUCT_DECLINED
                is_regulatory_breach = is_adverse_action

            final_state = existing.state
            await db.commit()

        # ── Session 2 (separate): append decision_log — best-effort ──────────
        # Using a separate session so that hash-chain serialization contention
        # (the FOR UPDATE lock in _append_in_session) cannot roll back the
        # product_activation write that already committed above.
        try:
            await decision_log_service.append(
                DecisionLogEntry(
                    agent_id="activation_gate",
                    event_type=event_type,
                    case_id=case_id,
                    payload={
                        "product_code": product_code,
                        "track_status": track_status,
                        "activation_state": final_state,
                        "account_number": account_number,
                        "decline_reason": decline_reason,
                        "is_adverse_action": is_adverse_action,
                        "criteria_evaluated": activation_criteria,
                    },
                    is_compliance_event=True,
                    is_regulatory_breach=is_regulatory_breach,
                ),
                # No db= argument → service opens its own session+transaction
            )
        except Exception as _dl_exc:
            _log.error(
                f"activation_gate: decision_log append FAILED "
                f"case={case_id} product={product_code}: {_dl_exc!r}",
                exc_info=True,
            )

        return {
            "activation_state": final_state,
            "account_number": account_number,
            "decline_reason": decline_reason,
            "is_adverse_action": is_adverse_action,
        }


# Module-level singleton
activation_gate_service = ActivationGateService()
