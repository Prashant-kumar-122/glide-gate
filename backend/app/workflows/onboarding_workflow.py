"""Temporal OnboardingWorkflow + all Temporal Activities (Phase 0.5 / Phase 3 / Phase 5).

Architecture:
  - OnboardingWorkflow (@workflow.defn) owns the stage-level FSM.
  - Each stage is handled by one or more @activity.defn functions that invoke
    the corresponding agent's LangGraph graph.
  - Human-interaction stages (INTAKE, REVIEW, SALES_REVIEW) use
    workflow.wait_condition() + a signal handler so Temporal durably resumes
    after a crash without re-running completed activities.
  - PARALLEL_PRODUCTS launches one child workflow per product via
    workflow.execute_child_workflow().
  - The workflow ID is deterministic: f"onboarding-{case_id}" so any service
    with a case_id can Signal or Query the running workflow.

Phase 3 additions:
  - load_domain_definition_activity: loads DomainDefinition from DB at workflow
    start; result is stored in Temporal history so replays are deterministic.
  - StageDispatcher: maps stage_code → Temporal activity name via
    DomainDefinition.task_routing.  Replaces the hardcoded if/elif routing from
    orchestrator_agent.py.

Phase 5 additions:
  - SLAHook.on_stage_entered() stub replaced by _start_sla_timer() method.
  - start_sla_tracking_activity: resolves domain_stage_slas config, writes
    case_sla_tracking row, returns config dict (or None if not configured).
  - pause_sla_tracking_activity / resume_sla_tracking_activity: clock-pause
    support for human-pending stages with pause_on_human_review=True.
  - send_sla_warning_activity / trigger_sla_breach_activity: fire SLA events,
    write to decision_log (breach sets is_regulatory_breach=True).
  - _watch_sla(): async Temporal coroutine started as asyncio.create_task()
    inside each stage handler; cancelled on stage exit via finally block.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from app.agents.base.a2a_types import (
    HumanReviewSignal,
    OnboardingStage,
    OnboardingStateDict,
    OnboardingWorkflowInput,
    OnboardingWorkflowResult,
    StageAdvanceSignal,
)
from app.services.orchestration.stage_dispatcher import StageDispatcher

_NO_RETRY = RetryPolicy(maximum_attempts=1)
_STANDARD_RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=5))

# ── Activities ────────────────────────────────────────────────────────────────


@activity.defn(name="load_domain_definition_activity")
async def load_domain_definition_activity(domain_code: str) -> dict[str, Any]:
    """Load a DomainDefinition from DB and return as a JSON-serializable dict.

    Runs once at workflow start.  On Temporal replay the result is returned
    from history without re-querying the DB, ensuring determinism.
    """
    from app.database import AsyncSessionLocal
    from app.domain.domain_definition import DomainDefinitionLoader

    async with AsyncSessionLocal() as session:
        loader = DomainDefinitionLoader(session)
        domain_def = await loader.load(domain_code)
        return domain_def.model_dump()


@activity.defn(name="initialize_case_activity")
async def initialize_case_activity(input: OnboardingWorkflowInput) -> OnboardingStateDict:
    """Initialise OnboardingState in ContextStoreService and return as dict."""
    from uuid import UUID

    from app.services.context_store.context_store_service import context_store

    case_id = UUID(input.case_id)
    client_id = UUID(input.client_id)

    try:
        state = await context_store.initialise(case_id, client_id, input.selected_products)
    except Exception:
        from app.agents.base.a2a_types import OnboardingState
        state = OnboardingState(
            case_id=case_id,
            client_id=client_id,
            selected_products=input.selected_products,
        )

    return {
        "case_id": input.case_id,
        "client_id": input.client_id,
        "stage": state.stage,
        "selected_products": state.selected_products,
        "product_tracks": {},
        "priority_tier": getattr(state, "priority_tier", "standard"),
        "client_data": {},
        "documents_required": [],
        "documents_received": [],
        "version": state.version,
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
        "next_stage": None,
        "extra": {
            "kyc_status": "PENDING",
            "kyc_risk_score": None,
            "sales_review_id": None,
            "sales_review_decision": "PENDING",
            "escalation_reason": None,
            "human_review_id": None,
        },
    }


@activity.defn(name="customer_service_kickoff_activity")
async def customer_service_kickoff_activity(state: OnboardingStateDict) -> OnboardingStateDict:
    """Start the intake conversation (WebSocket event + DB init)."""
    from app.agents.customer_service.graph import build_customer_service_kickoff_graph

    graph = build_customer_service_kickoff_graph()
    return await graph.ainvoke(state)


@activity.defn(name="kyc_compliance_activity")
async def kyc_compliance_activity(state: OnboardingStateDict) -> OnboardingStateDict:
    """Run KYC check synchronously; returns state with kyc_status + next_stage set."""
    from app.agents.kyc_compliance.graph import build_kyc_graph

    graph = build_kyc_graph()
    result: OnboardingStateDict = await graph.ainvoke(state)

    # Persist compliance decision log
    await _log_kyc_decision(result)

    return result


async def _log_kyc_decision(state: OnboardingStateDict) -> None:
    """Background: log KYC outcome to audit and update case stage in DB."""
    from uuid import UUID

    from sqlalchemy import update as sa_update

    from app.database import AsyncSessionLocal
    from app.models.cases import OnboardingCase

    case_id_str = state.get("case_id", "")
    kyc_status = (state.get("extra") or {}).get("kyc_status", "PENDING")

    if not case_id_str:
        return

    # Persist stage to DB
    new_stage: str | None = None
    if kyc_status == "PASSED":
        new_stage = "PARALLEL_PRODUCTS"
    elif kyc_status in ("FAILED", "ESCALATED"):
        new_stage = "ESCALATED"

    if new_stage:
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    sa_update(OnboardingCase)
                    .where(OnboardingCase.id == UUID(case_id_str))
                    .values(current_stage=new_stage, status=new_stage)
                )
                await db.commit()
        except Exception as exc:
            activity.logger.warning(f"Failed to persist KYC stage for case {case_id_str}: {exc}")

    # Compliance decision log
    try:
        from app.services.compliance.compliance_decision_logger import compliance_decision_logger
        client_id_str = state.get("client_id", "")
        _extra = state.get("extra") or {}
        await compliance_decision_logger.log_automated_kyc_decision(
            case_id=UUID(case_id_str),
            client_id=UUID(client_id_str) if client_id_str else UUID(int=0),
            kyc_status=kyc_status,
            risk_band=state.get("_kyc_risk_band", "UNKNOWN"),
            composite_score=float(_extra.get("kyc_risk_score") or 0.0),
            identity_score=0.0,
            aml_score=0.0,
            profile_score=0.0,
            escalation_reasons=state.get("_kyc_escalation_reasons", []),
            required_documents=state.get("_kyc_required_documents", []),
            evidence_packet_id=state.get("_kyc_evidence_packet_id", ""),
        )
    except Exception as exc:
        activity.logger.warning(f"Failed to log KYC compliance decision: {exc}")


@activity.defn(name="product_onboarding_activity")
async def product_onboarding_activity(state: OnboardingStateDict) -> OnboardingStateDict:
    """Run the full product onboarding pipeline for one product track."""
    import traceback as _tb
    from app.agents.product_onboarding.graph import build_product_onboarding_graph

    try:
        graph = build_product_onboarding_graph()
        return await graph.ainvoke(state)
    except Exception as _exc:
        activity.logger.error(
            f"product_onboarding_activity FAILED "
            f"case={state.get('case_id')} product={state.get('_product_code')}: "
            f"{_exc}\n{_tb.format_exc()}"
        )
        raise


@activity.defn(name="sales_manager_kickoff_activity")
async def sales_manager_kickoff_activity(state: OnboardingStateDict) -> OnboardingStateDict:
    """Persist the sales review request; human decision arrives via Signal."""
    from app.agents.sales_manager.graph import build_sales_manager_kickoff_graph

    graph = build_sales_manager_kickoff_graph()
    return await graph.ainvoke(state)


@activity.defn(name="collaboration_kickoff_activity")
async def collaboration_kickoff_activity(state: OnboardingStateDict) -> OnboardingStateDict:
    """Create advisor collaboration room for human review."""
    from app.agents.collaboration.graph import build_collaboration_graph

    graph = build_collaboration_graph()
    return await graph.ainvoke(state)


@activity.defn(name="notification_activity")
async def notification_activity(state: OnboardingStateDict) -> OnboardingStateDict:
    """Dispatch a notification described by state['_notification_payload']."""
    from app.agents.notification.graph import build_notification_graph

    graph = build_notification_graph()
    return await graph.ainvoke(state)


@activity.defn(name="escalation_alert_activity")
async def escalation_alert_activity(state: OnboardingStateDict) -> OnboardingStateDict:
    """Dispatch an escalation alert and persist a HumanReview record."""
    from uuid import UUID

    from app.agents.notification.graph import build_escalation_alert_graph

    graph = build_escalation_alert_graph()
    notif_state: OnboardingStateDict = {
        **state,
        "_notification_payload": {
            "reason": (state.get("extra") or {}).get("escalation_reason", ""),
            "risk_band": state.get("_kyc_risk_band", "UNKNOWN"),
            "evidence_packet_id": state.get("_kyc_evidence_packet_id", ""),
        },
    }
    await graph.ainvoke(notif_state)

    # Persist HumanReview record
    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")
    if case_id_str and client_id_str:
        try:
            from app.database import AsyncSessionLocal
            from app.services.compliance.human_review_service import human_review_service

            async with AsyncSessionLocal() as db:
                await human_review_service.create_review(
                    case_id=UUID(case_id_str),
                    client_id=UUID(client_id_str),
                    escalation_reason=(state.get("extra") or {}).get("escalation_reason", ""),
                    kyc_payload={
                        "risk_band": state.get("_kyc_risk_band", ""),
                        "escalation_reasons": state.get("_kyc_escalation_reasons", []),
                    },
                    db=db,
                )
        except Exception as exc:
            activity.logger.warning(f"Failed to persist HumanReview for case {case_id_str}: {exc}")

    return state


@activity.defn(name="completion_activity")
async def completion_activity(state: OnboardingStateDict) -> OnboardingStateDict:
    """Provision accounts and send completion notifications."""
    from uuid import UUID

    from app.database import AsyncSessionLocal
    from app.services.accounts.account_service import AccountService

    case_id_str = state.get("case_id", "")
    client_id_str = state.get("client_id", "")

    if case_id_str and client_id_str:
        case_id = UUID(case_id_str)
        client_id = UUID(client_id_str)
        selected_products = state.get("selected_products", [])

        try:
            async with AsyncSessionLocal() as db:
                await AccountService.ensure_created(
                    session=db,
                    case_id=case_id,
                    client_id=client_id,
                    products=selected_products,
                )
                await db.commit()
        except Exception as exc:
            activity.logger.warning(f"Account creation failed for case {case_id_str}: {exc}")

        # Update DB to COMPLETE
        try:
            from sqlalchemy import update as sa_update
            from app.models.cases import OnboardingCase

            async with AsyncSessionLocal() as db:
                await db.execute(
                    sa_update(OnboardingCase)
                    .where(OnboardingCase.id == case_id)
                    .values(status="COMPLETE", current_stage="COMPLETE", percentage=100.0)
                )
                await db.commit()
        except Exception as exc:
            activity.logger.warning(f"Failed to mark case COMPLETE in DB: {exc}")

    return {**state, "stage": "COMPLETE", "next_stage": None}


@activity.defn(name="persist_stage_activity")
async def persist_stage_activity(input: dict[str, Any]) -> None:
    """Write status + current_stage to the onboarding_cases table and notify the frontend."""
    from uuid import UUID

    from sqlalchemy import update as sa_update

    from app.database import AsyncSessionLocal
    from app.models.cases import OnboardingCase
    from app.websocket.socket_emitter import socket_emitter

    case_id_str = input.get("case_id", "")
    stage = input.get("stage", "")

    if not case_id_str or not stage:
        return

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                sa_update(OnboardingCase)
                .where(OnboardingCase.id == UUID(case_id_str))
                .values(status=stage, current_stage=stage)
            )
            await db.commit()
    except Exception as exc:
        activity.logger.warning(f"persist_stage_activity failed for case {case_id_str}: {exc}")
        return

    await socket_emitter.case_stage_changed(case_id_str, {"stage": stage, "case_id": case_id_str})

    # When the case enters REVIEW, trigger AI completeness validation for every
    # document that was uploaded during INTAKE. client_data in shared_context is
    # now guaranteed to be complete, so the OCR simulated fallback (and LLM path)
    # will produce accurate, client-specific results.
    if stage == "REVIEW":
        import asyncio

        from sqlalchemy import select

        from app.models.documents import Document
        from app.services.validation.validation_orchestrator import run_validate_in_background

        try:
            async with AsyncSessionLocal() as db:
                rows = await db.execute(
                    select(Document.id).where(Document.case_id == UUID(case_id_str))
                )
                doc_ids = rows.scalars().all()

            for doc_id in doc_ids:
                asyncio.create_task(
                    run_validate_in_background(doc_id),
                    name=f"validate-review-{doc_id}",
                )

            activity.logger.info(
                f"[persist_stage_activity] Queued validation for {len(doc_ids)} document(s) "
                f"on REVIEW entry for case={case_id_str}"
            )
        except Exception as exc:
            activity.logger.warning(
                f"[persist_stage_activity] Failed to queue document validations "
                f"for case={case_id_str}: {exc}"
            )


@activity.defn(name="fraud_screening_activity")
async def fraud_screening_activity(state: OnboardingStateDict) -> OnboardingStateDict:
    """Run fraud screening concurrently with KYC (Phase 4.6)."""
    from app.agents.fraud_screening.graph import build_fraud_screening_graph

    graph = build_fraud_screening_graph()
    return await graph.ainvoke(state)


@activity.defn(name="start_sla_tracking_activity")
async def start_sla_tracking_activity(input: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve domain_stage_slas config, write case_sla_tracking row.

    Returns the resolved SLA config dict (window_hours, warning_pct, …) or None
    if no SLA is configured for this stage or the matching row has is_enabled=False.
    """
    from uuid import UUID

    from app.database import AsyncSessionLocal
    from app.services.sla.sla_monitor_service import sla_monitor_service

    case_id_str: str = input.get("case_id", "")
    stage_code: str = input.get("stage_code", "")
    domain_code: str = input.get("domain_code", "wealth_management")
    priority_tier: str | None = input.get("priority_tier") or None
    product_code: str | None = input.get("product_code") or None

    if not case_id_str or not stage_code:
        return None

    async with AsyncSessionLocal() as db:
        sla_spec = await sla_monitor_service.resolve_sla(
            db, domain_code, stage_code, priority_tier, product_code
        )
        if sla_spec is None:
            return None

        await sla_monitor_service.start_tracking(
            db,
            case_id=UUID(case_id_str),
            stage_code=stage_code,
            sla_spec=sla_spec,
            priority_tier=priority_tier,
            product_code=product_code,
        )
        await db.commit()

    return {
        "window_hours": sla_spec.window_hours,
        "warning_pct": sla_spec.warning_pct,
        "escalation_pct": sla_spec.escalation_pct,
        "warning_task_type": sla_spec.warning_task_type,
        "escalation_task_type": sla_spec.escalation_task_type,
        "escalation_target_agent": sla_spec.escalation_target_agent,
        "pause_on_human_review": sla_spec.pause_on_human_review,
        "is_enabled": sla_spec.is_enabled,
    }


