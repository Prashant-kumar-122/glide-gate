from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

import httpx

from app.services.llm.llm_provider import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
)


class LocalModelProvider(LLMProvider):
    """OpenAI-compatible local endpoint (Ollama, LM Studio, vLLM, etc.)."""

    provider_name = "local"
    default_model = "llama3"

    def __init__(self, base_url: str, model: str | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model or self.default_model

    def is_available(self) -> bool:
        return bool(self._base_url)

    def _build_messages(self, request: LLMRequest) -> list[dict[str, str]]:
        msgs: list[dict[str, str]] = []
        if request.system_prompt:
            msgs.append({"role": "system", "content": request.system_prompt})
        msgs.extend({"role": m.role, "content": m.content} for m in request.messages)
        return msgs

    def _build_payload(self, request: LLMRequest, stream: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": self._build_messages(request),
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": stream,
        }
        if request.frequency_penalty:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty:
            payload["presence_penalty"] = request.presence_penalty
        if request.seed is not None:
            payload["seed"] = request.seed
        return payload

    async def complete(self, request: LLMRequest) -> LLMResponse:
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=self._build_payload(request),
            )
            resp.raise_for_status()

        data = resp.json()
        latency_ms = int((time.monotonic() - t0) * 1000)
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            text=text,
            model=self._model,
            provider=self.provider_name,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        t0 = time.monotonic()
        full_text = ""

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=self._build_payload(request, stream=True),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or line == "data: [DONE]":
                        continue
                    raw = line.removeprefix("data: ")
                    try:
                        chunk = json.loads(raw)
                        token = chunk["choices"][0]["delta"].get("content", "")
                        full_text += token
                        yield LLMStreamChunk(token=token)
                    except Exception:
                        continue

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
