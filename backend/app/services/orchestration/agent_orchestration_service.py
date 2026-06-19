"""AgentOrchestrationService — Temporal-backed orchestration (Phase 0.5).

Temporal is the sole execution substrate for all agent tasks — there is no
asyncio fallback and no AgentEventBus. Per-request tasks (notifications,
document processing, collaboration) run as DirectTaskWorkflow instances so
every agent call is durable, retried, and visible in the Temporal Web UI.
"""
from __future__ import annotations

import asyncio
import os
from uuid import UUID

from loguru import logger

from app.agents.base.a2a_types import (
    OnboardingStage,
    OnboardingWorkflowInput,
    StageAdvanceSignal,
    HumanReviewSignal,
    TaskPacket,
    TaskType,
)

# ── Temporal configuration ────────────────────────────────────────────────────

_TEMPORAL_HOST = os.environ.get("TEMPORAL_HOST", "localhost:7233")
_TEMPORAL_ENABLED = os.environ.get("TEMPORAL_ENABLED", "true").lower() == "true"
_TASK_QUEUE = "onboarding"

# ── Helpers ───────────────────────────────────────────────────────────────────


def _workflow_id(case_id: UUID) -> str:
    return f"onboarding-{case_id}"


def _direct_task_id(task: TaskPacket) -> str:
    return f"task-{task.id}"


# ── Service ───────────────────────────────────────────────────────────────────


