"""Add domain_id to onboarding_cases for multi-domain case isolation

Revision ID: 0029_case_domain_id
Revises: 0028_domain_product_description
Create Date: 2026-06-18

Every case is now stamped with the domain that was active when it was created.
list_cases filters by the user's domain membership (derived from their persona codes
in domain_personas) so that, e.g., deposit_ops users only see retail_deposit cases
and advisor users only see wealth_management cases.  Admin users bypass the filter.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0029_case_domain_id"
down_revision = "0028_domain_product_desc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "onboarding_cases",
        sa.Column(
            "domain_id",
            sa.UUID(),
            sa.ForeignKey("domains.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_onboarding_cases_domain_id", "onboarding_cases", ["domain_id"])

    # Backfill: all cases created before multi-domain support belong to wealth_management.
    op.execute(sa.text("""
        UPDATE onboarding_cases
        SET domain_id = d.id
        FROM domains d
        WHERE d.domain_code = 'wealth_management'
          AND onboarding_cases.domain_id IS NULL
    """))


def downgrade() -> None:
    op.drop_index("ix_onboarding_cases_domain_id", table_name="onboarding_cases")
    op.drop_column("onboarding_cases", "domain_id")
