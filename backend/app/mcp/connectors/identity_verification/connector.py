from __future__ import annotations

import asyncio
import random
import time
from typing import Any
from uuid import UUID

from loguru import logger

from app.mcp.mcp_connector import MCPConnector, MCPToolDefinition
from app.mcp.mcp_logger import mcp_logger
from app.mcp.connectors.identity_verification.simulator import (
    simulate_verify_identity,
    simulate_check_sanctions,
    simulate_score_aml_risk,
)

_TOOLS: list[MCPToolDefinition] = [
    MCPToolDefinition(
        name="verify_identity",
        description="Verify a client's identity documents against authoritative sources.",
        input_schema={
            "type": "object",
            "required": ["full_name", "document_type", "document_number"],
            "properties": {
                "full_name": {"type": "string"},
                "date_of_birth": {"type": "string", "format": "date"},
                "nationality": {"type": "string"},
                "document_type": {"type": "string", "enum": ["PASSPORT", "NATIONAL_ID", "DRIVING_LICENSE"]},
                "document_number": {"type": "string"},
                "document_expiry": {"type": "string", "format": "date"},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "verified": {"type": "boolean"},
                "confidence_score": {"type": "number"},
                "identity_match": {"type": "object"},
                "flags": {"type": "array", "items": {"type": "string"}},
                "provider_reference": {"type": "string"},
            },
        },
    ),
    MCPToolDefinition(
        name="check_sanctions",
        description="Screen a client against global sanctions and watchlists.",
        input_schema={
            "type": "object",
            "required": ["full_name"],
            "properties": {
                "full_name": {"type": "string"},
                "date_of_birth": {"type": "string", "format": "date"},
                "nationality": {"type": "string"},
                "aliases": {"type": "array", "items": {"type": "string"}},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "is_sanctioned": {"type": "boolean"},
                "screening_score": {"type": "number"},
                "matches": {"type": "array"},
                "lists_screened": {"type": "array"},
                "provider_reference": {"type": "string"},
            },
        },
    ),
    MCPToolDefinition(
        name="score_aml_risk",
        description="Calculate an AML risk score from client profile attributes.",
        input_schema={
            "type": "object",
            "required": ["full_name"],
            "properties": {
                "full_name": {"type": "string"},
                "nationality": {"type": "string"},
                "country_of_residence": {"type": "string"},
                "occupation": {"type": "string"},
                "annual_income": {"type": "number"},
                "source_of_wealth": {"type": "string"},
                "pep_status": {"type": "boolean"},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "risk_score": {"type": "number"},
                "risk_band": {"type": "string"},
                "risk_factors": {"type": "array"},
                "recommended_action": {"type": "string"},
                "provider_reference": {"type": "string"},
            },
        },
    ),
]

_DISPATCHERS = {
    "verify_identity": simulate_verify_identity,
    "check_sanctions": simulate_check_sanctions,
    "score_aml_risk": simulate_score_aml_risk,
}


class IdentityVerificationConnector(MCPConnector):
    connector_name = "identity_verification"

    def list_tools(self) -> list[MCPToolDefinition]:
        return _TOOLS

    async def invoke(
        self,
        tool_name: str,
        inputs: dict[str, Any],
        *,
        case_id: UUID | None = None,
        agent_id: str = "unknown",
    ) -> dict[str, Any]:
        if tool_name not in _DISPATCHERS:
            raise ValueError(f"Unknown tool {tool_name!r} on connector {self.connector_name!r}")

        latency_ms = random.randint(100, 800)
        await asyncio.sleep(latency_ms / 1000)

        t0 = time.monotonic()
        try:
            result = _DISPATCHERS[tool_name](inputs)
            status = "SUCCESS"
            error_msg = None
        except Exception as exc:
            logger.error(f"IdentityVerificationConnector.{tool_name} failed: {exc}")
            result = {}
            status = "FAILED"
            error_msg = str(exc)

        elapsed_ms = int((time.monotonic() - t0) * 1000) + latency_ms

        await mcp_logger.log(
            connector_name=self.connector_name,
            tool_name=tool_name,
            agent_id=agent_id,
            inputs=inputs,
            output=result,
            status=status,
            latency_ms=elapsed_ms,
            case_id=case_id,
            error_message=error_msg,
            is_simulated=True,
        )

        if status == "FAILED":
            raise RuntimeError(f"{self.connector_name}.{tool_name} failed: {error_msg}")

        return result


identity_verification_connector = IdentityVerificationConnector()
