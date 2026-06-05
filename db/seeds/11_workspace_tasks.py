"""Seed: Demo workspace tasks for the sample case."""
from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.tasks import WorkspaceTask

CASE_ID             = UUID("e0000000-0001-0001-0001-000000000001")
ADVISOR_USER_ID     = UUID("b0000000-0002-0002-0002-000000000002")
SALES_MANAGER_ID    = UUID("b0000000-0003-0003-0003-000000000003")

TASK_DOC_ID  = UUID("a0000011-0001-0001-0001-000000000001")
TASK_SALE_ID = UUID("a0000011-0002-0002-0002-000000000002")

_TASKS = [
    WorkspaceTask(
        id=TASK_DOC_ID,
        case_id=CASE_ID,
        assignee_id=ADVISOR_USER_ID,
        assignee_role="advisor",
        task_type="DOCUMENT_REVIEW",
        title="Review uploaded document: Passport_AaravMehta.pdf",
        status="PENDING",
    ),
    WorkspaceTask(
        id=TASK_SALE_ID,
        case_id=CASE_ID,
        assignee_id=SALES_MANAGER_ID,
        assignee_role="sales_manager",
        task_type="SALES_REVIEW",
        title="Sales Manager Review Required",
        status="PENDING",
    ),
]


async def seed(session: AsyncSession) -> None:
    existing = await session.get(WorkspaceTask, TASK_DOC_ID)
    if existing:
        print("  [skip] workspace_tasks already seeded")
        return

    for task in _TASKS:
        session.add(task)
        print(f"  [seed] workspace_task {task.id} ({task.task_type} / {task.assignee_role})")

    await session.commit()


if __name__ == "__main__":
    async def main() -> None:
        async with AsyncSessionLocal() as session:
            await seed(session)

    asyncio.run(main())
