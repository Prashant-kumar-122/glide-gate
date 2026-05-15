from __future__ import annotations

import time
from typing import Any, AsyncIterator

from app.services.llm.llm_provider import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
)


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude provider with prompt caching support.
    System prompt is wrapped in an ephemeral cache_control block when
    use_cache=True, reducing token costs on repeated agent calls.
    """

    provider_name = "anthropic"
    default_model = "claude-sonnet-4-6"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self._api_key = api_key
        self._model = model or self.default_model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None and self._api_key:
            import anthropic  # type: ignore[import]

            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _build_system(self, request: LLMRequest) -> Any:
        if not request.system_prompt:
            return None
        if request.use_cache:
            return [
                {
                    "type": "text",
                    "text": request.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        return request.system_prompt

    def _build_kwargs(self, request: LLMRequest) -> dict[str, Any]:
        kwargs: dict[str, Any] = dict(
            model=self._model,
            max_tokens=request.max_tokens,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature,
            top_p=request.top_p,
        )
        system = self._build_system(request)
        if system:
            kwargs["system"] = system
        return kwargs

    async def complete(self, request: LLMRequest) -> LLMResponse:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Anthropic API key not configured")

        t0 = time.monotonic()
        resp = await client.messages.create(**self._build_kwargs(request))
        latency_ms = int((time.monotonic() - t0) * 1000)

        cached = bool(
            getattr(resp, "usage", None)
            and getattr(resp.usage, "cache_read_input_tokens", 0)
        )
        return LLMResponse(
            text=resp.content[0].text if resp.content else "",
            model=self._model,
            provider=self.provider_name,
            input_tokens=getattr(resp.usage, "input_tokens", 0),
            output_tokens=getattr(resp.usage, "output_tokens", 0),
            latency_ms=latency_ms,
            cached=cached,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Anthropic API key not configured")

        t0 = time.monotonic()
        full_text = ""

        async with client.messages.stream(**self._build_kwargs(request)) as stream_ctx:
            async for text_chunk in stream_ctx.text_stream:
                full_text += text_chunk
                yield LLMStreamChunk(token=text_chunk)

            final = await stream_ctx.get_final_message()
            latency_ms = int((time.monotonic() - t0) * 1000)
            cached = bool(
                getattr(final, "usage", None)
                and getattr(final.usage, "cache_read_input_tokens", 0)
            )
            yield LLMStreamChunk(
                token="",
                is_final=True,
                final_response=LLMResponse(
                    text=full_text,
                    model=self._model,
                    provider=self.provider_name,
                    input_tokens=getattr(final.usage, "input_tokens", 0),
                    output_tokens=getattr(final.usage, "output_tokens", 0),
                    latency_ms=latency_ms,
                    cached=cached,
                ),
            )