@activity.defn(name="pause_sla_tracking_activity")
async def pause_sla_tracking_activity(input: dict[str, Any]) -> None:
    """Record paused_at in case_sla_tracking (clock-pause for human-review stages)."""
    from uuid import UUID

    from app.database import AsyncSessionLocal
    from app.services.sla.sla_monitor_service import sla_monitor_service

    case_id_str: str = input.get("case_id", "")
    stage_code: str = input.get("stage_code", "")
    if not case_id_str or not stage_code:
        return

    async with AsyncSessionLocal() as db:
        await sla_monitor_service.pause_tracking(db, UUID(case_id_str), stage_code)
        await db.commit()


@activity.defn(name="resume_sla_tracking_activity")
async def resume_sla_tracking_activity(input: dict[str, Any]) -> dict[str, Any]:
    """Accumulate paused_duration_seconds; return elapsed_active_seconds."""
    from uuid import UUID

    from app.database import AsyncSessionLocal
    from app.services.sla.sla_monitor_service import sla_monitor_service

    case_id_str: str = input.get("case_id", "")
    stage_code: str = input.get("stage_code", "")
    if not case_id_str or not stage_code:
        return {"elapsed_active_seconds": 0.0}

    async with AsyncSessionLocal() as db:
        elapsed = await sla_monitor_service.resume_tracking(db, UUID(case_id_str), stage_code)
        await db.commit()

    return {"elapsed_active_seconds": elapsed}


