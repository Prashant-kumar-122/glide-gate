from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies.permission_guard import require_permission
from app.api.error_handlers import NotFoundError
from app.services.validation.prompt_override_store import (
    get_prompt_override,
    is_overridden,
    reset_prompt_override,
    set_prompt_override,
)

router = APIRouter(prefix="/admin/validation-prompts", tags=["admin"])

VALID_CATEGORIES = {"identity", "financial", "legal", "insurance", "compliance", "entity"}

_DEFAULTS_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "prompts" / "validation_defaults"


def _load_default(category: str) -> dict[str, Any]:
    path = _DEFAULTS_DIR / f"{category}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "category": category,
        "goal": f"Validate completeness and authenticity of {category} documents",
        "factors": [],
    }


# ── Request / Response models ─────────────────────────────────────────────────

class ValidationPromptOut(BaseModel):
    category: str
    goal: str
    factors: list[str]
    is_overridden: bool


class ValidationPromptUpdate(BaseModel):
    goal: str
    factors: list[str]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ValidationPromptOut])
async def list_validation_prompts(
    _user: dict = Depends(require_permission("admin:config")),
) -> list[ValidationPromptOut]:
    results = []
    for cat in sorted(VALID_CATEGORIES):
        base = _load_default(cat)
        override = get_prompt_override(cat)
        effective = override if override else base
        results.append(ValidationPromptOut(
            category=cat,
            goal=effective.get("goal", ""),
            factors=effective.get("factors", []),
            is_overridden=is_overridden(cat),
        ))
    return results


@router.get("/{category}", response_model=ValidationPromptOut)
async def get_validation_prompt(
    category: str,
    _user: dict = Depends(require_permission("admin:config")),
) -> ValidationPromptOut:
    if category not in VALID_CATEGORIES:
        raise NotFoundError("ValidationPrompt", category)
    base = _load_default(category)
    override = get_prompt_override(category)
    effective = override if override else base
    return ValidationPromptOut(
        category=category,
        goal=effective.get("goal", ""),
        factors=effective.get("factors", []),
        is_overridden=is_overridden(category),
    )


@router.put("/{category}", response_model=ValidationPromptOut)
async def update_validation_prompt(
    category: str,
    body: ValidationPromptUpdate,
    _user: dict = Depends(require_permission("admin:config")),
) -> ValidationPromptOut:
    if category not in VALID_CATEGORIES:
        raise NotFoundError("ValidationPrompt", category)
    set_prompt_override(category, body.goal, body.factors)
    return ValidationPromptOut(
        category=category,
        goal=body.goal,
        factors=body.factors,
        is_overridden=True,
    )


@router.delete("/{category}", response_model=ValidationPromptOut)
async def reset_validation_prompt(
    category: str,
    _user: dict = Depends(require_permission("admin:config")),
) -> ValidationPromptOut:
    if category not in VALID_CATEGORIES:
        raise NotFoundError("ValidationPrompt", category)
    reset_prompt_override(category)
    base = _load_default(category)
    return ValidationPromptOut(
        category=category,
        goal=base.get("goal", ""),
        factors=base.get("factors", []),
        is_overridden=False,
    )
