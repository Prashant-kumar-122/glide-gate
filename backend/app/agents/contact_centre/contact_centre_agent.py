from __future__ import annotations

from typing import Any

from app.agents.base.a2a_types import AgentID, TaskPacket, TaskResponse, TaskType
from app.agents.base.base_agent import BaseAgent
from app.agents.contact_centre.status_summariser import StatusSummariser

_CC_SYSTEM_PROMPT = """\
You are a contact centre AI assistant for GlideGate wealth management.
Given a client's onboarding case details, produce a concise call summary and recommended actions.
Be factual, empathetic, and highlight any compliance escalations clearly.
Format: 3–5 sentences max, then a bullet list of recommended next steps.
"""


class ContactCentreAgent(BaseAgent):
    """
    Contact Centre Agent (BRD Section 6.1, Section 7.3, FR-05).

    Provides real-time status summaries for CC representatives and
    supports call-handling with AI-generated summaries.

    Handles:
    - SUMMARISE_CALL      — generate a call summary for a case (AI-enhanced if available)
    - GET_CLIENT_STATUS   — return structured onboarding status for a case
    """

    agent_id = AgentID.CONTACT_CENTRE

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._summariser = StatusSummariser()
        self._anthropic: Any = None  # lazy-initialised

    async def process(self, task: TaskPacket) -> TaskResponse:
        handlers = {
            TaskType.SUMMARISE_CALL: self._handle_summarise,
            TaskType.GET_CLIENT_STATUS: self._handle_get_status,
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

    async def _handle_summarise(self, task: TaskPacket) -> TaskResponse:
        client_data: dict[str, Any] = task.payload.get("client_data", {})
        onboarding_state: dict[str, Any] = task.payload.get("onboarding_state", {})

        base = self._summariser.summarise(
            case_id=str(task.case_id),
            client_data=client_data,
            onboarding_state=onboarding_state,
        )

        ai_summary = await self._ai_enhance(base.summary_text, base.recommended_next_steps)
        final_text = ai_summary if ai_summary else base.summary_text

        self.logger.info(
            f"Call summary generated for case={task.case_id} stage={base.current_stage} "
            f"escalation={base.escalation_flag}"
        )

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result={
                **base.model_dump(),
                "summary_text": final_text,
                "ai_enhanced": bool(ai_summary),
            },
        )

    async def _handle_get_status(self, task: TaskPacket) -> TaskResponse:
        client_data: dict[str, Any] = task.payload.get("client_data", {})
        onboarding_state: dict[str, Any] = task.payload.get("onboarding_state", {})

        summary = self._summariser.summarise(
            case_id=str(task.case_id),
            client_data=client_data,
            onboarding_state=onboarding_state,
        )

        return TaskResponse(
            task_id=task.id,
            from_agent=self.agent_id,
            status="SUCCESS",
            result=summary.model_dump(),
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

    async def _ai_enhance(
        self, base_summary: str, next_steps: list[str]
    ) -> str:
        client = self._get_client()
        if client is None:
            return ""
        try:
            from app.config import settings

            steps_str = "\n".join(f"- {s}" for s in next_steps)
            prompt = (
                f"Onboarding case summary:\n{base_summary}\n\n"
                f"Suggested next steps:\n{steps_str}\n\n"
                "Rewrite as a concise, professional call guide for a contact centre representative. "
                "3–5 sentences, then a bullet list of recommended actions."
            )
            resp = await client.messages.create(
                model=settings.PRIMARY_LLM_MODEL,
                max_tokens=300,
                system=_CC_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            return resp.content[0].text.strip()
        except Exception as exc:
            self.logger.warning(f"AI call summary enhancement failed: {exc}")
            return ""