@activity.defn(name="send_sla_warning_activity")
async def send_sla_warning_activity(input: dict[str, Any]) -> None:
    """Record SLA_WARNING in decision_log and send notification.  Idempotent."""
    from uuid import UUID

    from app.database import AsyncSessionLocal
    from app.services.sla.sla_monitor_service import sla_monitor_service
    from app.services.audit.decision_log_service import DecisionLogService, DecisionLogEntry
    from app.services.audit.audit_event_types import AuditEventType

    case_id_str: str = input.get("case_id", "")
    stage_code: str = input.get("stage_code", "")
    if not case_id_str or not stage_code:
        return

    case_id = UUID(case_id_str)

    async with AsyncSessionLocal() as db:
        sent = await sla_monitor_service.record_warning_sent(db, case_id, stage_code)
        await db.commit()

    if not sent:
        return  # already fired

    try:
        log_svc = DecisionLogService()
        await log_svc.append(
            DecisionLogEntry(
                agent_id="sla_monitor",
                event_type=AuditEventType.SLA_WARNING,
                payload={
                    "case_id": case_id_str,
                    "stage_code": stage_code,
                    "sla_config": input.get("sla_config", {}),
                },
                case_id=case_id,
                is_compliance_event=True,
                is_regulatory_breach=False,
            )
        )
    except Exception as exc:
        activity.logger.warning(f"SLA_WARNING decision_log failed for case {case_id_str}: {exc}")

    activity.logger.warning(
        f"[SLA] Warning threshold reached: case={case_id_str} stage={stage_code}"
    )


