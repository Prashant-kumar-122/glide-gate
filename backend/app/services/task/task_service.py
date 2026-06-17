from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.tasks import WorkspaceTask
from app.models.cases import OnboardingCase
from app.models.clients import Client
from app.models.documents import Document
from app.websocket.socket_emitter import socket_emitter


class TaskService:
    async def create_task(
        self,
        *,
        case_id: UUID,
        assignee_id: UUID | None,
        assignee_role: str,
        task_type: str,
        title: str,
        document_id: UUID | None = None,
        review_id: UUID | None = None,
        db: AsyncSession,
    ) -> WorkspaceTask:
        task = WorkspaceTask(
            id=uuid4(),
            case_id=case_id,
            assignee_id=assignee_id,
            assignee_role=assignee_role,
            task_type=task_type,
            title=title,
            status="PENDING",
            document_id=document_id,
            review_id=review_id,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        payload = await self._task_payload(task, db)
        await socket_emitter.task_created(case_id, payload)

        logger.info(
            f"[TaskService] Task created id={task.id} type={task_type} case={case_id}"
        )
        return task

    async def decide(
        self,
        *,
        task_id: UUID,
        decision: Literal["APPROVED", "REJECTED", "MORE_INFO_REQUESTED"],
        decision_notes: str | None,
        decided_by: UUID | None,
        db: AsyncSession,
    ) -> WorkspaceTask:
        result = await db.execute(
            select(WorkspaceTask).where(WorkspaceTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise ValueError(f"WorkspaceTask {task_id} not found")
        if task.status != "PENDING":
            raise ValueError(
                f"Task {task_id} already decided (status={task.status})"
            )

        task.status = decision
        task.decision_notes = decision_notes
        task.decided_by = decided_by
        task.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # For document-review tasks, sync Document.status so the all-docs-approved
        # trigger in the documents router fires correctly even when the frontend's
        # secondary PATCH /documents/{id} call fails or arrives out of order.
        if task.task_type == "DOCUMENT_REVIEW" and task.document_id:
            doc_status = "APPROVED" if decision == "APPROVED" else (
                "NEEDS_REVISION" if decision == "REJECTED" else None
            )
            if doc_status:
                doc_result = await db.execute(
                    select(Document).where(Document.id == task.document_id)
                )
                doc = doc_result.scalar_one_or_none()
                if doc is not None and doc.status != doc_status:
                    doc.status = doc_status

        await db.commit()
        await db.refresh(task)

        payload = await self._task_payload(task, db)
        await socket_emitter.task_updated(task.case_id, payload)

        # If this was the last pending document task for the case, trigger
        # the REVIEW → KYC (or SALES_REVIEW) advance via the same logic used
        # by the document-status endpoint.
        if task.task_type == "DOCUMENT_REVIEW" and decision == "APPROVED":
            asyncio.create_task(
                self._maybe_advance_from_review(task.case_id),
                name=f"advance-review-{task.case_id}",
            )

        logger.info(
            f"[TaskService] Task decided id={task_id} decision={decision}"
        )
        return task

    async def list_tasks(
        self,
        *,
        assignee_role: str,
        assignee_id: UUID | None = None,
        case_id: UUID | None = None,
        db: AsyncSession,
    ) -> list[WorkspaceTask]:
        query = select(WorkspaceTask).where(
            WorkspaceTask.assignee_role == assignee_role
        )
        if assignee_id is not None:
            query = query.where(WorkspaceTask.assignee_id == assignee_id)
        if case_id is not None:
            query = query.where(WorkspaceTask.case_id == case_id)
        query = query.order_by(WorkspaceTask.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_task(self, task_id: UUID, db: AsyncSession) -> WorkspaceTask | None:
        result = await db.execute(
            select(WorkspaceTask).where(WorkspaceTask.id == task_id)
        )
        return result.scalar_one_or_none()

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _maybe_advance_from_review(self, case_id: UUID) -> None:
        """Safety-net: if all DOCUMENT_REVIEW tasks for the case are APPROVED and
        the case is still in REVIEW, send the advance_stage Temporal signal.

        Checks WorkspaceTask statuses (not Document.status) because task status is
        authoritative here — Document.status may lag if the frontend's secondary
        PATCH /documents/{id} call failed or was skipped (e.g. document_id is null).
        Temporal owns stage transitions; we do NOT touch current_stage in the DB here.
        """
        async with AsyncSessionLocal() as db:
            try:
                case_result = await db.execute(
                    select(OnboardingCase).where(OnboardingCase.id == case_id)
                )
                case = case_result.scalar_one_or_none()
                if not case or case.current_stage != "REVIEW":
                    return

                tasks_result = await db.execute(
                    select(WorkspaceTask)
                    .where(WorkspaceTask.case_id == case_id)
                    .where(WorkspaceTask.task_type == "DOCUMENT_REVIEW")
                )
                doc_tasks = tasks_result.scalars().all()
                if not doc_tasks:
                    return
                if not all(t.status == "APPROVED" for t in doc_tasks):
                    return

                from app.models.cases import Product
                from app.agents.base.a2a_types import (
                    AgentID, OnboardingStage, TaskPacket, TaskType,
                )
                from app.services.orchestration.agent_orchestration_service import (
                    orchestration_service,
                )

                selected = case.selected_products or []
                has_institutional = False
                if selected:
                    inst_result = await db.execute(
                        select(Product).where(
                            Product.product_code.in_(selected),
                            Product.product_type == "institutional",
                        )
                    )
                    has_institutional = inst_result.scalar_one_or_none() is not None

                to_stage = (
                    OnboardingStage.SALES_REVIEW if has_institutional else OnboardingStage.KYC
                )
                shared_ctx = dict(case.shared_context or {})
                case_name = (case.extra_metadata or {}).get("case_name") or f"Case {str(case_id)[:8]}"

                logger.info(
                    f"[TaskService] All doc tasks approved for case={case_id} "
                    f"→ advancing to {to_stage}"
                )

                await orchestration_service.publish_task(
                    TaskPacket(
                        from_agent=AgentID.ORCHESTRATOR,
                        to_agent=AgentID.ORCHESTRATOR,
                        task_type=TaskType.ADVANCE_STAGE,
                        case_id=case_id,
                        client_id=case.client_id,
                        priority="HIGH",
                        payload={
                            "to_stage": to_stage,
                            "client_data": shared_ctx.get("client_data", {}),
                            "selected_products": selected,
                            "case_name": case_name,
                        },
                    )
                )
            except Exception as exc:
                logger.warning(
                    f"[TaskService] _maybe_advance_from_review failed case={case_id}: {exc}"
                )

    async def _task_payload(self, task: WorkspaceTask, db: AsyncSession) -> dict:
        case_result = await db.execute(
            select(OnboardingCase)
            .options(selectinload(OnboardingCase.client))
            .where(OnboardingCase.id == task.case_id)
        )
        case = case_result.scalar_one_or_none()
        case_name = ((case.extra_metadata or {}).get("case_name") or "") if case else ""
        client_name = ""
        if case and hasattr(case, "client") and case.client:
            c = case.client
            client_name = f"{c.first_name} {c.last_name}".strip()

        return {
            "task_id": str(task.id),
            "case_id": str(task.case_id),
            "assignee_role": task.assignee_role,
            "task_type": task.task_type,
            "title": task.title,
            "status": task.status,
            "case_name": case_name,
            "client_name": client_name,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }


task_service = TaskService()
