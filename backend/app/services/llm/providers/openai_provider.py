from __future__ import annotations

import time
from typing import Any, AsyncIterator

from app.services.llm.llm_provider import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
)


class OpenAIProvider(LLMProvider):
    provider_name = "openai"
    default_model = "gpt-4o"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model or self.default_model
        self._base_url = base_url
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None and self._api_key:
            import openai  # type: ignore[import]

            kwargs: dict[str, Any] = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        return self._client

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _build_messages(self, request: LLMRequest) -> list[dict[str, str]]:
        msgs: list[dict[str, str]] = []
        if request.system_prompt:
            msgs.append({"role": "system", "content": request.system_prompt})
        msgs.extend({"role": m.role, "content": m.content} for m in request.messages)
        return msgs

    def _build_kwargs(self, request: LLMRequest, stream: bool = False) -> dict[str, Any]:
        kwargs: dict[str, Any] = dict(
            model=self._model,
            max_tokens=request.max_tokens,
            messages=self._build_messages(request),
            temperature=request.temperature,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            stream=stream,
        )
        if request.seed is not None:
            kwargs["seed"] = request.seed
        return kwargs

    async def complete(self, request: LLMRequest) -> LLMResponse:
        client = self._get_client()
        if client is None:
            raise RuntimeError("OpenAI API key not configured")

        t0 = time.monotonic()
        resp = await client.chat.completions.create(**self._build_kwargs(request))
        latency_ms = int((time.monotonic() - t0) * 1000)

        return LLMResponse(
            text=resp.choices[0].message.content or "",
            model=self._model,
            provider=self.provider_name,
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
            latency_ms=latency_ms,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        client = self._get_client()
        if client is None:
            raise RuntimeError("OpenAI API key not configured")

        t0 = time.monotonic()
        full_text = ""

        async for chunk in await client.chat.completions.create(
            **self._build_kwargs(request, stream=True)
        ):
            token = chunk.choices[0].delta.content or "" if chunk.choices else ""
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
