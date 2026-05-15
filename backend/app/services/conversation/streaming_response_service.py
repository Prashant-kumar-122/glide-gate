from __future__ import annotations

import json
from typing import AsyncGenerator

from app.services.llm.llm_provider import LLMMessage, LLMRequest
from app.services.llm.llm_fallback_chain import llm_fallback_chain

CSA_SYSTEM_PROMPT = """\
You are a warm, professional wealth management onboarding specialist at GlideGate.
Your role is to collect required application information from the client conversationally.

Guidelines:
- Ask ONE question at a time.
- Acknowledge the client's response before moving on (one sentence).
- Keep each reply to 2–4 sentences total.
- Do not give investment advice or make product recommendations.
- If the client asks an off-topic question, answer briefly and redirect.
- When all required information is collected, thank the client warmly and explain that
  identity verification is the next step.
"""


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


class StreamingResponseService:
    """Wraps LLM streaming into Server-Sent Events format."""

    async def stream_reply(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str = CSA_SYSTEM_PROMPT,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        yield _sse({"type": "start"})

        llm_messages = [
            LLMMessage(role=m["role"], content=m["content"])  # type: ignore[arg-type]
            for m in messages
            if m.get("role") in ("user", "assistant")
        ]

        if not llm_messages:
            yield _sse({"type": "end", "input_tokens": 0, "output_tokens": 0})
            return

        request = LLMRequest(
            messages=llm_messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        final_resp = None
        try:
            async for chunk in llm_fallback_chain.stream(request):
                if chunk.is_final:
                    final_resp = chunk.final_response
                else:
                    yield _sse({"type": "token", "token": chunk.token})
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
            return

        yield _sse({
            "type": "end",
            "input_tokens": final_resp.input_tokens if final_resp else 0,
            "output_tokens": final_resp.output_tokens if final_resp else 0,
        })

    async def stream_text(self, text: str) -> AsyncGenerator[str, None]:
        """Typewriter-effect stream for pre-computed or fallback text."""
        yield _sse({"type": "start"})
        for word in text.split():
            yield _sse({"type": "token", "token": word + " "})
        yield _sse({"type": "end", "input_tokens": 0, "output_tokens": 0})


streaming_response_service = StreamingResponseService()
