"""Add trusted contact detail questions (first name, last name, phone, relationship)

Revision ID: 0005_trusted_contact_questions
Revises: 0004_admin_config
Create Date: 2026-05-20

The trusted_contact section already has will_name_trusted_contact (order_index=11).
This migration adds four follow-up questions shown only when that answer is 'Yes',
shifting every question with order_index >= 12 up by 4 to make room.
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0005_trusted_contact_questions"
down_revision = "0004_admin_config"
branch_labels = None
depends_on = None

_QUESTIONNAIRE_ID = "c0000000-0001-0001-0001-000000000001"

_SHOW_IF = json.dumps({"field": "will_name_trusted_contact", "value": "Yes", "operator": "eq"})
_REQUIRED = json.dumps({"required": True})
_EMPTY_OPTS = json.dumps([])
_RELATIONSHIP_OPTS = json.dumps(["Brother", "Father", "Son", "Mother", "Spouse", "Sister", "Daughter"])

_NEW_QUESTIONS = [
    ("trusted_contact_first_name",    "Trusted Contact First Name",    "text",   12, _EMPTY_OPTS),
    ("trusted_contact_last_name",     "Trusted Contact Last Name",     "text",   13, _EMPTY_OPTS),
    ("trusted_contact_phone_number",  "Trusted Contact Phone Number",  "text",   14, _EMPTY_OPTS),
    ("trusted_contact_relationship",  "Trusted Contact Relationship",  "select", 15, _RELATIONSHIP_OPTS),
]


def _esc(s: str) -> str:
    """Escape a string value for embedding in a SQL literal."""
    return s.replace("'", "''")


def upgrade() -> None:
    conn = op.get_bind()

    # Shift existing questions at order_index >= 12 up by 4 to make room
    conn.execute(sa.text(
        f"UPDATE onboarding_questions "
        f"SET order_index = order_index + 4 "
        f"WHERE questionnaire_id = '{_QUESTIONNAIRE_ID}' AND order_index >= 12"
    ))

    for key, text, qtype, order, opts in _NEW_QUESTIONS:
        conn.execute(sa.text(
            f"INSERT INTO onboarding_questions "
            f"(questionnaire_id, section, question_key, question_text, "
            f" question_type, options, validation_rules, show_if, "
            f" order_index, is_required, metadata) "
            f"VALUES ("
            f"  '{_QUESTIONNAIRE_ID}', "
            f"  'trusted_contact', "
            f"  '{_esc(key)}', "
            f"  '{_esc(text)}', "
            f"  '{_esc(qtype)}', "
            f"  '{_esc(opts)}'::jsonb, "
            f"  '{_esc(_REQUIRED)}'::jsonb, "
            f"  '{_esc(_SHOW_IF)}'::jsonb, "
            f"  {order}, "
            f"  TRUE, "
            f"  '{{}}'::jsonb"
            f")"
        ))


def downgrade() -> None:
    conn = op.get_bind()

    keys_list = ", ".join(f"'{k}'" for k, *_ in _NEW_QUESTIONS)
    conn.execute(sa.text(
        f"DELETE FROM onboarding_questions "
        f"WHERE questionnaire_id = '{_QUESTIONNAIRE_ID}' "
        f"AND question_key IN ({keys_list})"
    ))

    conn.execute(sa.text(
        f"UPDATE onboarding_questions "
        f"SET order_index = order_index - 4 "
        f"WHERE questionnaire_id = '{_QUESTIONNAIRE_ID}' AND order_index >= 16"
    ))
