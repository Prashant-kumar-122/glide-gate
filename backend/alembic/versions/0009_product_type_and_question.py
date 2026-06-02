"""Add product_type to products and product_id to onboarding_questions

Revision ID: 0009_product_type_and_question
Revises: b8acf771a6d9
Create Date: 2026-06-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_product_type_and_question"
down_revision = "b8acf771a6d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add product_type column to products (default 'retail' covers existing rows)
    op.add_column(
        "products",
        sa.Column(
            "product_type",
            sa.String(20),
            nullable=False,
            server_default="retail",
        ),
    )
    op.create_check_constraint(
        "products_type_chk",
        "products",
        "product_type IN ('retail', 'institutional')",
    )

    # 2. Add product_id FK column to onboarding_questions (nullable — NULL = universal)
    op.add_column(
        "onboarding_questions",
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_onboarding_questions_product_id",
        "onboarding_questions",
        ["product_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_onboarding_questions_product_id", "onboarding_questions")
    op.drop_column("onboarding_questions", "product_id")
    op.drop_constraint("products_type_chk", "products", type_="check")
    op.drop_column("products", "product_type")
