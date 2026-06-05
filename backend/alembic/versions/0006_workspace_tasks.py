"""Add workspace_tasks table

Revision ID: 0006_workspace_tasks
Revises: 0005_sales_review
Create Date: 2026-06-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_workspace_tasks"
down_revision = "0005_sales_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    from sqlalchemy import inspect as sa_inspect
    if "workspace_tasks" in sa_inspect(bind).get_table_names():
        return

    op.create_table(
        "workspace_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("onboarding_cases.id"),
            nullable=False,
        ),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assignee_role", sa.String(20), nullable=False),
        sa.Column("task_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=True,
        ),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision_notes", sa.Text, nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime, nullable=True),
        sa.Column(
            "metadata", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "task_type IN ('DOCUMENT_REVIEW','SALES_REVIEW')", name="wt_type_chk"
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED','MORE_INFO_REQUESTED')",
            name="wt_status_chk",
        ),
        sa.CheckConstraint(
            "assignee_role IN ('advisor','sales_manager')", name="wt_role_chk"
        ),
    )
    op.create_index("ix_workspace_tasks_case_id", "workspace_tasks", ["case_id"])
    op.create_index(
        "ix_workspace_tasks_assignee_id", "workspace_tasks", ["assignee_id"]
    )
    op.create_index("ix_workspace_tasks_status", "workspace_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_workspace_tasks_status", table_name="workspace_tasks")
    op.drop_index("ix_workspace_tasks_assignee_id", table_name="workspace_tasks")
    op.drop_index("ix_workspace_tasks_case_id", table_name="workspace_tasks")
    op.drop_table("workspace_tasks")
