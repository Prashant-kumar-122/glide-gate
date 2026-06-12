"""Direct-task Temporal activities + DirectTaskWorkflow.

Replaces the AgentEventBus for per-request tasks (notifications, document
processing, collaboration) dispatched outside the main OnboardingWorkflow —
e.g. from API routers, journey resumption, or an agent calling send_task()
during its own activity execution.

Each activity instantiates a fresh agent and delegates to timed_process()
so timing and audit logging are preserved.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskResponse

_DIRECT_RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=2))

# ── Per-agent activities ──────────────────────────────────────────────────────


@activity.defn(name="direct_notification_task")
async def direct_notification_task(task: TaskPacket) -> TaskResponse:
    from app.agents.notification.notification_agent import NotificationAgent
    return await NotificationAgent().timed_process(task)


@activity.defn(name="direct_collaboration_task")
async def direct_collaboration_task(task: TaskPacket) -> TaskResponse:
    from app.agents.collaboration.collaboration_agent import CollaborationAgent
    return await CollaborationAgent().timed_process(task)


@activity.defn(name="direct_document_task")
async def direct_document_task(task: TaskPacket) -> TaskResponse:
    from app.agents.document_intelligence.document_intelligence_agent import (
        DocumentIntelligenceAgent,
    )
    return await DocumentIntelligenceAgent().timed_process(task)


@activity.defn(name="direct_contact_centre_task")
async def direct_contact_centre_task(task: TaskPacket) -> TaskResponse:
    from app.agents.contact_centre.contact_centre_agent import ContactCentreAgent
    return await ContactCentreAgent().timed_process(task)


@activity.defn(name="direct_sales_manager_task")
async def direct_sales_manager_task(task: TaskPacket) -> TaskResponse:
    from app.agents.sales_manager.sales_manager_agent import SalesManagerAgent
    return await SalesManagerAgent().timed_process(task)


@activity.defn(name="direct_product_onboarding_task")
async def direct_product_onboarding_task(task: TaskPacket) -> TaskResponse:
    from app.agents.product_onboarding.product_onboarding_agent import ProductOnboardingAgent
    return await ProductOnboardingAgent().timed_process(task)


@activity.defn(name="direct_customer_service_task")
async def direct_customer_service_task(task: TaskPacket) -> TaskResponse:
    from app.agents.customer_service.customer_service_agent import CustomerServiceAgent
    return await CustomerServiceAgent().timed_process(task)


# Module-level map: AgentID str value → activity function
# Used by DirectTaskWorkflow.run() — all entries are already-imported names so
# Temporal's workflow sandbox can resolve them without I/O.
_AGENT_ACTIVITY: dict[str, Any] = {
    AgentID.NOTIFICATION:          direct_notification_task,
    AgentID.COLLABORATION:         direct_collaboration_task,
    AgentID.DOCUMENT_INTELLIGENCE: direct_document_task,
    AgentID.CONTACT_CENTRE:        direct_contact_centre_task,
    AgentID.SALES_MANAGER:         direct_sales_manager_task,
    AgentID.PRODUCT_ONBOARDING:    direct_product_onboarding_task,
    AgentID.CUSTOMER_SERVICE:      direct_customer_service_task,
}


def get_direct_task_activities() -> list[Any]:
    return list(_AGENT_ACTIVITY.values())


# ── DirectTaskWorkflow ────────────────────────────────────────────────────────


@workflow.defn(name="DirectTaskWorkflow")
class DirectTaskWorkflow:
    """Short-lived workflow that executes a single per-request agent task.

    Started by AgentOrchestrationService.publish_task() for any task that is
    not a workflow-control signal (ADVANCE_STAGE, ESCALATE, etc.). Running as
    a Temporal workflow gives automatic retries, crash recovery, and visibility
    in the Temporal Web UI.
    """

    @workflow.run
    async def run(self, task: TaskPacket) -> TaskResponse:
        activity_fn = _AGENT_ACTIVITY.get(task.to_agent)
        if activity_fn is None:
            raise ApplicationError(
                f"No direct-task activity registered for agent: {task.to_agent!r}",
                non_retryable=True,
            )
        return await workflow.execute_activity(
            activity_fn,
            task,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=_DIRECT_RETRY,
        )