class AgentOrchestrationService:
    """Singleton service that boots the Temporal worker on application startup.

    Responsibilities:
    - Connect to the self-hosted Temporal server (required; no fallback).
    - Register all Temporal workflows and activities.
    - Start the Temporal worker as a background asyncio task.
    - Provide `start_onboarding`, `resume_onboarding`, and `publish_task`
      entry points called by the REST API layer.

    All agent tasks — workflow-control signals and direct per-request calls
    alike — route through Temporal. There is no AgentEventBus.
    """

    def __init__(self) -> None:
        self._temporal_client = None
        self._worker = None
        self._worker_task: asyncio.Task | None = None
        self._active_cases: set[UUID] = set()
        self._started = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Connect to Temporal and start the worker. Skipped when TEMPORAL_ENABLED=false."""
        if self._started:
            return

        if not _TEMPORAL_ENABLED:
            logger.warning(
                "TEMPORAL_ENABLED=false — Temporal worker not started. "
                "Set TEMPORAL_ENABLED=true once Temporal is running."
            )
            self._started = True
            return

        try:
            await self._start_temporal_worker()
            logger.info("AgentOrchestrationService started (Temporal worker running)")
        except Exception as exc:
            logger.warning(
                f"Temporal unavailable at {_TEMPORAL_HOST} — worker not started. Error: {exc}"
            )

        self._started = True

    async def stop(self) -> None:
        """Cancel the background worker task and close Temporal connection."""
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

        if self._worker is not None:
            await self._worker.shutdown()
            self._worker = None

        self._started = False
        logger.info("AgentOrchestrationService stopped")

    # ── Onboarding entry points ───────────────────────────────────────────────

    async def start_onboarding(
        self,
        case_id: UUID,
        client_id: UUID,
        selected_products: list[str],
        client_name: str = "",
        client_email: str = "",
        case_name: str = "",
    ) -> None:
        """Start a new OnboardingWorkflow via Temporal."""
        if not self._started:
            await self.start()

        self._active_cases.add(case_id)

        from app.workflows.onboarding_workflow import OnboardingWorkflow

        await self._temporal_client.start_workflow(
            OnboardingWorkflow.run,
            OnboardingWorkflowInput(
                case_id=str(case_id),
                client_id=str(client_id),
                selected_products=selected_products,
                client_name=client_name,
                client_email=client_email,
                case_name=case_name,
            ),
            id=_workflow_id(case_id),
            task_queue=_TASK_QUEUE,
        )
        logger.info(
            f"OnboardingWorkflow started: case={case_id} products={selected_products}"
        )

    async def resume_onboarding(self, case_id: UUID) -> None:
        """Signal an existing Temporal workflow to resume."""
        if not self._started:
            await self.start()

        self._active_cases.add(case_id)

        handle = self._temporal_client.get_workflow_handle(_workflow_id(case_id))
        try:
            from app.services.context_store.context_store_service import context_store
            state = await context_store.get(case_id)
            stage = str(state.stage)
        except KeyError:
            stage = OnboardingStage.INTAKE

        await handle.signal(
            "advance_stage",
            StageAdvanceSignal(to_stage=stage).model_dump(),
        )
        logger.info(f"Signalled OnboardingWorkflow to resume: case={case_id} stage={stage}")

    async def publish_task(self, task: TaskPacket) -> None:
        """Route a TaskPacket to Temporal.

        Workflow-control tasks (stage advance, escalate, KYC trigger, etc.)
        become Signals on the running OnboardingWorkflow.

        All other tasks start a short-lived DirectTaskWorkflow that executes
        the appropriate agent activity with retries.
        """
        if not self._started:
            await self.start()

        _SIGNAL_TYPES = {
            TaskType.ADVANCE_STAGE,
            TaskType.ESCALATE,
            TaskType.RESUME_ONBOARDING,
            TaskType.RUN_KYC_CHECK,
            TaskType.SALES_MANAGER_REVIEW,
        }

        if task.task_type in _SIGNAL_TYPES:
            workflow_id = _workflow_id(task.case_id)
            handle = self._temporal_client.get_workflow_handle(workflow_id)
            if task.task_type == TaskType.ESCALATE:
                signal = StageAdvanceSignal(
                    to_stage=OnboardingStage.ESCALATED,
                    payload={"escalation_reason": task.payload.get("reason", "")},
                )
            elif task.task_type == TaskType.RUN_KYC_CHECK:
                signal = StageAdvanceSignal(to_stage=OnboardingStage.KYC, payload=task.payload)
            elif task.task_type == TaskType.SALES_MANAGER_REVIEW:
                signal = StageAdvanceSignal(
                    to_stage=OnboardingStage.SALES_REVIEW, payload=task.payload
                )
            else:
                signal = StageAdvanceSignal(
                    to_stage=task.payload.get("to_stage", ""),
                    payload=task.payload,
                )
            try:
                await handle.signal("advance_stage", signal.model_dump())
                logger.info(
                    f"Signal sent: advance_stage workflow={workflow_id} "
                    f"to_stage={signal.to_stage} task_type={task.task_type}"
                )
            except Exception as sig_exc:
                logger.error(
                    f"Signal FAILED: advance_stage workflow={workflow_id} "
                    f"to_stage={signal.to_stage} error={sig_exc!r}"
                )
                raise
            return

        # Per-request agent task → DirectTaskWorkflow
        from app.agents.direct_task_activities import DirectTaskWorkflow

        await self._temporal_client.start_workflow(
            DirectTaskWorkflow.run,
            task,
            id=_direct_task_id(task),
            task_queue=_TASK_QUEUE,
        )

    async def start_product_onboarding(
        self,
        case_id: UUID,
        client_id: UUID,
        selected_products: list[str],
    ) -> None:
        """Signal the workflow to begin PARALLEL_PRODUCTS (called post human-review)."""
        if not self._started:
            await self.start()

        handle = self._temporal_client.get_workflow_handle(_workflow_id(case_id))
        await handle.signal(
            "human_review_completed",
            HumanReviewSignal(
                decision="APPROVED",
                reviewer_id="system",
                payload={"selected_products": selected_products},
            ).model_dump(),
        )

    # ── Temporal Signals (convenience helpers for API routers) ────────────────

    async def signal_stage_advance(
        self, case_id: UUID, to_stage: str, payload: dict | None = None
    ) -> None:
        """Send advance_stage signal to the running OnboardingWorkflow."""
        handle = self._temporal_client.get_workflow_handle(_workflow_id(case_id))
        await handle.signal(
            "advance_stage",
            StageAdvanceSignal(to_stage=to_stage, payload=payload or {}).model_dump(),
        )

    async def signal_human_review(
        self,
        case_id: UUID,
        decision: str,
        reviewer_id: str,
        payload: dict | None = None,
    ) -> None:
        """Send human_review_completed signal to the running OnboardingWorkflow."""
        handle = self._temporal_client.get_workflow_handle(_workflow_id(case_id))
        await handle.signal(
            "human_review_completed",
            HumanReviewSignal(
                decision=decision,
                reviewer_id=reviewer_id,
                payload=payload or {},
            ).model_dump(),
        )

    # ── Introspection ─────────────────────────────────────────────────────────

    @property
    def active_cases(self) -> frozenset[UUID]:
        return frozenset(self._active_cases)

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def temporal_client(self):
        return self._temporal_client

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _start_temporal_worker(self) -> None:
        from temporalio.client import Client
        from temporalio.worker import Worker
        from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

        from app.agents.direct_task_activities import DirectTaskWorkflow
        from app.workflows.onboarding_workflow import (
            OnboardingWorkflow,
            ProductOnboardingWorkflow,
            get_all_activities,
        )

        self._temporal_client = await Client.connect(_TEMPORAL_HOST)
        self._worker = Worker(
            self._temporal_client,
            task_queue=_TASK_QUEUE,
            workflows=[OnboardingWorkflow, ProductOnboardingWorkflow, DirectTaskWorkflow],
            activities=get_all_activities(),
            workflow_runner=SandboxedWorkflowRunner(
                restrictions=SandboxRestrictions.default.with_passthrough_modules(
                    "pydantic",
                    "pydantic_core",
                    "loguru",
                    # app.services.orchestration is passed through so the sandbox
                    # reuses the outer-process module cache instead of re-importing
                    # it.  Re-importing triggers __init__.py → journey_resumption_service
                    # → app.database → app.config → Settings() → pydantic_settings
                    # → Path.expanduser(), which the sandbox restricts.
                    # stage_dispatcher.py itself is pure deterministic Python, so
                    # passing the whole package through is safe.
                    "app.services.orchestration",
                )
            ),
        )
        self._worker_task = asyncio.create_task(
            self._worker.run(), name="temporal-worker"
        )
        logger.info(
            f"Temporal worker started: host={_TEMPORAL_HOST} queue={_TASK_QUEUE}"
        )


# Process-level singleton — imported by main.py, routers, and services.
orchestration_service = AgentOrchestrationService()
