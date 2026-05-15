from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator

from app.services.llm.llm_provider import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
)


class GoogleProvider(LLMProvider):
    """Google Gemini provider via google-generativeai SDK (sync wrapped in executor)."""

    provider_name = "google"
    default_model = "gemini-1.5-flash"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._api_key = api_key
        self._model = model or self.default_model
        self._genai: Any = None

    def _get_genai(self) -> Any:
        if self._genai is None and self._api_key:
            import google.generativeai as genai  # type: ignore[import]

            genai.configure(api_key=self._api_key)
            self._genai = genai
        return self._genai

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _build_model(self, request: LLMRequest) -> Any:
        genai = self._get_genai()
        config = genai.types.GenerationConfig(
            temperature=request.temperature,
            top_p=request.top_p,
            max_output_tokens=request.max_tokens,
        )
        return genai.GenerativeModel(
            model_name=self._model,
            generation_config=config,
            system_instruction=request.system_prompt or None,
        )

    def _build_contents(self, request: LLMRequest) -> list[dict[str, Any]]:
        return [{"role": m.role, "parts": [m.content]} for m in request.messages]

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("Google API key not configured")

        model = self._build_model(request)
        contents = self._build_contents(request)
        t0 = time.monotonic()

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: model.generate_content(contents))
        latency_ms = int((time.monotonic() - t0) * 1000)

        text = resp.text if hasattr(resp, "text") else ""
        return LLMResponse(
            text=text,
            model=self._model,
            provider=self.provider_name,
            latency_ms=latency_ms,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        if not self.is_available():
            raise RuntimeError("Google API key not configured")

        model = self._build_model(request)
        contents = self._build_contents(request)
        t0 = time.monotonic()
        full_text = ""

        loop = asyncio.get_event_loop()
        stream_resp = await loop.run_in_executor(
            None, lambda: model.generate_content(contents, stream=True)
        )

        for chunk in stream_resp:
            token = chunk.text if hasattr(chunk, "text") else ""
            full_text += token
            yield LLMStreamChunk(token=token)

        latency_ms = int((time.monotonic() - t0) * 1000)
        yield LLMStreamChunk(
            token="",
            is_final=True,
            final_response=LLMResponse(
                text=full_text,
                model=self._model,
                provider=self.provider_name,
                latency_ms=latency_ms,
            ),
        )
