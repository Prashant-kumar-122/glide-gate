from __future__ import annotations

from typing import Any

from app.agents.base.a2a_types import (
    AgentID,
    OnboardingStage,
    TaskPacket,
    TaskResponse,
    TaskType,
)
from app.agents.base.base_agent import BaseAgent
from app.agents.customer_service.conversation_memory import ConversationMemory
from app.database import AsyncSessionLocal
from app.agents.customer_service.data_collection_orchestrator import (
    CollectionStatus,
    DataCollectionOrchestrator,
    QuestionnaireField,
)
from app.agents.customer_service.intent_classifier import Intent, IntentClassifier

_SYSTEM_PROMPT = """\
You are a warm, professional wealth management onboarding specialist at GlideGate.
Your role is to collect required application information from the client conversationally.

Guidelines:
- Ask ONE question at a time.
- Acknowledge the client's response before moving on (one sentence).
- Keep each reply to 2–4 sentences total.
- Do not give investment advice or make product recommendations.
- If the client asks an off-topic question, answer briefly and redirect.
- When all information is collected, thank them warmly and explain that identity verification is next.
"""

_FALLBACK_GREETING = (
    "Welcome to GlideGate! I'm your personal onboarding specialist and I'll guide you "
    "through the account setup — it should take about 5–10 minutes. "
    "Let's start: could you please provide your full legal name as it appears on your ID document?"
)

_FALLBACK_COMPLETE = (
    "Thank you — we've collected all the information needed for your application. "
    "The next step is a quick identity verification check. "
    "We'll notify you as soon as it's complete."
)


