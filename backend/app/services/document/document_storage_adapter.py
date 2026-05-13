from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from loguru import logger

from app.config import settings


class StorageResult:
    __slots__ = ("storage_path", "checksum_sha256", "stored_bytes")

    def __init__(self, storage_path: str, checksum_sha256: str, stored_bytes: int) -> None:
        self.storage_path = storage_path
        self.checksum_sha256 = checksum_sha256
        self.stored_bytes = stored_bytes


class DocumentStorageAdapter(ABC):
    """Abstract storage backend for document bytes."""

    @abstractmethod
    async def store(
        self,
        case_id: UUID,
        document_id: UUID,
        filename: str,
        data: bytes,
    ) -> StorageResult: ...

    @abstractmethod
    async def retrieve(self, storage_path: str) -> bytes: ...

    @abstractmethod
    async def delete(self, storage_path: str) -> None: ...


# ── Local disk ────────────────────────────────────────────────────────────────

class LocalStorageAdapter(DocumentStorageAdapter):
    """Stores files under DOCUMENT_STORAGE_PATH / case_id / document_id / filename."""

    def __init__(self, base_path: str | None = None) -> None:
        self._base = Path(base_path or settings.DOCUMENT_STORAGE_PATH)

    async def store(
        self,
        case_id: UUID,
        document_id: UUID,
        filename: str,
        data: bytes,
    ) -> StorageResult:
        dest_dir = self._base / str(case_id) / str(document_id)
        dest_dir.mkdir(parents=True, exist_ok=True)

        safe_name = Path(filename).name  # strip any path traversal
        dest_path = dest_dir / safe_name

        dest_path.write_bytes(data)

        checksum = hashlib.sha256(data).hexdigest()
        storage_path = str(dest_path)
        logger.debug(f"[LocalStorage] Stored {storage_path} ({len(data)} bytes)")
        return StorageResult(
            storage_path=storage_path,
            checksum_sha256=checksum,
            stored_bytes=len(data),
        )

    async def retrieve(self, storage_path: str) -> bytes:
        path = Path(storage_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found at {storage_path}")
        return path.read_bytes()

    async def delete(self, storage_path: str) -> None:
        path = Path(storage_path)
        if path.exists():
            path.unlink()
            logger.debug(f"[LocalStorage] Deleted {storage_path}")


# ── S3-compatible stub ────────────────────────────────────────────────────────

class S3StorageAdapter(DocumentStorageAdapter):
    """S3-compatible stub — raises NotImplementedError until real credentials wired."""

    async def store(self, case_id: UUID, document_id: UUID, filename: str, data: bytes) -> StorageResult:
        raise NotImplementedError(
            "S3StorageAdapter is a stub. Set DOCUMENT_STORAGE_BACKEND=local "
            "or provide real boto3 credentials and implement this method."
        )

    async def retrieve(self, storage_path: str) -> bytes:
        raise NotImplementedError("S3StorageAdapter.retrieve is not implemented")

    async def delete(self, storage_path: str) -> None:
        raise NotImplementedError("S3StorageAdapter.delete is not implemented")


# ── Factory ───────────────────────────────────────────────────────────────────

class StorageAdapterFactory:
    _instance: DocumentStorageAdapter | None = None

    @classmethod
    def get(cls) -> DocumentStorageAdapter:
        if cls._instance is None:
            backend = settings.DOCUMENT_STORAGE_BACKEND
            if backend == "s3":
                cls._instance = S3StorageAdapter()
                logger.info("[StorageFactory] Using S3StorageAdapter (stub)")
            else:
                cls._instance = LocalStorageAdapter()
                logger.info(
                    f"[StorageFactory] Using LocalStorageAdapter "
                    f"path={settings.DOCUMENT_STORAGE_PATH}"
                )
        return cls._instance


storage_adapter = StorageAdapterFactory.get()