@activity.defn(name="trigger_sla_breach_activity")
async def trigger_sla_breach_activity(input: dict[str, Any]) -> None:
    """Record SLA_BREACH in decision_log (is_regulatory_breach=True) and escalate case.

    Idempotent: if breach_triggered_at is already set, does nothing.
    """
    from uuid import UUID

    from sqlalchemy import update as sa_update

    from app.database import AsyncSessionLocal
    from app.models.cases import OnboardingCase
    from app.services.sla.sla_monitor_service import sla_monitor_service
    from app.services.audit.decision_log_service import DecisionLogService, DecisionLogEntry
    from app.services.audit.audit_event_types import AuditEventType
    from app.websocket.socket_emitter import socket_emitter

    case_id_str: str = input.get("case_id", "")
    stage_code: str = input.get("stage_code", "")
    if not case_id_str or not stage_code:
        return

    case_id = UUID(case_id_str)

    async with AsyncSessionLocal() as db:
        triggered = await sla_monitor_service.record_breach_triggered(db, case_id, stage_code)
        await db.commit()

    if not triggered:
        return  # already fired

    # Escalate the case
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                sa_update(OnboardingCase)
                .where(OnboardingCase.id == case_id)
                .values(status="ESCALATED", current_stage="ESCALATED")
            )
            await db.commit()
    except Exception as exc:
        activity.logger.warning(f"SLA breach escalation DB write failed for case {case_id_str}: {exc}")

    # Write to decision_log (is_regulatory_breach=True per FR-AU-01)
    try:
        log_svc = DecisionLogService()
        await log_svc.append(
            DecisionLogEntry(
                agent_id="sla_monitor",
                event_type=AuditEventType.SLA_BREACH,
                payload={
                    "case_id": case_id_str,
                    "stage_code": stage_code,
                    "sla_config": input.get("sla_config", {}),
                },
                case_id=case_id,
                is_compliance_event=True,
                is_regulatory_breach=True,
            )
        )
    except Exception as exc:
        activity.logger.warning(f"SLA_BREACH decision_log failed for case {case_id_str}: {exc}")

    # Notify via socket
    try:
        await socket_emitter.case_stage_changed(
            case_id_str,
            {"stage": "ESCALATED", "case_id": case_id_str, "reason": "sla_breach"},
        )
    except Exception:
        pass

    activity.logger.warning(
        f"[SLA] Breach threshold reached, case ESCALATED: case={case_id_str} stage={stage_code}"
    )


@activity.defn(name="contact_centre_summary_activity")
async def _contact_centre_summary_activity(state: OnboardingStateDict) -> OnboardingStateDict:
    """Generate contact-centre status summary for the case."""
    from app.agents.contact_centre.graph import build_contact_centre_graph

    graph = build_contact_centre_graph()
    return await graph.ainvoke(state)


# ── Activity lookup (Phase 3) ─────────────────────────────────────────────────
# Maps Temporal activity name strings (from StageDispatcher.resolve().activity_name)
# to the actual @activity.defn-decorated callable.  Used by OnboardingWorkflow
# stage handlers to call the correct activity without hardcoding function refs.

_ACTIVITY_LOOKUP: dict[str, Any] = {
    "customer_service_kickoff_activity": customer_service_kickoff_activity,
    "collaboration_kickoff_activity":    collaboration_kickoff_activity,
    "sales_manager_kickoff_activity":    sales_manager_kickoff_activity,
    "kyc_compliance_activity":           kyc_compliance_activity,
    "product_onboarding_activity":       product_onboarding_activity,
    "notification_activity":             notification_activity,
    "escalation_alert_activity":         escalation_alert_activity,
    "completion_activity":               completion_activity,
    "fraud_screening_activity":          fraud_screening_activity,
}


def get_all_activities() -> list[Any]:
    """Return the list of all activity functions to register with the Temporal worker."""
    from app.agents.direct_task_activities import get_direct_task_activities

    return [
        load_domain_definition_activity,
        initialize_case_activity,
        customer_service_kickoff_activity,
        kyc_compliance_activity,
        product_onboarding_activity,
        sales_manager_kickoff_activity,
        collaboration_kickoff_activity,
        notification_activity,
        escalation_alert_activity,
        completion_activity,
        persist_stage_activity,
        _contact_centre_summary_activity,
        fraud_screening_activity,
        # Phase 5 SLA activities
        start_sla_tracking_activity,
        pause_sla_tracking_activity,
        resume_sla_tracking_activity,
        send_sla_warning_activity,
        trigger_sla_breach_activity,
        *get_direct_task_activities(),
    ]


# ── ProductOnboardingWorkflow (child) ─────────────────────────────────────────


@workflow.defn(name="ProductOnboardingWorkflow")
class ProductOnboardingWorkflow:
    """Child workflow: runs the full product onboarding pipeline for one product.

    Spawned by OnboardingWorkflow once per selected product so that products
    execute in parallel and are individually trackable in the Temporal Web UI.
    """

    @workflow.run
    async def run(self, state: OnboardingStateDict) -> OnboardingStateDict:
        product_code = state.get("_product_code", "")
        workflow.logger.info(
            f"ProductOnboardingWorkflow started for case={state.get('case_id')} "
            f"product={product_code}"
        )
        result = await workflow.execute_activity(
            product_onboarding_activity,
            state,
            schedule_to_close_timeout=timedelta(hours=2),
            retry_policy=_STANDARD_RETRY,
        )
        workflow.logger.info(
            f"ProductOnboardingWorkflow done: case={state.get('case_id')} "
            f"product={product_code} status={result.get('_product_track_status')}"
        )
        return result


