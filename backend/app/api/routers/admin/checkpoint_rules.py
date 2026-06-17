from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies.permission_guard import require_permission
from app.api.error_handlers import ConflictError, NotFoundError, UnprocessableError
from app.agents.kyc_compliance.checkpoint_rule_engine import CheckpointRule
import app.services.compliance.checkpoint_rule_repository as rule_repo

router = APIRouter(prefix="/admin/checkpoint-rules", tags=["admin"])


# ── Request / Response models ─────────────────────────────────────────────────

class CheckpointRuleOut(BaseModel):
    rule_id: str
    description: str
    product_type: str | None
    risk_level: str | None
    account_value_band: str | None
    jurisdiction: str | None
    action: str
    required_documents: list[str]
    reason_template: str
    is_builtin: bool


class CreateCheckpointRuleRequest(BaseModel):
    rule_id: str | None = Field(None, description="Auto-generated if omitted")
    description: str
    product_type: str | None = None
    risk_level: str | None = None
    account_value_band: str | None = None
    jurisdiction: str | None = None
    action: Literal["ESCALATE", "ENHANCED_DD", "REQUIRE_DOCUMENTS"]
    required_documents: list[str] = []
    reason_template: str = ""


def _to_out(rule: CheckpointRule) -> CheckpointRuleOut:
    return CheckpointRuleOut(
        rule_id=rule.rule_id,
        description=rule.description,
        product_type=rule.product_type,
        risk_level=rule.risk_level,
        account_value_band=rule.account_value_band,
        jurisdiction=rule.jurisdiction,
        action=rule.action,
        required_documents=rule.required_documents,
        reason_template=rule.reason_template,
        is_builtin=rule_repo.is_builtin(rule.rule_id),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[CheckpointRuleOut])
async def list_checkpoint_rules(
    _user: dict = Depends(require_permission("admin:config")),
) -> list[CheckpointRuleOut]:
    return [_to_out(r) for r in rule_repo.get_all()]


@router.post("/reset", response_model=list[CheckpointRuleOut])
async def reset_checkpoint_rules(
    _user: dict = Depends(require_permission("admin:config")),
) -> list[CheckpointRuleOut]:
    rules = rule_repo.reset()
    return [_to_out(r) for r in rules]


@router.post("", response_model=CheckpointRuleOut, status_code=201)
async def create_checkpoint_rule(
    body: CreateCheckpointRuleRequest,
    _user: dict = Depends(require_permission("admin:config")),
) -> CheckpointRuleOut:
    rule_id = body.rule_id or rule_repo.make_rule_id()
    rule = CheckpointRule(
        rule_id=rule_id,
        description=body.description,
        product_type=body.product_type,
        risk_level=body.risk_level,
        account_value_band=body.account_value_band,
        jurisdiction=body.jurisdiction,
        action=body.action,
        required_documents=body.required_documents,
        reason_template=body.reason_template,
    )
    try:
        added = rule_repo.add(rule)
    except ValueError as e:
        raise ConflictError(str(e)) from e
    return _to_out(added)


@router.put("/{rule_id}", response_model=CheckpointRuleOut)
async def update_checkpoint_rule(
    rule_id: str,
    body: CreateCheckpointRuleRequest,
    _user: dict = Depends(require_permission("admin:config")),
) -> CheckpointRuleOut:
    if rule_repo.get(rule_id) is None:
        raise NotFoundError("CheckpointRule", rule_id)
    updated = CheckpointRule(
        rule_id=rule_id,
        description=body.description,
        product_type=body.product_type,
        risk_level=body.risk_level,
        account_value_band=body.account_value_band,
        jurisdiction=body.jurisdiction,
        action=body.action,
        required_documents=body.required_documents,
        reason_template=body.reason_template,
    )
    rule_repo.update(rule_id, updated)
    return _to_out(updated)


@router.delete("/{rule_id}")
async def delete_checkpoint_rule(
    rule_id: str,
    _user: dict = Depends(require_permission("admin:config")),
) -> dict:
    if rule_repo.get(rule_id) is None:
        raise NotFoundError("CheckpointRule", rule_id)
    try:
        rule_repo.remove(rule_id)
    except ValueError as e:
        raise UnprocessableError(str(e)) from e
    return {"deleted": rule_id}
