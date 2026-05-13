from app.mcp.connectors.document_management.connector import (
    DocumentManagementConnector,
    document_management_connector,
)
from app.mcp.connectors.document_management.simulator import (
    simulate_upload_document,
    simulate_retrieve_document,
    simulate_get_document_status,
    simulate_extract_ocr,
)

__all__ = [
    "DocumentManagementConnector",
    "document_management_connector",
    "simulate_upload_document",
    "simulate_retrieve_document",
    "simulate_get_document_status",
    "simulate_extract_ocr",
]