# ── OnboardingWorkflow (root) ─────────────────────────────────────────────────


@workflow.defn(name="OnboardingWorkflow")
class OnboardingWorkflow:
    """Root workflow: manages stage-level FSM for one onboarding case.

    Stage progression:
        INTAKE (wait for advance_stage signal)
          → SALES_REVIEW? (institutional: kickoff + wait for human_review_completed)
          → KYC (run synchronously via activity)
          → PARALLEL_PRODUCTS (child workflow per product, gathered)
          → REVIEW? (human: kickoff + wait for human_review_completed)
          → COMPLETE (accounts + notifications)
          or ESCALATED at any stage

    Phase 3: StageDispatcher (driven by DomainDefinition.task_routing) selects
    the activity to run for each stage.

    Phase 5: _start_sla_timer() replaces the no-op SLAHook stub.  Each stage
    handler starts a Temporal coroutine (_watch_sla) that fires warning/breach
    activities at configured percentages of the SLA window.  Human-pending stages
    with pause_on_human_review=True cancel the timer before the wait and restart
    it after the human responds.
    """

    def __init__(self) -> None:
        self._advance_signals: list[StageAdvanceSignal] = []
        self._human_signals: list[HumanReviewSignal] = []
        # Phase 3: populated in run() after load_domain_definition_activity
        self._dispatcher: StageDispatcher | None = None

    # ── SLA timer helpers (Phase 5) ───────────────────────────────────────────

    async def _start_sla_timer(
        self, state: OnboardingStateDict, stage_code: str
    ) -> tuple["asyncio.Task[None] | None", "dict[str, Any] | None"]:
        """Call start_sla_tracking_activity and launch _watch_sla as a background task.

        Returns (task, sla_config).  Both are None if no SLA is configured.
        task is an asyncio.Task; the caller must cancel it in a finally block.
        """
        try:
            sla_config = await workflow.execute_activity(
                start_sla_tracking_activity,
                {
                    "case_id": state.get("case_id", ""),
                    "stage_code": stage_code,
                    "domain_code": "wealth_management",
                    "priority_tier": state.get("priority_tier") or None,
                    "product_code": None,
                },
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=_STANDARD_RETRY,
            )
        except Exception as exc:
            workflow.logger.warning(f"start_sla_tracking_activity failed stage={stage_code}: {exc}")
            return None, None

        if not sla_config:
            return None, None

        task = asyncio.create_task(
            self._watch_sla(state.get("case_id", ""), stage_code, sla_config)
        )
        return task, sla_config

    async def _watch_sla(
        self,
        case_id: str,
        stage_code: str,
        sla_config: "dict[str, Any]",
        elapsed_seconds: float = 0.0,
    ) -> None:
        """Background Temporal coroutine: fires warning then breach activities.

        elapsed_seconds: active seconds already elapsed before this coroutine
        started (used when resuming after a clock-pause).  The coroutine is
        cancelled by the caller's finally block when the stage exits.
        """
        window_hours = float(sla_config.get("window_hours", 1.0))
        warning_pct = int(sla_config.get("warning_pct", 80))
        escalation_pct = int(sla_config.get("escalation_pct", 100))

        warning_total = window_hours * 3600 * warning_pct / 100
        breach_total = window_hours * 3600 * escalation_pct / 100

        remaining_to_warning = max(0.0, warning_total - elapsed_seconds)
        remaining_to_breach = max(0.0, breach_total - elapsed_seconds)

        try:
            if remaining_to_warning > 0:
                await workflow.sleep(timedelta(seconds=remaining_to_warning))
            await workflow.execute_activity(
                send_sla_warning_activity,
                {"case_id": case_id, "stage_code": stage_code, "sla_config": sla_config},
                schedule_to_close_timeout=timedelta(minutes=2),
                retry_policy=_NO_RETRY,
            )
            gap = remaining_to_breach - remaining_to_warning
            if gap > 0:
                await workflow.sleep(timedelta(seconds=gap))
            await workflow.execute_activity(
                trigger_sla_breach_activity,
                {"case_id": case_id, "stage_code": stage_code, "sla_config": sla_config},
                schedule_to_close_timeout=timedelta(minutes=5),
                retry_policy=_NO_RETRY,
            )
        except asyncio.CancelledError:
            pass  # Stage exited before SLA threshold; timer cancelled cleanly

    async def _pause_sla(
        self,
        case_id: str,
        stage_code: str,
        sla_task: "asyncio.Task[None] | None",
    ) -> None:
        """Cancel the running SLA task and record paused_at in DB."""
        if sla_task is not None and not sla_task.done():
            sla_task.cancel()
        try:
            await workflow.execute_activity(
                pause_sla_tracking_activity,
                {"case_id": case_id, "stage_code": stage_code},
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=_STANDARD_RETRY,
            )
        except Exception as exc:
            workflow.logger.warning(f"pause_sla_tracking_activity failed: {exc}")

    async def _resume_sla(
        self,
        case_id: str,
        stage_code: str,
        sla_config: "dict[str, Any]",
    ) -> "asyncio.Task[None]":
        """Accumulate paused duration and restart _watch_sla with remaining time."""
        try:
            resume = await workflow.execute_activity(
                resume_sla_tracking_activity,
                {"case_id": case_id, "stage_code": stage_code},
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=_STANDARD_RETRY,
            )
            elapsed = float((resume or {}).get("elapsed_active_seconds", 0.0))
        except Exception as exc:
            workflow.logger.warning(f"resume_sla_tracking_activity failed: {exc}")
            elapsed = 0.0
        return asyncio.create_task(
            self._watch_sla(case_id, stage_code, sla_config, elapsed_seconds=elapsed)
        )

    # ── Signal handlers ───────────────────────────────────────────────────────

    @workflow.signal
    def advance_stage(self, signal: StageAdvanceSignal) -> None:
        if isinstance(signal, dict):
            signal = StageAdvanceSignal(**signal)
        workflow.logger.info(f"advance_stage signal received: to_stage={signal.to_stage}")
        self._advance_signals.append(signal)

    @workflow.signal
    def human_review_completed(self, signal: HumanReviewSignal) -> None:
        if isinstance(signal, dict):
            signal = HumanReviewSignal(**signal)
        self._human_signals.append(signal)

    # ── Run ───────────────────────────────────────────────────────────────────

    @workflow.run
    async def run(self, input: OnboardingWorkflowInput) -> OnboardingWorkflowResult:
        workflow.logger.info(
            f"OnboardingWorkflow started: case={input.case_id} "
            f"products={input.selected_products}"
        )

        # Phase 3: load DomainDefinition once at workflow start.
        # The activity result is stored in Temporal history so replays are
        # deterministic — the DB is NOT re-queried on replay.
        domain_dict = await workflow.execute_activity(
            load_domain_definition_activity,
            input.domain_code,
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=_STANDARD_RETRY,
        )
        self._dispatcher = StageDispatcher.from_domain_dict(domain_dict)

        state: OnboardingStateDict = await workflow.execute_activity(
            initialize_case_activity,
            input,
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=_STANDARD_RETRY,
        )

        # Kickoff INTAKE — starts conversation context
        kickoff_dispatch = self._dispatcher.resolve("INTAKE", state)
        kickoff_fn = (
            _ACTIVITY_LOOKUP.get(kickoff_dispatch.activity_name, customer_service_kickoff_activity)
            if kickoff_dispatch else customer_service_kickoff_activity
        )
        await workflow.execute_activity(
            kickoff_fn,
            state,
            schedule_to_close_timeout=timedelta(minutes=5),
            retry_policy=_NO_RETRY,
        )

        while True:
            stage = OnboardingStage(state.get("stage", OnboardingStage.INTAKE))

            if stage == OnboardingStage.INTAKE:
                state = await self._handle_intake(state)

            elif stage == OnboardingStage.SALES_REVIEW:
                state = await self._handle_sales_review(state)

            elif stage == OnboardingStage.KYC:
                state = await self._handle_kyc(state)

            elif stage == OnboardingStage.PARALLEL_PRODUCTS:
                state = await self._handle_parallel_products(state)

            elif stage == OnboardingStage.REVIEW:
                state = await self._handle_review(state)

            elif stage == OnboardingStage.COMPLETE:
                state = await self._handle_complete(state)
                break

            elif stage == OnboardingStage.ESCALATED:
                state = await self._handle_escalated(state)
                # If still ESCALATED after resolution attempt, exit workflow.
                if OnboardingStage(state.get("stage", "ESCALATED")) == OnboardingStage.ESCALATED:
                    break
                # Otherwise loop — the stage was advanced (e.g. to PARALLEL_PRODUCTS).

            else:
                workflow.logger.warning(
                    f"Unknown stage {stage!r} for case={state.get('case_id')} — terminating"
                )
                break

        final_stage = state.get("stage", "UNKNOWN")
        workflow.logger.info(
            f"OnboardingWorkflow finished: case={input.case_id} final_stage={final_stage}"
        )
        return OnboardingWorkflowResult(final_stage=final_stage, case_id=input.case_id)

    # ── Stage handlers ────────────────────────────────────────────────────────

    async def _handle_intake(self, state: OnboardingStateDict) -> OnboardingStateDict:
        """Wait for CustomerService to signal data collection complete."""
        sla_task, _ = await self._start_sla_timer(state, "INTAKE")
        try:
            await workflow.wait_condition(
                lambda: len(self._advance_signals) > 0,
                timeout=timedelta(days=7),
            )
            signal = self._advance_signals.pop(0)
            next_stage = signal.to_stage or "REVIEW"
            state = {**state, "stage": next_stage, **signal.payload}
            await workflow.execute_activity(
                persist_stage_activity,
                {"case_id": state["case_id"], "stage": next_stage},
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=_STANDARD_RETRY,
            )
            return state
        finally:
            if sla_task and not sla_task.done():
                sla_task.cancel()

    async def _handle_sales_review(self, state: OnboardingStateDict) -> OnboardingStateDict:
        """Kickoff sales review and wait for a decision signal.

        The sales review service sends an advance_stage(to_stage="KYC") signal
        (via publish_task(RUN_KYC_CHECK)) on approval. Both signal types are
        accepted so either code path unblocks the workflow.
        """
        sla_task, sla_config = await self._start_sla_timer(state, "SALES_REVIEW")
        case_id = state.get("case_id", "")
        try:
            dispatch = self._dispatcher.resolve("SALES_REVIEW", state) if self._dispatcher else None
            kickoff_fn = (
                _ACTIVITY_LOOKUP.get(dispatch.activity_name, sales_manager_kickoff_activity)
                if dispatch and dispatch.activity_name in _ACTIVITY_LOOKUP
                else sales_manager_kickoff_activity
            )
            await workflow.execute_activity(
                kickoff_fn,
                state,
                schedule_to_close_timeout=timedelta(minutes=5),
                retry_policy=_NO_RETRY,
            )

            # Pause SLA clock while waiting for human decision
            if sla_config and sla_config.get("pause_on_human_review"):
                await self._pause_sla(case_id, "SALES_REVIEW", sla_task)
                sla_task = None

            await workflow.wait_condition(
                lambda: len(self._human_signals) > 0 or len(self._advance_signals) > 0,
                timeout=timedelta(days=7),
            )

            # Resume SLA clock after human responds
            if sla_config and sla_config.get("pause_on_human_review"):
                sla_task = await self._resume_sla(case_id, "SALES_REVIEW", sla_config)

            if self._advance_signals:
                signal = self._advance_signals.pop(0)
                next_stage = signal.to_stage
                extra = {**(state.get("extra") or {}), "sales_review_decision": "APPROVED"}
                state = {**state, "stage": next_stage, "extra": extra}
            else:
                human_sig = self._human_signals.pop(0)
                if human_sig.decision in ("APPROVED", "MORE_INFO_REQUESTED"):
                    next_stage = "KYC"
                else:
                    next_stage = "ESCALATED"
                extra = {**(state.get("extra") or {}), "sales_review_decision": human_sig.decision}
                state = {**state, "stage": next_stage, "extra": extra}

            await workflow.execute_activity(
                persist_stage_activity,
                {"case_id": state["case_id"], "stage": next_stage},
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=_STANDARD_RETRY,
            )
            return state
        finally:
            if sla_task and not sla_task.done():
                sla_task.cancel()

    async def _handle_kyc(self, state: OnboardingStateDict) -> OnboardingStateDict:
        """Run KYC compliance check and fraud screening concurrently (Phase 4.6)."""
        sla_task, _ = await self._start_sla_timer(state, "KYC")
        try:
            return await self._run_kyc(state)
        finally:
            if sla_task and not sla_task.done():
                sla_task.cancel()

    async def _run_kyc(self, state: OnboardingStateDict) -> OnboardingStateDict:
        """Inner KYC logic extracted so _handle_kyc can wrap it with the SLA finally."""

        dispatch = self._dispatcher.resolve("KYC", state) if self._dispatcher else None
        kyc_fn = (
            _ACTIVITY_LOOKUP.get(dispatch.activity_name, kyc_compliance_activity)
            if dispatch and dispatch.activity_name in _ACTIVITY_LOOKUP
            else kyc_compliance_activity
        )
        # Phase 4.6: run KYC and fraud screening in parallel Temporal activities.
        # fraud_screening_activity is best-effort — its failure must not kill the workflow.
        _gather_results = await asyncio.gather(
            workflow.execute_activity(
                kyc_fn,
                state,
                schedule_to_close_timeout=timedelta(minutes=30),
                retry_policy=_STANDARD_RETRY,
            ),
            workflow.execute_activity(
                fraud_screening_activity,
                state,
                schedule_to_close_timeout=timedelta(minutes=5),
                retry_policy=_NO_RETRY,
            ),
            return_exceptions=True,
        )
        kyc_result = _gather_results[0]
        if isinstance(kyc_result, BaseException):
            raise kyc_result  # KYC failure IS fatal

        _fraud_raw = _gather_results[1]
        if isinstance(_fraud_raw, BaseException):
            # Fraud screening unavailable — default to CLEARED so KYC can proceed.
            workflow.logger.warning(f"fraud_screening_activity failed, defaulting to CLEARED: {_fraud_raw}")
            fraud_result: OnboardingStateDict = {
                **state,
                "extra": {**(state.get("extra") or {}), "fraud_screened": "CLEARED"},
            }
        else:
            fraud_result = _fraud_raw

        # Merge fraud result into KYC result.  KYC must spread LAST so its
        # authoritative keys (kyc_status, kyc_risk_score, …) win over the stale
        # copies that fraud_result carries from the shared initial state.
        # fraud_result only adds fraud-specific keys (fraud_screened,
        # escalation_reason); KYC does not set those, so they are preserved.
        merged_extra = {**(fraud_result.get("extra") or {}), **(kyc_result.get("extra") or {})}
        result = {**kyc_result, "extra": merged_extra}

        # If fraud was flagged, override next_stage to ESCALATED regardless of KYC outcome
        if merged_extra.get("fraud_screened") == "FLAGGED":
            result = {**result, "next_stage": "ESCALATED"}

        _result_extra = result.get("extra") or {}
        next_stage = result.get("next_stage") or (
            "PARALLEL_PRODUCTS" if _result_extra.get("kyc_status") == "PASSED" else "ESCALATED"
        )
        state = {**result, "stage": next_stage}
        await workflow.execute_activity(
            persist_stage_activity,
            {"case_id": state["case_id"], "stage": next_stage},
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=_STANDARD_RETRY,
        )

        # Send KYC outcome notifications via dispatcher-selected activity
        selected_products = state.get("selected_products", [])
        dispatch_notif = self._dispatcher.resolve("COMPLETE", state) if self._dispatcher else None
        notif_fn = (
            _ACTIVITY_LOOKUP.get(dispatch_notif.activity_name, notification_activity)
            if dispatch_notif and dispatch_notif.activity_name in _ACTIVITY_LOOKUP
            else notification_activity
        )
        if _result_extra.get("kyc_status") in ("PASSED", "FAILED"):
            templates = (
                [("kyc_passed", "NORMAL")]
                if _result_extra.get("kyc_status") == "PASSED"
                else [("kyc_failed", "HIGH"), ("kyc_failed_inapp", "HIGH")]
            )
            for tmpl, priority in templates:
                await workflow.execute_activity(
                    notif_fn,
                    {
                        **state,
                        "_notification_payload": {
                            "template": tmpl,
                            "selected_products": selected_products,
                            "priority": priority,
                        },
                    },
                    schedule_to_close_timeout=timedelta(minutes=2),
                    retry_policy=_NO_RETRY,
                )
        return state

    async def _handle_parallel_products(
        self, state: OnboardingStateDict
    ) -> OnboardingStateDict:
        """Launch one child workflow per selected product in parallel."""
        sla_task, _ = await self._start_sla_timer(state, "PARALLEL_PRODUCTS")
        try:
            selected_products: list[str] = state.get("selected_products", [])
            case_id = state.get("case_id", "")

            child_handles = await asyncio.gather(*[
                workflow.start_child_workflow(
                    ProductOnboardingWorkflow,
                    {**state, "_product_code": pc},
                    id=f"onboarding-{case_id}-product-{pc}",
                    parent_close_policy=workflow.ParentClosePolicy.TERMINATE,
                )
                for pc in selected_products
            ])
            product_results: list[OnboardingStateDict] = list(
                await asyncio.gather(*child_handles)
            )

            # Merge product track state from child results
            merged_tracks: dict[str, Any] = dict(state.get("product_tracks") or {})
            problematic = {"UNSUITABLE", "FAILED"}

            for res in product_results:
                for pc, track in (res.get("product_tracks") or {}).items():
                    merged_tracks[pc] = track

            has_issues = any(
                merged_tracks.get(pc, {}).get("stage", "") in problematic
                for pc in selected_products
            )
            next_stage = "REVIEW" if has_issues else "COMPLETE"
            state = {**state, "product_tracks": merged_tracks, "stage": next_stage}

            await workflow.execute_activity(
                persist_stage_activity,
                {"case_id": case_id, "stage": next_stage},
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=_STANDARD_RETRY,
            )
            return state
        finally:
            if sla_task and not sla_task.done():
                sla_task.cancel()

    async def _handle_review(self, state: OnboardingStateDict) -> OnboardingStateDict:
        """Create collaboration room and wait for either a human-review or advance-stage signal.

        The REVIEW stage is entered from two different paths:
        - Post-INTAKE document review: advance_stage signal carries the next stage
          (KYC, SALES_REVIEW, ESCALATED).
        - Post-PARALLEL_PRODUCTS product issues review: human_review_completed signal
          carries the decision; APPROVED → COMPLETE, REJECTED → ESCALATED.
        Both signal types are accepted so either path unblocks the workflow.
        """
        sla_task, sla_config = await self._start_sla_timer(state, "REVIEW")
        case_id = state.get("case_id", "")
        try:
            dispatch = self._dispatcher.resolve("REVIEW", state) if self._dispatcher else None
            collab_fn = (
                _ACTIVITY_LOOKUP.get(dispatch.activity_name, collaboration_kickoff_activity)
                if dispatch and dispatch.activity_name in _ACTIVITY_LOOKUP
                else collaboration_kickoff_activity
            )
            await workflow.execute_activity(
                collab_fn,
                state,
                schedule_to_close_timeout=timedelta(minutes=5),
                retry_policy=_NO_RETRY,
            )

            # Pause SLA clock while waiting for human decision
            if sla_config and sla_config.get("pause_on_human_review"):
                await self._pause_sla(case_id, "REVIEW", sla_task)
                sla_task = None

            await workflow.wait_condition(
                lambda: len(self._human_signals) > 0 or len(self._advance_signals) > 0,
                timeout=timedelta(days=30),
            )

            # Resume SLA clock after human responds
            if sla_config and sla_config.get("pause_on_human_review"):
                sla_task = await self._resume_sla(case_id, "REVIEW", sla_config)

            if self._advance_signals:
                signal = self._advance_signals.pop(0)
                next_stage = signal.to_stage
                state = {**state, "stage": next_stage, **signal.payload}
            else:
                human_sig = self._human_signals.pop(0)
                next_stage = "COMPLETE" if human_sig.decision == "APPROVED" else "ESCALATED"
                state = {**state, "stage": next_stage}

            await workflow.execute_activity(
                persist_stage_activity,
                {"case_id": state["case_id"], "stage": next_stage},
                schedule_to_close_timeout=timedelta(seconds=30),
                retry_policy=_STANDARD_RETRY,
            )
            return state
        finally:
            if sla_task and not sla_task.done():
                sla_task.cancel()

    async def _handle_complete(self, state: OnboardingStateDict) -> OnboardingStateDict:
        """Provision accounts and send completion notifications."""
        result = await workflow.execute_activity(
            completion_activity,
            state,
            schedule_to_close_timeout=timedelta(minutes=10),
            retry_policy=_STANDARD_RETRY,
        )

        # Completion notifications via dispatcher-selected activity
        dispatch = self._dispatcher.resolve("COMPLETE", state) if self._dispatcher else None
        notif_fn = (
            _ACTIVITY_LOOKUP.get(dispatch.activity_name, notification_activity)
            if dispatch and dispatch.activity_name in _ACTIVITY_LOOKUP
            else notification_activity
        )
        for tmpl in ("onboarding_complete", "onboarding_complete_inapp"):
            await workflow.execute_activity(
                notif_fn,
                {**result, "_notification_payload": {"template": tmpl}},
                schedule_to_close_timeout=timedelta(minutes=2),
                retry_policy=_NO_RETRY,
            )
        return result

    async def _handle_escalated(self, state: OnboardingStateDict) -> OnboardingStateDict:
        """Dispatch escalation alert then wait for a resolution signal.

        ESCALATED is not a hard terminal state: a compliance officer may approve
        the escalation review and advance the case to PARALLEL_PRODUCTS.
        The workflow waits for human_review_completed or advance_stage.
        If no signal arrives within 90 days the workflow exits.
        """
        sla_task, _ = await self._start_sla_timer(state, "ESCALATED")
        try:
            dispatch = self._dispatcher.resolve("ESCALATED", state) if self._dispatcher else None
            escalation_fn = (
                _ACTIVITY_LOOKUP.get(dispatch.activity_name, escalation_alert_activity)
                if dispatch and dispatch.activity_name in _ACTIVITY_LOOKUP
                else escalation_alert_activity
            )
            await workflow.execute_activity(
                escalation_fn,
                state,
                schedule_to_close_timeout=timedelta(minutes=5),
                retry_policy=_NO_RETRY,
            )
            await workflow.execute_activity(
                _contact_centre_summary_activity,
                state,
                schedule_to_close_timeout=timedelta(minutes=5),
                retry_policy=_NO_RETRY,
            )

            # Wait for a resolution signal (approved → PARALLEL_PRODUCTS, rejected → done).
            resolved = await workflow.wait_condition(
                lambda: len(self._human_signals) > 0 or len(self._advance_signals) > 0,
                timeout=timedelta(days=90),
            )

            if not resolved:
                # Timed out — treat as terminal escalation.
                return {**state, "stage": "ESCALATED"}

            if self._human_signals:
                signal = self._human_signals.pop(0)
                if signal.decision == "APPROVED":
                    return {**state, "stage": "PARALLEL_PRODUCTS"}
            elif self._advance_signals:
                signal = self._advance_signals.pop(0)
                return {**state, "stage": signal.to_stage}

            return {**state, "stage": "ESCALATED"}
        finally:
            if sla_task and not sla_task.done():
                sla_task.cancel()
