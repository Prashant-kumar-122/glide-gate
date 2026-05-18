"""Persist admin configuration to DB (validation prompt overrides + LLM config)

Revision ID: 0004_admin_config
Revises: 0003_case_percentage
Create Date: 2026-05-18

Replaces the two in-memory dicts that were lost on every server restart:
  - prompt_override_store._prompt_overrides  (validation prompt overrides per category)
  - deterministic_controls_applier._active_overrides  (LLM provider / model / params)

Both are stored as JSONB blobs in a single admin_config table, keyed by namespace.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_admin_config"
down_revision = "0003_case_percentage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_config",
        sa.Column("namespace", sa.String(50), primary_key=True),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("admin_config")
