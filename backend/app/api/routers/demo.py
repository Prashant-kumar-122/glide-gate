from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.role_guard import require_role
from app.config import settings
from app.services.demo.demo_mode_service import demo_mode_service

router = APIRouter(prefix="/demo", tags=["demo"])


def _require_demo_mode() -> None:
    """Dependency that blocks all demo endpoints when DEMO_MODE is False."""
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=404,
            detail="Demo endpoints are only available when DEMO_MODE=True.",
        )


# ── Status ────────────────────────────────────────────────────────────────────


@router.get(
    "/status",
    summary="Demo mode status and loaded fixtures",
    dependencies=[Depends(_require_demo_mode)],
)
async def get_demo_status(
    _current_user=Depends(get_current_user),
) -> dict:
    return demo_mode_service.status()


# ── Conversation turn management ──────────────────────────────────────────────


@router.post(
    "/cases/{case_id}/reset",
    summary="Reset demo state for a case (turn counter + KYC scenario)",
    dependencies=[Depends(_require_demo_mode), Depends(require_role("admin", "advisor"))],
)
async def reset_case_demo(
    case_id: UUID,
    _current_user=Depends(get_current_user),
) -> dict:
    demo_mode_service.reset_case(case_id)
    return {"case_id": str(case_id), "reset": True}


# ── KYC scenario control ──────────────────────────────────────────────────────


class SetKYCScenarioRequest(BaseModel):
    scenario: str  # "passing" | "high_risk"


@router.post(
    "/cases/{case_id}/kyc-scenario",
    summary="Set the KYC scenario for a case (passing | high_risk)",
    dependencies=[Depends(_require_demo_mode), Depends(require_role("admin", "advisor"))],
)
async def set_kyc_scenario(
    case_id: UUID,
    body: SetKYCScenarioRequest,
    _current_user=Depends(get_current_user),
) -> dict:
    try:
        demo_mode_service.set_kyc_scenario(case_id, body.scenario)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "case_id": str(case_id),
        "kyc_scenario": body.scenario,
        "message": f"KYC scenario set to '{body.scenario}' for case {case_id}.",
    }


@router.get(
    "/cases/{case_id}/kyc-scenario",
    summary="Get the active KYC scenario for a case",
    dependencies=[Depends(_require_demo_mode)],
)
async def get_kyc_scenario(
    case_id: UUID,
    _current_user=Depends(get_current_user),
) -> dict:
    return {
        "case_id": str(case_id),
        "kyc_scenario": demo_mode_service.get_kyc_scenario(case_id),
    }
