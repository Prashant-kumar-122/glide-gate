"""Temporal OnboardingWorkflow + all Temporal Activities (Phase 0.5).

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

_NO_RETRY = RetryPolicy(maximum_attempts=1)
_STANDARD_RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=5))

# ── Activities ────────────────────────────────────────────────────────────────


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
    from app.agents.product_onboarding.graph import build_product_onboarding_graph

    graph = build_product_onboarding_graph()
    return await graph.ainvoke(state)


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


def get_all_activities() -> list[Any]:
    """Return the list of all activity functions to register with the Temporal worker."""
    from app.agents.direct_task_activities import get_direct_task_activities

    return [
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
    """

    def __init__(self) -> None:
        self._advance_signals: list[StageAdvanceSignal] = []
        self._human_signals: list[HumanReviewSignal] = []

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

        state: OnboardingStateDict = await workflow.execute_activity(
            initialize_case_activity,
            input,
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=_STANDARD_RETRY,
        )

        # Kickoff INTAKE — starts conversation context
        await workflow.execute_activity(
            customer_service_kickoff_activity,
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

    async def _handle_sales_review(self, state: OnboardingStateDict) -> OnboardingStateDict:
        """Kickoff sales review and wait for a decision signal.

        The sales review service sends an advance_stage(to_stage="KYC") signal
        (via publish_task(RUN_KYC_CHECK)) on approval. Both signal types are
        accepted so either code path unblocks the workflow.
        """
        await workflow.execute_activity(
            sales_manager_kickoff_activity,
            state,
            schedule_to_close_timeout=timedelta(minutes=5),
            retry_policy=_NO_RETRY,
        )
        await workflow.wait_condition(
            lambda: len(self._human_signals) > 0 or len(self._advance_signals) > 0,
            timeout=timedelta(days=7),
        )

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

    async def _handle_kyc(self, state: OnboardingStateDict) -> OnboardingStateDict:
        """Run KYC compliance check as a synchronous activity."""
        result = await workflow.execute_activity(
            kyc_compliance_activity,
            state,
            schedule_to_close_timeout=timedelta(minutes=30),
            retry_policy=_STANDARD_RETRY,
        )
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

        # Send KYC outcome notifications
        selected_products = state.get("selected_products", [])
        client_id = state.get("client_id", "")
        if _result_extra.get("kyc_status") in ("PASSED", "FAILED"):
            templates = (
                [("kyc_passed", "NORMAL")]
                if _result_extra.get("kyc_status") == "PASSED"
                else [("kyc_failed", "HIGH"), ("kyc_failed_inapp", "HIGH")]
            )
            for tmpl, priority in templates:
                await workflow.execute_activity(
                    notification_activity,
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
        terminal = {"COMPLETE", "UNSUITABLE", "FAILED"}
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

    async def _handle_review(self, state: OnboardingStateDict) -> OnboardingStateDict:
        """Create collaboration room and wait for either a human-review or advance-stage signal.

        The REVIEW stage is entered from two different paths:
        - Post-INTAKE document review: advance_stage signal carries the next stage
          (KYC, SALES_REVIEW, ESCALATED).
        - Post-PARALLEL_PRODUCTS product issues review: human_review_completed signal
          carries the decision; APPROVED → COMPLETE, REJECTED → ESCALATED.
        Both signal types are accepted so either path unblocks the workflow.
        """
        await workflow.execute_activity(
            collaboration_kickoff_activity,
            state,
            schedule_to_close_timeout=timedelta(minutes=5),
            retry_policy=_NO_RETRY,
        )
        await workflow.wait_condition(
            lambda: len(self._human_signals) > 0 or len(self._advance_signals) > 0,
            timeout=timedelta(days=30),
        )

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

    async def _handle_complete(self, state: OnboardingStateDict) -> OnboardingStateDict:
        """Provision accounts and send completion notifications."""
        result = await workflow.execute_activity(
            completion_activity,
            state,
            schedule_to_close_timeout=timedelta(minutes=10),
            retry_policy=_STANDARD_RETRY,
        )
        # Completion notifications
        for tmpl in ("onboarding_complete", "onboarding_complete_inapp"):
            await workflow.execute_activity(
                notification_activity,
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
        await workflow.execute_activity(
            escalation_alert_activity,
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


@activity.defn(name="contact_centre_summary_activity")
async def _contact_centre_summary_activity(state: OnboardingStateDict) -> OnboardingStateDict:
    """Generate contact-centre status summary for the case."""
    from app.agents.contact_centre.graph import build_contact_centre_graph

    graph = build_contact_centre_graph()
    return await graph.ainvoke(state)
