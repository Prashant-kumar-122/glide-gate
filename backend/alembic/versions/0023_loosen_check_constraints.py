"""Phase 8: Drop hardcoded DB CHECK constraints on stage/status/product_type.

These constraints enforced a fixed vocabulary (INTAKE, KYC, ...) at the DB
layer.  After this migration, validation is enforced at the application layer
by ContextStoreService (stage values validated against domain_stages rows) and
the domain_products table (product_type is now a free-form label defined per
domain, not a DB-enforced enum).

Constraints dropped:
  - oc_status_chk    (onboarding_cases.status)
  - oc_stage_chk     (onboarding_cases.current_stage)
  - products_type_chk (products.product_type)

Revision ID: 0023_loosen_check_constraints
Revises: 0022_user_personas
Create Date: 2026-06-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0023_loosen_check_constraints"
down_revision = "0022_user_personas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("oc_status_chk", "onboarding_cases", type_="check")
    op.drop_constraint("oc_stage_chk", "onboarding_cases", type_="check")
    op.drop_constraint("products_type_chk", "products", type_="check")


def downgrade() -> None:
    _stages = "('INTAKE','SALES_REVIEW','KYC','PARALLEL_PRODUCTS','REVIEW','COMPLETE','ESCALATED')"
    op.create_check_constraint("oc_status_chk", "onboarding_cases", f"status IN {_stages}")
    op.create_check_constraint("oc_stage_chk", "onboarding_cases", f"current_stage IN {_stages}")
    op.create_check_constraint(
        "products_type_chk", "products", "product_type IN ('retail', 'institutional')"
    )
