"""add_fk_indexes

Revision ID: b8acf771a6d9
Revises: 0008_notifications_user_id
Create Date: 2026-05-28 15:15:30.735360

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b8acf771a6d9'
down_revision: Union[str, None] = '0008_notifications_user_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # agent_tasks
    op.drop_index('idx_at_case_id', table_name='agent_tasks')
    op.drop_index('idx_at_status', table_name='agent_tasks')
    op.create_index(op.f('ix_agent_tasks_case_id'), 'agent_tasks', ['case_id'], unique=False)
    op.create_index(op.f('ix_agent_tasks_client_id'), 'agent_tasks', ['client_id'], unique=False)
    op.create_index(op.f('ix_agent_tasks_status'), 'agent_tasks', ['status'], unique=False)

    # case_product_steps
    op.drop_index('idx_cps_case_product_id', table_name='case_product_steps')
    op.create_index(op.f('ix_case_product_steps_case_product_id'), 'case_product_steps', ['case_product_id'], unique=False)

    # case_products
    op.drop_index('idx_case_products_case_id', table_name='case_products')
    op.drop_index('idx_case_products_status', table_name='case_products')
    op.create_index(op.f('ix_case_products_case_id'), 'case_products', ['case_id'], unique=False)
    op.create_index(op.f('ix_case_products_product_id'), 'case_products', ['product_id'], unique=False)

    # case_summaries
    op.drop_index('idx_cs_case_id', table_name='case_summaries')
    op.create_index(op.f('ix_case_summaries_case_id'), 'case_summaries', ['case_id'], unique=False)

    # collaboration_comments
    op.drop_index('idx_cc_case_id', table_name='collaboration_comments')
    op.drop_index('idx_cc_room_id', table_name='collaboration_comments')
    op.create_index(op.f('ix_collaboration_comments_case_id'), 'collaboration_comments', ['case_id'], unique=False)
    op.create_index(op.f('ix_collaboration_comments_document_id'), 'collaboration_comments', ['document_id'], unique=False)
    op.create_index(op.f('ix_collaboration_comments_parent_id'), 'collaboration_comments', ['parent_id'], unique=False)
    op.create_index(op.f('ix_collaboration_comments_room_id'), 'collaboration_comments', ['room_id'], unique=False)

    # collaboration_participants
    op.drop_index('idx_cpart_room_id', table_name='collaboration_participants')
    op.create_index(op.f('ix_collaboration_participants_room_id'), 'collaboration_participants', ['room_id'], unique=False)

    # collaboration_rooms
    op.drop_index('idx_cr_case_id', table_name='collaboration_rooms')
    op.create_index(op.f('ix_collaboration_rooms_case_id'), 'collaboration_rooms', ['case_id'], unique=False)

    # conversation_messages
    op.drop_index('idx_cm_case_id', table_name='conversation_messages')
    op.create_index(op.f('ix_conversation_messages_case_id'), 'conversation_messages', ['case_id'], unique=False)
    op.create_index(op.f('ix_conversation_messages_client_id'), 'conversation_messages', ['client_id'], unique=False)

    # documents — rename existing + add parent_doc_id index
    op.drop_index('idx_docs_case_id', table_name='documents')
    op.drop_index('idx_docs_category', table_name='documents')
    op.drop_index('idx_docs_client_id', table_name='documents')
    op.drop_index('idx_docs_status', table_name='documents')
    op.create_index(op.f('ix_documents_case_id'), 'documents', ['case_id'], unique=False)
    op.create_index(op.f('ix_documents_category'), 'documents', ['category'], unique=False)
    op.create_index(op.f('ix_documents_client_id'), 'documents', ['client_id'], unique=False)
    op.create_index(op.f('ix_documents_parent_doc_id'), 'documents', ['parent_doc_id'], unique=False)
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)

    # event_logs
    op.create_index(op.f('ix_event_logs_case_id'), 'event_logs', ['case_id'], unique=False)
    op.create_index(op.f('ix_event_logs_client_id'), 'event_logs', ['client_id'], unique=False)

    # human_reviews
    op.drop_index('idx_hr_case_id', table_name='human_reviews')
    op.create_index(op.f('ix_human_reviews_case_id'), 'human_reviews', ['case_id'], unique=False)
    op.create_index(op.f('ix_human_reviews_kyc_check_id'), 'human_reviews', ['kyc_check_id'], unique=False)

    # kyc_checks
    op.drop_index('idx_kyc_case_id', table_name='kyc_checks')
    op.create_index(op.f('ix_kyc_checks_case_id'), 'kyc_checks', ['case_id'], unique=False)
    op.create_index(op.f('ix_kyc_checks_client_id'), 'kyc_checks', ['client_id'], unique=False)

    # mcp_tool_calls
    op.create_index(op.f('ix_mcp_tool_calls_case_id'), 'mcp_tool_calls', ['case_id'], unique=False)

    # notifications — rename existing user_id index
    op.drop_index('idx_notif_user_id', table_name='notifications')
    op.create_index(op.f('ix_notifications_case_id'), 'notifications', ['case_id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)

    # onboarding_answers
    op.drop_index('idx_oa_case_id', table_name='onboarding_answers')
    op.drop_index('idx_oa_client_id', table_name='onboarding_answers')
    op.create_index(op.f('ix_onboarding_answers_case_id'), 'onboarding_answers', ['case_id'], unique=False)
    op.create_index(op.f('ix_onboarding_answers_client_id'), 'onboarding_answers', ['client_id'], unique=False)
    op.create_index(op.f('ix_onboarding_answers_question_id'), 'onboarding_answers', ['question_id'], unique=False)
    op.create_index(op.f('ix_onboarding_answers_questionnaire_id'), 'onboarding_answers', ['questionnaire_id'], unique=False)

    # onboarding_cases
    op.drop_index('idx_oc_client_id', table_name='onboarding_cases')
    op.drop_index('idx_oc_current_stage', table_name='onboarding_cases')
    op.drop_index('idx_oc_status', table_name='onboarding_cases')
    op.create_index(op.f('ix_onboarding_cases_assigned_advisor_id'), 'onboarding_cases', ['assigned_advisor_id'], unique=False)
    op.create_index(op.f('ix_onboarding_cases_client_id'), 'onboarding_cases', ['client_id'], unique=False)
    op.create_index(op.f('ix_onboarding_cases_current_stage'), 'onboarding_cases', ['current_stage'], unique=False)
    op.create_index(op.f('ix_onboarding_cases_status'), 'onboarding_cases', ['status'], unique=False)

    # onboarding_question_rules
    op.drop_index('idx_oqr_question_id', table_name='onboarding_question_rules')
    op.create_index(op.f('ix_onboarding_question_rules_question_id'), 'onboarding_question_rules', ['question_id'], unique=False)

    # onboarding_question_sessions
    op.drop_index('idx_oqs_case_id', table_name='onboarding_question_sessions')
    op.create_index(op.f('ix_onboarding_question_sessions_case_id'), 'onboarding_question_sessions', ['case_id'], unique=False)
    op.create_index(op.f('ix_onboarding_question_sessions_client_id'), 'onboarding_question_sessions', ['client_id'], unique=False)
    op.create_index(op.f('ix_onboarding_question_sessions_questionnaire_id'), 'onboarding_question_sessions', ['questionnaire_id'], unique=False)

    # onboarding_questions
    op.drop_index('idx_oqn_questionnaire_id', table_name='onboarding_questions')
    op.create_index(op.f('ix_onboarding_questions_questionnaire_id'), 'onboarding_questions', ['questionnaire_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_onboarding_questions_questionnaire_id'), table_name='onboarding_questions')
    op.create_index('idx_oqn_questionnaire_id', 'onboarding_questions', ['questionnaire_id'], unique=False)

    op.drop_index(op.f('ix_onboarding_question_sessions_questionnaire_id'), table_name='onboarding_question_sessions')
    op.drop_index(op.f('ix_onboarding_question_sessions_client_id'), table_name='onboarding_question_sessions')
    op.drop_index(op.f('ix_onboarding_question_sessions_case_id'), table_name='onboarding_question_sessions')
    op.create_index('idx_oqs_case_id', 'onboarding_question_sessions', ['case_id'], unique=False)

    op.drop_index(op.f('ix_onboarding_question_rules_question_id'), table_name='onboarding_question_rules')
    op.create_index('idx_oqr_question_id', 'onboarding_question_rules', ['question_id'], unique=False)

    op.drop_index(op.f('ix_onboarding_cases_status'), table_name='onboarding_cases')
    op.drop_index(op.f('ix_onboarding_cases_current_stage'), table_name='onboarding_cases')
    op.drop_index(op.f('ix_onboarding_cases_client_id'), table_name='onboarding_cases')
    op.drop_index(op.f('ix_onboarding_cases_assigned_advisor_id'), table_name='onboarding_cases')
    op.create_index('idx_oc_status', 'onboarding_cases', ['status'], unique=False)
    op.create_index('idx_oc_current_stage', 'onboarding_cases', ['current_stage'], unique=False)
    op.create_index('idx_oc_client_id', 'onboarding_cases', ['client_id'], unique=False)

    op.drop_index(op.f('ix_onboarding_answers_questionnaire_id'), table_name='onboarding_answers')
    op.drop_index(op.f('ix_onboarding_answers_question_id'), table_name='onboarding_answers')
    op.drop_index(op.f('ix_onboarding_answers_client_id'), table_name='onboarding_answers')
    op.drop_index(op.f('ix_onboarding_answers_case_id'), table_name='onboarding_answers')
    op.create_index('idx_oa_client_id', 'onboarding_answers', ['client_id'], unique=False)
    op.create_index('idx_oa_case_id', 'onboarding_answers', ['case_id'], unique=False)

    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_case_id'), table_name='notifications')
    op.create_index('idx_notif_user_id', 'notifications', ['user_id'], unique=False)

    op.drop_index(op.f('ix_mcp_tool_calls_case_id'), table_name='mcp_tool_calls')

    op.drop_index(op.f('ix_kyc_checks_client_id'), table_name='kyc_checks')
    op.drop_index(op.f('ix_kyc_checks_case_id'), table_name='kyc_checks')
    op.create_index('idx_kyc_case_id', 'kyc_checks', ['case_id'], unique=False)

    op.drop_index(op.f('ix_human_reviews_kyc_check_id'), table_name='human_reviews')
    op.drop_index(op.f('ix_human_reviews_case_id'), table_name='human_reviews')
    op.create_index('idx_hr_case_id', 'human_reviews', ['case_id'], unique=False)

    op.drop_index(op.f('ix_event_logs_client_id'), table_name='event_logs')
    op.drop_index(op.f('ix_event_logs_case_id'), table_name='event_logs')

    op.drop_index(op.f('ix_documents_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_parent_doc_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_client_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_category'), table_name='documents')
    op.drop_index(op.f('ix_documents_case_id'), table_name='documents')
    op.create_index('idx_docs_status', 'documents', ['status'], unique=False)
    op.create_index('idx_docs_client_id', 'documents', ['client_id'], unique=False)
    op.create_index('idx_docs_category', 'documents', ['category'], unique=False)
    op.create_index('idx_docs_case_id', 'documents', ['case_id'], unique=False)

    op.drop_index(op.f('ix_conversation_messages_client_id'), table_name='conversation_messages')
    op.drop_index(op.f('ix_conversation_messages_case_id'), table_name='conversation_messages')
    op.create_index('idx_cm_case_id', 'conversation_messages', ['case_id'], unique=False)

    op.drop_index(op.f('ix_collaboration_rooms_case_id'), table_name='collaboration_rooms')
    op.create_index('idx_cr_case_id', 'collaboration_rooms', ['case_id'], unique=False)

    op.drop_index(op.f('ix_collaboration_participants_room_id'), table_name='collaboration_participants')
    op.create_index('idx_cpart_room_id', 'collaboration_participants', ['room_id'], unique=False)

    op.drop_index(op.f('ix_collaboration_comments_room_id'), table_name='collaboration_comments')
    op.drop_index(op.f('ix_collaboration_comments_parent_id'), table_name='collaboration_comments')
    op.drop_index(op.f('ix_collaboration_comments_document_id'), table_name='collaboration_comments')
    op.drop_index(op.f('ix_collaboration_comments_case_id'), table_name='collaboration_comments')
    op.create_index('idx_cc_room_id', 'collaboration_comments', ['room_id'], unique=False)
    op.create_index('idx_cc_case_id', 'collaboration_comments', ['case_id'], unique=False)

    op.drop_index(op.f('ix_case_summaries_case_id'), table_name='case_summaries')
    op.create_index('idx_cs_case_id', 'case_summaries', ['case_id'], unique=False)

    op.drop_index(op.f('ix_case_products_product_id'), table_name='case_products')
    op.drop_index(op.f('ix_case_products_case_id'), table_name='case_products')
    op.create_index('idx_case_products_status', 'case_products', ['status'], unique=False)
    op.create_index('idx_case_products_case_id', 'case_products', ['case_id'], unique=False)

    op.drop_index(op.f('ix_case_product_steps_case_product_id'), table_name='case_product_steps')
    op.create_index('idx_cps_case_product_id', 'case_product_steps', ['case_product_id'], unique=False)

    op.drop_index(op.f('ix_agent_tasks_status'), table_name='agent_tasks')
    op.drop_index(op.f('ix_agent_tasks_client_id'), table_name='agent_tasks')
    op.drop_index(op.f('ix_agent_tasks_case_id'), table_name='agent_tasks')
    op.create_index('idx_at_status', 'agent_tasks', ['status'], unique=False)
    op.create_index('idx_at_case_id', 'agent_tasks', ['case_id'], unique=False)
