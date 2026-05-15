from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.agents.base.a2a_types import AgentID, OnboardingStage, TaskPacket, TaskType
from app.agents.customer_service.intent_classifier import Intent, IntentClassifier
from app.database import AsyncSessionLocal
from app.models.communications import ConversationMessage
from app.services.context_store.context_store_service import context_store
from app.services.conversation.session_manager import ConversationSession, session_manager
from app.services.conversation.streaming_response_service import streaming_response_service

_MAX_HISTORY = 20


class ConversationCoordinator:
    """
    Coordinates the streaming conversational onboarding interface.

    Per request:
      1. Resolves or creates a per-case session (DCO + memory).
      2. Extracts field values from the user message and persists them to ContextStore.
      3. Loads DB message history and augments the user turn with a guidance note.
      4. Delegates streaming to StreamingResponseService (real Anthropic streaming).
      5. Persists the assistant reply to DB after streaming completes.
      6. Signals OrchestratorAgent to advance to KYC when all fields are collected.
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
        session = await self._resolve_session(case_id)
        await self._extract_and_persist(case_id, user_message, session)

        status = session.dco.status(case_id)
        next_field = session.dco.next_field(case_id)

        history = await self._load_history(case_id)
        guided_msg = self._build_guided_message(user_message, next_field, status.is_complete)
        messages = history + [{"role": "user", "content": guided_msg}]

        full_text = ""
        input_tokens = 0
        output_tokens = 0

        async for sse_line in streaming_response_service.stream_reply(messages):
            yield sse_line
            # Reconstruct full_text from token events for DB persistence
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

        if status.is_complete and not session._advance_sent:
            session._advance_sent = True
            asyncio.create_task(
                self._signal_advance(case_id, client_id, status.collected_fields)
            )

    # ── Session resolution ────────────────────────────────────────────────────

    async def _resolve_session(self, case_id: UUID) -> ConversationSession:
        existing = session_manager.get(case_id)
        if existing:
            return existing

        selected_products: list[str] = []
        existing_data: dict = {}
        try:
            state = await context_store.get(case_id)
            selected_products = state.selected_products
            existing_data = state.client_data or {}
        except Exception as exc:
            logger.warning(f"ConversationCoordinator: context load failed for {case_id}: {exc}")

        session = session_manager.get_or_create(case_id, selected_products)
        for field_id, value in existing_data.items():
            if value is not None:
                session.dco.update(case_id, field_id, value)
        return session

    # ── Data extraction ───────────────────────────────────────────────────────

    async def _extract_and_persist(
        self, case_id: UUID, user_message: str, session: ConversationSession
    ) -> None:
        session.memory.add(case_id, "user", user_message)
        classification = self._classifier.classify(user_message)
        if classification.intent not in (Intent.PROVIDE_INFO, Intent.CONFIRM):
            return
        field = session.dco.next_field(case_id)
        if field is None:
            return
        value = session.dco.extract_and_update(case_id, user_message, field)
        if value is not None:
            asyncio.create_task(self._persist_field(case_id, field.field_id, value))

    # ── Message building ──────────────────────────────────────────────────────

    def _build_guided_message(self, user_message: str, next_field, is_complete: bool) -> str:
        if is_complete:
            return (
                user_message
                + "\n\n[CONTEXT: All required information has been collected. "
                "Thank the client warmly in 2 sentences and explain identity verification is next.]"
            )
        if next_field:
            note = f"\n\n[CONTEXT: Next required field is '{next_field.label}'. Ask: '{next_field.question}'"
            if next_field.options:
                note += f" Options: {', '.join(str(o) for o in next_field.options)}"
            note += "]"
            return user_message + note
        return user_message

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
                # The last row is the current user turn already committed by the router — exclude it
                if rows and rows[-1].role == "user":
                    rows = rows[:-1]
                return [{"role": r.role, "content": r.content} for r in rows]
        except Exception as exc:
            logger.warning(f"ConversationCoordinator: history load failed for {case_id}: {exc}")
            return []

    async def _persist_field(self, case_id: UUID, field_id: str, value: object) -> None:
        try:
            state = await context_store.get(case_id)
            updated = dict(state.client_data or {})
            updated[field_id] = value
            await context_store.update(case_id, {"client_data": updated})
        except Exception as exc:
            logger.warning(f"ConversationCoordinator: field persist failed ({field_id}): {exc}")

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
