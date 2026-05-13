from __future__ import annotations

import asyncio
import random
import time
from typing import Any
from uuid import UUID

from loguru import logger

from app.mcp.mcp_connector import MCPConnector, MCPToolDefinition
from app.mcp.mcp_logger import mcp_logger
from app.mcp.connectors.document_management.simulator import (
    simulate_upload_document,
    simulate_retrieve_document,
    simulate_get_document_status,
    simulate_extract_ocr,
)

_TOOLS: list[MCPToolDefinition] = [
    MCPToolDefinition(
        name="upload_document",
        description="Upload a document to the document management system.",
        input_schema={
            "type": "object",
            "required": ["file_name", "file_size", "content_type", "document_category"],
            "properties": {
                "file_name": {"type": "string"},
                "file_size": {"type": "integer"},
                "content_type": {"type": "string"},
                "document_category": {
                    "type": "string",
                    "enum": ["identity", "financial", "legal", "insurance", "compliance", "entity"],
                },
                "case_id": {"type": "string"},
                "client_id": {"type": "string"},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "storage_url": {"type": "string"},
                "upload_status": {"type": "string"},
                "checksum": {"type": "string"},
                "uploaded_at": {"type": "string"},
            },
        },
    ),
    MCPToolDefinition(
        name="retrieve_document",
        description="Retrieve document metadata and a time-limited download URL.",
        input_schema={
            "type": "object",
            "required": ["document_id"],
            "properties": {
                "document_id": {"type": "string"},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "file_name": {"type": "string"},
                "content_type": {"type": "string"},
                "storage_url": {"type": "string"},
                "download_url": {"type": "string"},
                "file_size": {"type": "integer"},
                "status": {"type": "string"},
            },
        },
    ),
    MCPToolDefinition(
        name="get_document_status",
        description="Get the current lifecycle status of a document.",
        input_schema={
            "type": "object",
            "required": ["document_id"],
            "properties": {
                "document_id": {"type": "string"},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "status": {"type": "string"},
                "last_updated": {"type": "string"},
                "reviewer_id": {"type": "string", "nullable": True},
            },
        },
    ),
    MCPToolDefinition(
        name="extract_ocr",
        description="Run OCR extraction on a stored document and return structured field data.",
        input_schema={
            "type": "object",
            "required": ["document_id"],
            "properties": {
                "document_id": {"type": "string"},
                "document_category": {
                    "type": "string",
                    "enum": ["identity", "financial", "legal", "insurance", "compliance", "entity"],
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "extracted_fields": {"type": "object"},
                "confidence": {"type": "number"},
                "extraction_quality": {"type": "string"},
                "pages_processed": {"type": "integer"},
            },
        },
    ),
]

_DISPATCHERS = {
    "upload_document": simulate_upload_document,
    "retrieve_document": simulate_retrieve_document,
    "get_document_status": simulate_get_document_status,
    "extract_ocr": simulate_extract_ocr,
}


class DocumentManagementConnector(MCPConnector):
    connector_name = "document_management"

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
            logger.error(f"DocumentManagementConnector.{tool_name} failed: {exc}")
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


document_management_connector = DocumentManagementConnector()
