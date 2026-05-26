from __future__ import annotations

from typing import AsyncIterator

from loguru import logger

from app.services.llm.llm_provider import LLMProvider, LLMRequest, LLMResponse, LLMStreamChunk
from app.services.llm.llm_provider_factory import llm_provider_factory


class LLMFallbackChain:
    """
    Tries providers in priority order (primary first).
    On any exception moves to the next available provider.
    Provider list is rebuilt from the factory on each call so that admin
    overrides (provider/model changes) take effect immediately.
    """

    async def complete(self, request: LLMRequest) -> LLMResponse:
        providers: list[LLMProvider] = llm_provider_factory.create_fallback_ordered()
        errors: list[str] = []
        for provider in providers:
            try:
                return await provider.complete(request)
            except Exception as exc:
                logger.warning(
                    f"LLMFallbackChain.complete: provider={provider.provider_name} failed: {exc!r}"
                )
                errors.append(f"{provider.provider_name}: {exc}")
        raise RuntimeError(f"All LLM providers failed. Errors: {'; '.join(errors)}")

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        providers: list[LLMProvider] = llm_provider_factory.create_fallback_ordered()
        errors: list[str] = []
        for provider in providers:
            try:
                async for chunk in provider.stream(request):
                    yield chunk
                return
            except Exception as exc:
                logger.warning(
                    f"LLMFallbackChain.complete: provider={provider.provider_name} failed: {exc!r}"
                )
                errors.append(f"{provider.provider_name}: {exc}")
        raise RuntimeError(
            f"All LLM providers failed during streaming. Errors: {'; '.join(errors)}"
        )


llm_fallback_chain = LLMFallbackChain()
