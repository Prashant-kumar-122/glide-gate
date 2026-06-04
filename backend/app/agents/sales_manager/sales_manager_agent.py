from __future__ import annotations

from typing import Any
from uuid import UUID

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskResponse, TaskType
from app.agents.base.base_agent import BaseAgent


class SalesManagerAgent(BaseAgent):
    """Sales Manager Review Agent — human-in-the-loop for institutional onboarding.

    Handles:
    - SALES_MANAGER_REVIEW: Receives a case entering SALES_REVIEW stage.
      Persists a SalesManagerReview record, generates an AI risk summary,
      notifies the Sales Manager, and waits for a human decision via the API.
    """

    agent_id = AgentID.SALES_MANAGER

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)

    async def process(self, task: TaskPacket) -> TaskResponse:
        handlers = {
            TaskType.SALES_MANAGER_REVIEW: self._handle_review,
            TaskType.HEALTH_CHECK: self._handle_health_check,
        }
        handler = handlers.get(task.task_type)
        if handler is None:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=[f"Unsupported task_type: {task.task_type}"],
            )
        return await handler(task)

    # ── Handlers ─────────────────────────────────────────────────────────────

    async def _handle_review(self, task: TaskPacket) -> TaskResponse:
        from app.database import AsyncSessionLocal
        from app.services.sales_review.sales_review_service import sales_review_service

        case_id = task.case_id
        client_id = task.client_id

        self.logger.info(f"[SalesManagerAgent] Initiating sales review for case={case_id}")

        async with AsyncSessionLocal() as db:
            try:
                review = await sales_review_service.create_review(
                    case_id=case_id,
                    client_id=client_id,
                    payload=task.payload,
                    db=db,
                )
                review_id = review.id
                ai_summary = review.ai_risk_summary or ""
                risk_score = review.risk_score
            except Exception as exc:
                self.logger.error(
                    f"[SalesManagerAgent] Failed to create review for case={case_id}: {exc}"
                )
                return TaskResponse(
                    task_id=task.id,
                    from_agent=self.agent_id,
                    status="FAILED",
                    errors=[str(exc)],
                )

        # Notify the Sales Manager in-app
        await self.send_task(
            TaskPacket(
                from_agent=self.agent_id,
                to_agent=AgentID.NOTIFICATION,
                task_type=TaskType.SEND_NOTIFICATION,
                case_id=case_id,
                client_id=client_id,
                priority="HIGH",
                payload={
                    "template": "sales_review_assigned",
                    "review_id": str(review_id),
                    "case_name": task.payload.get("case_name", ""),
                    "client_name": task.payload.get("client_name", ""),
                    "selected_products": task.payload.get("selected_products", []),
                    "risk_score": risk_score,
                },
            )
        )

        self.logger.info(
            f"[SalesManagerAgent] Sales review created review_id={review_id} case={case_id}"
        )
        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={
                "review_id": str(review_id),
                "case_id": str(case_id),
                "ai_risk_summary": ai_summary,
                "risk_score": risk_score,
                "status": "PENDING",
            },
        )

    async def _handle_health_check(self, task: TaskPacket) -> TaskResponse:
        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={"status": "healthy"},
        )
