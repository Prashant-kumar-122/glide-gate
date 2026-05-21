"""Create client_accounts table

Revision ID: 0006_client_accounts
Revises: 0005_trusted_contact_questions
Create Date: 2026-05-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_client_accounts"
down_revision = "0005_trusted_contact_questions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("onboarding_cases.id"), nullable=False),
        sa.Column("products", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("account_number", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", name="client_accounts_case_id_uq"),
        sa.UniqueConstraint("account_number", name="client_accounts_number_uq"),
    )
    op.create_index("ix_client_accounts_client_id", "client_accounts", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_client_accounts_client_id", table_name="client_accounts")
    op.drop_table("client_accounts")
