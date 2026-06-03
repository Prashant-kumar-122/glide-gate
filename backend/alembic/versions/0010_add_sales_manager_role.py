"""Add sales_manager to users role constraint

Revision ID: 0010_add_sales_manager_role
Revises: b8acf771a6d9
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_add_sales_manager_role"
down_revision = "0009_product_type_and_question"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("users_role_check", "users", type_="check")
    op.create_check_constraint(
        "users_role_check",
        "users",
        "role IN ('client', 'advisor', 'admin', 'sales_manager')",
    )


def downgrade() -> None:
    op.drop_constraint("users_role_check", "users", type_="check")
    op.create_check_constraint(
        "users_role_check",
        "users",
        "role IN ('client', 'advisor', 'admin')",
    )
