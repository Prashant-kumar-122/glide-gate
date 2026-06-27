from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies.permission_guard import require_permission
from app.config import settings
from app.services.llm.deterministic_controls_applier import (
    clear_overrides,
    get_all_overrides,
    set_overrides,
)

router = APIRouter(prefix="/admin/llm-config", tags=["admin"])


# ── Request / Response models ─────────────────────────────────────────────────

class LLMConfigOut(BaseModel):
    provider: str
    model: str
    temperature: float
    top_p: float
    seed: int
    frequency_penalty: float
    presence_penalty: float
    max_tokens: int
    cache_ttl: int
    max_retries: int
    overrides_active: bool
    api_key_configured: bool


class LLMConfigUpdate(BaseModel):
    provider: Literal["anthropic", "openai", "google", "local"] | None = None
    model: str | None = None
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    seed: int | None = None
    frequency_penalty: float | None = Field(None, ge=-2.0, le=2.0)
    presence_penalty: float | None = Field(None, ge=-2.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=32000)
    cache_ttl: int | None = Field(None, ge=0)
    max_retries: int | None = Field(None, ge=0, le=10)
    api_key: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

_PROVIDER_SETTINGS_KEY = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
}


def _api_key_configured(provider: str, overrides: dict) -> bool:
    override_key = overrides.get(f"{provider}_api_key", "")
    settings_key = getattr(settings, _PROVIDER_SETTINGS_KEY.get(provider, ""), "")
    return bool(override_key or settings_key)


@router.get("", response_model=LLMConfigOut)
async def get_llm_config(
    _user: dict = Depends(require_permission("admin:config")),
) -> LLMConfigOut:
    ov = get_all_overrides()
    provider = ov.get("provider", settings.PRIMARY_LLM_PROVIDER)
    return LLMConfigOut(
        provider=provider,
        model=ov.get("model", settings.PRIMARY_LLM_MODEL),
        temperature=ov.get("temperature", settings.LLM_TEMPERATURE),
        top_p=ov.get("top_p", settings.LLM_TOP_P),
        seed=ov.get("seed", settings.LLM_SEED),
        frequency_penalty=ov.get("frequency_penalty", settings.LLM_FREQUENCY_PENALTY),
        presence_penalty=ov.get("presence_penalty", settings.LLM_PRESENCE_PENALTY),
        max_tokens=ov.get("max_tokens", settings.LLM_MAX_TOKENS),
        cache_ttl=ov.get("cache_ttl", settings.LLM_CACHE_TTL),
        max_retries=ov.get("max_retries", settings.LLM_MAX_RETRIES),
        overrides_active=bool(ov),
        api_key_configured=_api_key_configured(provider, ov),
    )


@router.put("", response_model=LLMConfigOut)
async def update_llm_config(
    body: LLMConfigUpdate,
    _user: dict = Depends(require_permission("admin:config")),
) -> LLMConfigOut:
    updates = body.model_dump(exclude_none=True)
    if "api_key" in updates:
        # Store per-provider so keys survive provider switches
        ov = get_all_overrides()
        provider = updates.get("provider") or ov.get("provider") or settings.PRIMARY_LLM_PROVIDER
        updates[f"{provider}_api_key"] = updates.pop("api_key")
    set_overrides(updates)
    return await get_llm_config(_user=_user)


@router.delete("", response_model=LLMConfigOut)
async def reset_llm_config(
    _user: dict = Depends(require_permission("admin:config")),
) -> LLMConfigOut:
    clear_overrides()
    return await get_llm_config(_user=_user)
