from __future__ import annotations

from typing import Literal

from app.config import settings
from app.services.llm.deterministic_controls_applier import get_all_overrides
from app.services.llm.llm_provider import LLMProvider
from app.services.llm.providers.anthropic_provider import AnthropicProvider
from app.services.llm.providers.google_provider import GoogleProvider
from app.services.llm.providers.local_model_provider import LocalModelProvider
from app.services.llm.providers.openai_provider import OpenAIProvider

ProviderName = Literal["anthropic", "openai", "google", "local"]

_ALL_PROVIDERS: list[ProviderName] = ["anthropic", "openai", "google", "local"]


class LLMProviderFactory:
    def create(
        self,
        provider_name: ProviderName | None = None,
        model: str | None = None,
    ) -> LLMProvider:
        overrides = get_all_overrides()
        name: ProviderName = (  # type: ignore[assignment]
            provider_name
            or overrides.get("primary_provider", settings.PRIMARY_LLM_PROVIDER)
        )
        mdl = model or overrides.get("primary_model", settings.PRIMARY_LLM_MODEL)

        if name == "anthropic":
            return AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY, model=mdl)
        if name == "openai":
            return OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=mdl)
        if name == "google":
            return GoogleProvider(api_key=settings.GOOGLE_API_KEY, model=mdl)
        if name == "local":
            local_model = model or overrides.get("primary_model") or settings.LOCAL_MODEL_NAME
            return LocalModelProvider(base_url=settings.LOCAL_MODEL_ENDPOINT, model=local_model)
        raise ValueError(f"Unknown LLM provider: {name!r}")

    def create_fallback_ordered(self) -> list[LLMProvider]:
        """Primary provider first, then available fallbacks in declaration order."""
        overrides = get_all_overrides()
        primary: ProviderName = overrides.get(  # type: ignore[assignment]
            "primary_provider", settings.PRIMARY_LLM_PROVIDER
        )
        ordered: list[ProviderName] = [primary] + [  # type: ignore[list-item]
            n for n in _ALL_PROVIDERS if n != primary
        ]
        providers: list[LLMProvider] = []
        for name in ordered:
            try:
                p = self.create(provider_name=name)
                if p.is_available():
                    providers.append(p)
            except Exception:
                continue
        return providers


llm_provider_factory = LLMProviderFactory()
