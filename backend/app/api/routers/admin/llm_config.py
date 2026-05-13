from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies.role_guard import require_role
from app.config import settings

router = APIRouter(prefix="/admin/llm-config", tags=["admin"])

# In-memory override store (DB-persisted config wired in STEP-24)
_overrides: dict[str, Any] = {}


# ── Request / Response models ─────────────────────────────────────────────────

class LLMConfigOut(BaseModel):
    primary_provider: str
    primary_model: str
    temperature: float
    top_p: float
    seed: int
    frequency_penalty: float
    presence_penalty: float
    max_tokens: int
    cache_ttl: int
    max_retries: int
    overrides_active: bool


class LLMConfigUpdate(BaseModel):
    primary_provider: Literal["anthropic", "openai", "google", "local"] | None = None
    primary_model: str | None = None
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    seed: int | None = None
    frequency_penalty: float | None = Field(None, ge=-2.0, le=2.0)
    presence_penalty: float | None = Field(None, ge=-2.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=32000)
    cache_ttl: int | None = Field(None, ge=0)
    max_retries: int | None = Field(None, ge=0, le=10)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=LLMConfigOut)
async def get_llm_config(
    _user: dict = Depends(require_role("Admin")),
) -> LLMConfigOut:
    return LLMConfigOut(
        primary_provider=_overrides.get("primary_provider", settings.PRIMARY_LLM_PROVIDER),
        primary_model=_overrides.get("primary_model", settings.PRIMARY_LLM_MODEL),
        temperature=_overrides.get("temperature", settings.LLM_TEMPERATURE),
        top_p=_overrides.get("top_p", settings.LLM_TOP_P),
        seed=_overrides.get("seed", settings.LLM_SEED),
        frequency_penalty=_overrides.get("frequency_penalty", settings.LLM_FREQUENCY_PENALTY),
        presence_penalty=_overrides.get("presence_penalty", settings.LLM_PRESENCE_PENALTY),
        max_tokens=_overrides.get("max_tokens", settings.LLM_MAX_TOKENS),
        cache_ttl=_overrides.get("cache_ttl", settings.LLM_CACHE_TTL),
        max_retries=_overrides.get("max_retries", settings.LLM_MAX_RETRIES),
        overrides_active=bool(_overrides),
    )


@router.put("", response_model=LLMConfigOut)
async def update_llm_config(
    body: LLMConfigUpdate,
    _user: dict = Depends(require_role("Admin")),
) -> LLMConfigOut:
    updates = body.model_dump(exclude_none=True)
    _overrides.update(updates)
    return await get_llm_config(_user=_user)


@router.delete("", response_model=LLMConfigOut)
async def reset_llm_config(
    _user: dict = Depends(require_role("Admin")),
) -> LLMConfigOut:
    _overrides.clear()
    return await get_llm_config(_user=_user)
