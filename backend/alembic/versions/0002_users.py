"""Add users table for auth

Revision ID: 0002_users
Revises: 0001_initial
Create Date: 2026-05-14

BRD: Section 9.1, FR-01, Section 10.2
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_users"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), server_default="client", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('client', 'advisor', 'admin')", name="users_role_check"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_role", "users", ["role"])
    op.create_index("idx_users_active", "users", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_users_active", table_name="users")
    op.drop_index("idx_users_role", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
