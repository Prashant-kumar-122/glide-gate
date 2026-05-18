from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.agents.base.a2a_types import AgentID, OnboardingStage, TaskPacket, TaskType
from app.agents.customer_service.intent_classifier import Intent, IntentClassifier
from app.database import AsyncSessionLocal
from app.models.communications import ConversationMessage
from app.models.questionnaire import OnboardingAnswer, OnboardingQuestionSession
from app.services.context_store.context_store_service import context_store
from app.services.conversation.session_manager import ConversationSession, session_manager
from app.services.conversation.streaming_response_service import streaming_response_service

_MAX_HISTORY = 20

# Varied fallback phrasings used when LLM is unavailable (indexed by label hash for determinism)
_FALLBACK_TEMPLATES = [
    "Could you please share your {label}?",
    "I'll need your {label} to continue — could you provide that?",
    "What is your {label}?",
    "To move forward, could you tell me your {label}?",
    "We just need your {label} — could you share it with me?",
]


class ConversationCoordinator:
    """
    Coordinates the streaming conversational onboarding interface.

    Per request:
      1. Resolves or creates a per-case session (DCO + memory).
      2. Loads questions from DB into DCO on first use (falls back to hardcoded).
      3. Extracts field values from the user message and persists them to:
         - ContextStoreService (onboarding_cases.shared_context JSONB)
         - onboarding_answers table (one row per question per case, upsert)
         - onboarding_question_sessions table (progress tracking)
      4. Loads DB message history and augments the user turn with a guidance note.
      5. Delegates streaming to StreamingResponseService (real Anthropic streaming).
      6. Persists the assistant reply to DB after streaming completes.
      7. Signals OrchestratorAgent to advance to KYC when all fields are collected.
    """

    def __init__(self) -> None:
        self._classifier = IntentClassifier()

    async def handle_message(
        self,
        case_id: UUID,
        client_id: UUID,
        user_message: str,
        session_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        session = await self._resolve_session(case_id, client_id)
        validation_error = await self._extract_and_persist(case_id, user_message, session)

        status = session.dco.status(case_id)
        next_field = session.dco.next_field(case_id)

        history = await self._load_history(case_id)
        guided_msg = self._build_guided_message(
            user_message, next_field, status.is_complete, validation_error
        )
        messages = history + [{"role": "user", "content": guided_msg}]

        full_text = ""
        input_tokens = 0
        output_tokens = 0
        fallback = self._build_fallback_text(next_field, status.is_complete, validation_error)

        async for sse_line in streaming_response_service.stream_reply(
            messages, case_id=case_id, fallback_text=fallback
        ):
            yield sse_line
            if sse_line.startswith("data: "):
                try:
                    payload = json.loads(sse_line[6:].strip())
                    if payload.get("type") == "token":
                        full_text += payload.get("token", "")
                    elif payload.get("type") == "end":
                        input_tokens = payload.get("input_tokens", 0)
                        output_tokens = payload.get("output_tokens", 0)
                except json.JSONDecodeError:
                    pass

        if full_text:
            session.memory.add(case_id, "assistant", full_text)
            asyncio.create_task(
                self._persist_assistant(case_id, client_id, full_text, input_tokens, output_tokens)
            )

        # After streaming, emit the options for the next question so the frontend
        # can render them as clickable chips instead of plain text.
        if not status.is_complete and next_field and next_field.options:
            yield (
                f"data: {json.dumps({'type': 'options', 'field_id': next_field.field_id, 'options': next_field.options})}\n\n"
            )

        # Emit questionnaire progress so the frontend progress bar updates in real-time.
        yield f"data: {json.dumps({'type': 'progress', 'questionnaire_pct': status.completion_pct})}\n\n"

        if status.is_complete and not session._advance_sent:
            session._advance_sent = True
            asyncio.create_task(
                self._signal_advance(case_id, client_id, status.collected_fields)
            )

    async def handle_greeting(
        self,
        case_id: UUID,
        client_id: UUID,
    ) -> AsyncGenerator[str, None]:
        """Stream an initial greeting when the client opens a fresh conversation."""
        session = await self._resolve_session(case_id, client_id)
        first_field = session.dco.next_field(case_id)

        if first_field:
            guided = (
                f"[CONTEXT: This is the very first message to the client. "
                f"Greet them warmly, introduce yourself as GlideGate's onboarding assistant, "
                f"briefly explain you will be collecting some information to open their account, "
                f"and then ask them to provide their {first_field.label}. "
                f"Keep it to 3–4 sentences. Ask only this one question.]"
            )
            fallback = (
                f"Welcome to GlideGate! I'm your onboarding assistant, here to help you "
                f"complete your application. Let's get started — could you please share your "
                f"{first_field.label}?"
            )
        else:
            guided = (
                "[CONTEXT: Greet the client and let them know their onboarding information "
                "is complete and next steps will follow shortly.]"
            )
            fallback = (
                "Welcome back! Your onboarding information is complete. "
                "We will be in touch shortly with next steps."
            )

        messages = [{"role": "user", "content": guided}]
        full_text = ""

        async for sse_line in streaming_response_service.stream_reply(
            messages, case_id=case_id, fallback_text=fallback
        ):
            yield sse_line
            if sse_line.startswith("data: "):
                try:
                    payload = json.loads(sse_line[6:].strip())
                    if payload.get("type") == "token":
                        full_text += payload.get("token", "")
                except json.JSONDecodeError:
                    pass

        if full_text:
            session.memory.add(case_id, "assistant", full_text)
            asyncio.create_task(
                self._persist_assistant(case_id, client_id, full_text, 0, 0)
            )

        if first_field and first_field.options:
            yield (
                f"data: {json.dumps({'type': 'options', 'field_id': first_field.field_id, 'options': first_field.options})}\n\n"
            )

        # Emit initial questionnaire progress (0% on fresh start).
        greeting_status = session.dco.status(case_id)
        yield f"data: {json.dumps({'type': 'progress', 'questionnaire_pct': greeting_status.completion_pct})}\n\n"

    # ── Session resolution ────────────────────────────────────────────────────

    async def _resolve_session(self, case_id: UUID, client_id: UUID) -> ConversationSession:
        existing = session_manager.get(case_id)
        if existing:
            # Load DB questions if not yet loaded for this case (e.g. after server restart)
            if not existing.dco.is_db_loaded(case_id):
                async with AsyncSessionLocal() as db:
                    await existing.dco.load_questions_from_db(case_id, db)
            return existing

        selected_products: list[str] = []
        existing_data: dict = {}
        try:
            state = await context_store.get(case_id)
            selected_products = state.selected_products
            existing_data = state.client_data or {}
        except Exception as exc:
            logger.warning(f"ConversationCoordinator: context load failed for {case_id}: {exc}")

        session = session_manager.get_or_create(case_id, client_id, selected_products)

        # Load questions from DB into this session's DCO
        async with AsyncSessionLocal() as db:
            await session.dco.load_questions_from_db(case_id, db)

        # Hydrate already-collected fields from ContextStore
        for field_id, value in existing_data.items():
            if value is not None:
                session.dco.update(case_id, field_id, value)

        return session

    # ── Data extraction ───────────────────────────────────────────────────────

    async def _extract_and_persist(
        self, case_id: UUID, user_message: str, session: ConversationSession
    ) -> str | None:
        """Returns a validation error string if the provided value was invalid, else None."""
        session.memory.add(case_id, "user", user_message)
        classification = self._classifier.classify(user_message)
        field = session.dco.next_field(case_id)
        if field is None:
            return None
        # Choice/boolean fields have a fixed set of options (including "No").
        # A DECLINE intent must not block extraction — "No" is a valid answer, not a refusal.
        is_choice = field.field_type in ("choice", "multi_choice")
        allowed = (Intent.PROVIDE_INFO, Intent.CONFIRM)
        if not is_choice and classification.intent not in allowed:
            return None
        if is_choice and classification.intent not in (*allowed, Intent.DECLINE):
            return None
        value, error = session.dco.extract_and_update(case_id, user_message, field)
        if error:
            return error
        if value is not None:
            asyncio.create_task(
                self._persist_field(case_id, session.client_id, field.field_id, value, session)
            )
        return None

    # ── Message building ──────────────────────────────────────────────────────

    def _build_guided_message(
        self,
        user_message: str,
        next_field,
        is_complete: bool,
        validation_error: str | None = None,
    ) -> str:
        if is_complete:
            return (
                user_message
                + "\n\n[CONTEXT: All required information has been collected. "
                "Thank the client warmly in 2 sentences and explain identity verification is next.]"
            )
        if next_field:
            if validation_error:
                note = (
                    f"\n\n[CONTEXT: The client just provided an invalid value for "
                    f"'{next_field.label}'. Reason: {validation_error} "
                    f"Acknowledge their attempt kindly, explain the issue in plain language, "
                    f"and ask them to try again.]"
                )
            elif next_field.section == "regulatory_questions":
                note = (
                    f"\n\n[CONTEXT: The next question is a required regulatory disclosure. "
                    f"First acknowledge the client's previous response in one sentence, "
                    f"then ask this question EXACTLY as written, word for word: "
                    f'"{next_field.label}" Do NOT rephrase or add any question words.'
                )
            else:
                note = (
                    f"\n\n[CONTEXT: The next piece of information needed is '{next_field.label}'. "
                    f"First acknowledge the client's previous response warmly in one sentence, "
                    f"then ask them to provide their {next_field.label} in a friendly, "
                    f"conversational way. Do NOT repeat the field name robotically — phrase it as a "
                    f"natural question a human advisor would ask."
                )
            if not validation_error and next_field.options:
                opts = ", ".join(str(o) for o in next_field.options)
                note += f" They must choose one of: {opts}."
            note += "]"
            return user_message + note
        return user_message

    def _build_fallback_text(
        self, next_field, is_complete: bool, validation_error: str | None = None
    ) -> str:
        """Plain-text fallback streamed word-by-word when the LLM is unavailable."""
        if is_complete:
            return (
                "Thank you for providing all the required information. "
                "Your identity verification will begin shortly."
            )
        if next_field:
            if validation_error:
                return (
                    f"I'm sorry, that value isn't valid for {next_field.label}. "
                    f"{validation_error} Please try again."
                )
            if next_field.section == "regulatory_questions":
                return next_field.label
            label = next_field.label
            template = _FALLBACK_TEMPLATES[hash(label) % len(_FALLBACK_TEMPLATES)]
            return template.format(label=label)
        return "Thank you. We will process your information and be in touch shortly."

    # ── DB persistence ────────────────────────────────────────────────────────

    async def _load_history(self, case_id: UUID) -> list[dict[str, str]]:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ConversationMessage)
                    .where(ConversationMessage.case_id == case_id)
                    .where(ConversationMessage.role.in_(["user", "assistant"]))
                    .order_by(ConversationMessage.created_at.desc())
                    .limit(_MAX_HISTORY + 1)
                )
                rows = list(reversed(result.scalars().all()))
                # Exclude the current user turn already committed by the router
                if rows and rows[-1].role == "user":
                    rows = rows[:-1]
                return [{"role": r.role, "content": r.content} for r in rows]
        except Exception as exc:
            logger.warning(f"ConversationCoordinator: history load failed for {case_id}: {exc}")
            return []

    async def _persist_field(
        self,
        case_id: UUID,
        client_id: UUID,
        field_id: str,
        value: object,
        session: ConversationSession,
    ) -> None:
        # 1. Update ContextStore (shared_context JSONB on onboarding_cases)
        try:
            state = await context_store.get(case_id)
            updated = dict(state.client_data or {})
            updated[field_id] = value
            await context_store.update(case_id, {"client_data": updated})
        except Exception as exc:
            logger.warning(f"ConversationCoordinator: ContextStore update failed ({field_id}): {exc}")

        # 1b. Persist questionnaire portion of overall progress (0-60%) to the DB column
        try:
            q_status = session.dco.status(case_id)
            # questionnaire contributes 60% of the overall bar during INTAKE
            intake_pct = round(q_status.completion_pct * 60.0 / 100.0, 1)
            async with AsyncSessionLocal() as db:
                from sqlalchemy import update as sa_update
                from app.models.cases import OnboardingCase
                await db.execute(
                    sa_update(OnboardingCase)
                    .where(OnboardingCase.id == case_id)
                    .values(percentage=intake_pct)
                )
                await db.commit()
        except Exception as exc:
            logger.warning(f"ConversationCoordinator: percentage persist failed ({field_id}): {exc}")

        # 2. Upsert OnboardingAnswer + update OnboardingQuestionSession
        question_id = session.dco.get_question_id(case_id, field_id)
        questionnaire_id = session.dco.get_questionnaire_id(case_id)

        if question_id is None or questionnaire_id is None:
            # Questions loaded from hardcoded fallback — no DB question UUIDs available
            logger.debug(f"ConversationCoordinator: skipping OnboardingAnswer for {field_id} (no DB question id)")
            return

        try:
            async with AsyncSessionLocal() as db:
                # Use naive UTC — columns are TIMESTAMP WITHOUT TIME ZONE
                now = datetime.now(timezone.utc).replace(tzinfo=None)

                # Upsert OnboardingAnswer — one row per (case_id, question_id)
                stmt = (
                    pg_insert(OnboardingAnswer)
                    .values(
                        id=uuid4(),
                        case_id=case_id,
                        client_id=client_id,
                        questionnaire_id=questionnaire_id,
                        question_id=question_id,
                        question_key=field_id,
                        answer_value=value,
                        answered_at=now,
                        extra_metadata={},
                    )
                    .on_conflict_do_update(
                        constraint="oa_case_question_uq",
                        set_={
                            "answer_value": value,
                            "answered_at": now,
                            "updated_at": now,
                        },
                    )
                )
                await db.execute(stmt)

                # Update OnboardingQuestionSession progress
                await self._upsert_question_session(
                    db, case_id, client_id, questionnaire_id, session, now
                )

                await db.commit()
                logger.debug(f"ConversationCoordinator: persisted answer for {field_id} (case {case_id})")

        except Exception as exc:
            logger.warning(f"ConversationCoordinator: OnboardingAnswer persist failed ({field_id}): {exc}")

    async def _upsert_question_session(
        self,
        db,
        case_id: UUID,
        client_id: UUID,
        questionnaire_id: UUID,
        session: ConversationSession,
        now: datetime,
    ) -> None:
        """Create or update the OnboardingQuestionSession row for this case."""
        status = session.dco.status(case_id)
        next_field = session.dco.next_field(case_id)

        # Count answered questions (exclude the injected selected_products key)
        answered_count = max(0, len(status.collected_fields) - 1)
        current_section = next_field.section if next_field else "complete"
        is_complete = status.is_complete

        result = await db.execute(
            select(OnboardingQuestionSession)
            .where(OnboardingQuestionSession.case_id == case_id)
            .where(OnboardingQuestionSession.questionnaire_id == questionnaire_id)
        )
        q_session = result.scalar_one_or_none()

        if q_session:
            q_session.current_section = current_section
            q_session.current_question_index = answered_count
            if is_complete and q_session.status != "COMPLETED":
                q_session.status = "COMPLETED"
                q_session.completed_at = now
            elif not is_complete and q_session.status == "PAUSED":
                q_session.status = "IN_PROGRESS"
                q_session.resumed_at = now
            db.add(q_session)
        else:
            db.add(
                OnboardingQuestionSession(
                    case_id=case_id,
                    client_id=client_id,
                    questionnaire_id=questionnaire_id,
                    status="COMPLETED" if is_complete else "IN_PROGRESS",
                    current_section=current_section,
                    current_question_index=answered_count,
                    completed_sections=[],
                    session_data={},
                    completed_at=now if is_complete else None,
                    extra_metadata={},
                )
            )

    async def _persist_assistant(
        self,
        case_id: UUID,
        client_id: UUID,
        content: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        try:
            async with AsyncSessionLocal() as db:
                db.add(
                    ConversationMessage(
                        case_id=case_id,
                        client_id=client_id,
                        role="assistant",
                        content=content,
                        tokens_used=input_tokens + output_tokens,
                        extra_metadata={"input_tokens": input_tokens, "output_tokens": output_tokens},
                    )
                )
                await db.commit()
        except Exception as exc:
            logger.warning(f"ConversationCoordinator: assistant persist failed: {exc}")

    # ── Orchestrator signalling ───────────────────────────────────────────────

    async def _signal_advance(
        self, case_id: UUID, client_id: UUID, collected_fields: dict
    ) -> None:
        try:
            from app.services.orchestration.agent_orchestration_service import orchestration_service

            orchestrator = orchestration_service.registry.get(AgentID.ORCHESTRATOR)
            if orchestrator is None:
                logger.warning("ConversationCoordinator: orchestrator not registered")
                return

            await orchestrator.send_task(
                TaskPacket(
                    from_agent=AgentID.CUSTOMER_SERVICE,
                    to_agent=AgentID.ORCHESTRATOR,
                    task_type=TaskType.ADVANCE_STAGE,
                    case_id=case_id,
                    client_id=client_id,
                    priority="HIGH",
                    payload={
                        "to_stage": OnboardingStage.KYC,
                        "client_data": collected_fields,
                        "selected_products": collected_fields.get("selected_products", []),
                    },
                )
            )
            logger.info(f"ConversationCoordinator: ADVANCE_STAGE → KYC for case {case_id}")
        except Exception as exc:
            logger.warning(f"ConversationCoordinator: stage advance signal failed: {exc}")


conversation_coordinator = ConversationCoordinator()