class CustomerServiceAgent(BaseAgent):
    """
    Conversational front door for client data collection (BRD Section 6.1, FR-02, FR-12).

    Handles:
    - COLLECT_CLIENT_DATA  — initialise session and send greeting
    - CONTINUE_CONVERSATION — process a user turn, extract data, return next question

    When all required questionnaire fields are collected, signals the
    OrchestratorAgent to advance the workflow to KYC stage.
    """

    agent_id = AgentID.CUSTOMER_SERVICE

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        cfg = config or {}
        self._memory = ConversationMemory(max_messages=int(cfg.get("max_messages", 40)))
        self._dco = DataCollectionOrchestrator()
        self._classifier = IntentClassifier()
        self._anthropic: Any = None  # lazy-initialised in _get_client()

    # ── BaseAgent.process ─────────────────────────────────────────────────────

    async def process(self, task: TaskPacket) -> TaskResponse:
        handlers = {
            TaskType.COLLECT_CLIENT_DATA: self._handle_collect,
            TaskType.CONTINUE_CONVERSATION: self._handle_continue,
        }
        handler = handlers.get(task.task_type)
        if handler is None:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=[f"Unsupported task_type: {task.task_type}"],
            )
        return await handler(task)

    # ── Task handlers ─────────────────────────────────────────────────────────

    async def _handle_collect(self, task: TaskPacket) -> TaskResponse:
        selected_products: list[str] = task.payload.get("selected_products", [])
        self._dco.init_session(task.case_id, selected_products)
        self._memory.clear(task.case_id)
 
        async with AsyncSessionLocal() as db:
            await self._dco.load_questions_from_db(task.case_id, db)
 
        greeting = await self._greeting(selected_products)
        self._memory.add(task.case_id, "assistant", greeting)

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={
                "message": greeting,
                "case_id": str(task.case_id),
                "stage": "collection_started",
                "completion_pct": 0.0,
            },
        )

    async def _handle_continue(self, task: TaskPacket) -> TaskResponse:
        user_message: str = task.payload.get("message", "").strip()
        if not user_message:
            return TaskResponse(
                task_id=task.id,
                from_agent=self.agent_id,
                status="FAILED",
                errors=["Empty user message"],
            )

        # Ensure session exists (resume after restart)
        if not self._dco.has_session(task.case_id):
            self._dco.init_session(
                task.case_id, task.payload.get("selected_products", [])
            )
 
        # Load DB questions if not yet loaded for this case
        if not self._dco.is_db_loaded(task.case_id):
            async with AsyncSessionLocal() as db:
                await self._dco.load_questions_from_db(task.case_id, db)
 
        self._memory.add(task.case_id, "user", user_message)

        classification = self._classifier.classify(user_message)
        current_field = self._dco.next_field(task.case_id)

        # Attempt value extraction for the current pending field
        extracted_value: Any = None
        extraction_error: str | None = None
        if current_field and classification.intent in (Intent.PROVIDE_INFO, Intent.CONFIRM):
            extracted_value, extraction_error = self._dco.extract_and_update(
                task.case_id, user_message, current_field
            )

        status = self._dco.status(task.case_id)
        next_field = self._dco.next_field(task.case_id)

        # Generate reply
        if status.is_complete:
            reply = await self._completion_message()
            await self._signal_advance(task, status)
        elif classification.intent == Intent.REQUEST_HELP:
            reply = await self._help_response(user_message, current_field)
        elif classification.intent == Intent.ASK_QUESTION:
            reply = await self._answer_and_redirect(user_message, next_field)
        else:
            reply = await self._next_question(
                extracted_value, current_field, next_field, extraction_error
            )

        self._memory.add(task.case_id, "assistant", reply)

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={
                "message": reply,
                "case_id": str(task.case_id),
                "intent": str(classification.intent),
                "extracted_field": current_field.field_id if (current_field and extracted_value is not None) else None,
                "extracted_value": extracted_value,
                "completion_pct": status.completion_pct,
                "current_section": status.current_section,
                "is_complete": status.is_complete,
                "collected_fields": status.collected_fields,
            },
        )

    # ── Orchestrator signalling ───────────────────────────────────────────────

    async def _signal_advance(self, task: TaskPacket, status: CollectionStatus) -> None:
        if self._bus is None:
            self.logger.warning(
                f"No event bus; cannot advance stage for case={task.case_id}"
            )
            return
        await self.send_task(
            TaskPacket(
                from_agent=self.agent_id,
                to_agent=AgentID.ORCHESTRATOR,
                task_type=TaskType.ADVANCE_STAGE,
                case_id=task.case_id,
                client_id=task.client_id,
                priority="HIGH",
                payload={
                    "to_stage": OnboardingStage.KYC,
                    "client_data": status.collected_fields,
                    "selected_products": status.collected_fields.get("selected_products", []),
                },
            )
        )

    # ── LLM helpers ───────────────────────────────────────────────────────────

    def _get_client(self) -> Any:
        if self._anthropic is None:
            try:
                import anthropic  # type: ignore[import]
                from app.config import settings

                if settings.ANTHROPIC_API_KEY:
                    self._anthropic = anthropic.AsyncAnthropic(
                        api_key=settings.ANTHROPIC_API_KEY
                    )
            except Exception:
                pass
        return self._anthropic

    async def _llm(self, prompt: str) -> str:
        client = self._get_client()
        if client is None:
            return ""
        try:
            from app.config import settings

            resp = await client.messages.create(
                model=settings.PRIMARY_LLM_MODEL,
                max_tokens=256,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return resp.content[0].text.strip()
        except Exception as exc:
            self.logger.warning(f"LLM call failed, using template fallback: {exc}")
            return ""

    # ── Response generators ───────────────────────────────────────────────────

    async def _greeting(self, products: list[str]) -> str:
        names = {"cash_account": "Cash Account", "retirement_account": "Retirement Account"}
        product_str = " and ".join(names.get(p, p) for p in products) if products else "your account"
        result = await self._llm(
            f"Generate a warm 2-sentence greeting for a new client applying for: {product_str}. "
            f"End by asking for their full legal name."
        )
        return result or _FALLBACK_GREETING

    async def _next_question(
        self,
        extracted_value: Any,
        prev_field: QuestionnaireField | None,
        next_field: QuestionnaireField | None,
        validation_error: str | None = None,
    ) -> str:
        if next_field is None:
            return _FALLBACK_COMPLETE

        if validation_error and prev_field:
            result = await self._llm(
                f"The client provided an invalid value for '{prev_field.label}'. "
                f"Reason: {validation_error} "
                f"Apologise briefly and ask them to try again: '{prev_field.question}'."
            )
            return result or f"I'm sorry, that value isn't valid — {validation_error} Please try again."

        ack = ""
        if extracted_value is not None and prev_field:
            ack = f"The client just provided their {prev_field.label}. "

        q = next_field.question
        if next_field.options:
            opts = "; ".join(f"({i + 1}) {o}" for i, o in enumerate(next_field.options))
            q += f" [{opts}]"

        result = await self._llm(
            f"{ack}Acknowledge their answer in one sentence then ask: '{q}'. "
            f"Total reply: 2–3 sentences."
        )
        ack_text = "Thank you for that. " if extracted_value is not None else ""
        return result or f"{ack_text}{next_field.question}"

    async def _help_response(
        self, user_message: str, field: QuestionnaireField | None
    ) -> str:
        if field is None:
            return "We've collected everything needed. Let me know if you have any final questions."
        result = await self._llm(
            f"The client asked: '{user_message}'. We're asking for: '{field.label}' — '{field.question}'. "
            f"Explain what's needed in 1 sentence, then ask the question again."
        )
        return result or f"Happy to clarify! {field.question}"

    async def _answer_and_redirect(
        self, user_message: str, next_field: QuestionnaireField | None
    ) -> str:
        if next_field is None:
            return "Great question! We're almost done — let me know if you have anything else."
        result = await self._llm(
            f"Client asked: '{user_message}'. Answer briefly (1 sentence), "
            f"then ask: '{next_field.question}'."
        )
        return result or f"Great question! To continue: {next_field.question}"

    async def _completion_message(self) -> str:
        result = await self._llm(
            "All required onboarding information has been collected. "
            "Write a warm 2-sentence thank-you message and explain that identity verification is the next step."
        )
        return result or _FALLBACK_COMPLETE
