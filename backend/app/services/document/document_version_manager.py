from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documents import Document


class DocumentVersionManager:
    """Tracks document versions using the parent_doc_id self-referential FK.

    Each resubmission points to its predecessor via parent_doc_id.
    Version numbers are integers starting at 1; each resubmission increments
    by 1 relative to its parent.
    """

    async def next_version(
        self,
        parent_doc_id: UUID | None,
        db: AsyncSession,
    ) -> int:
        """Return the version number for a new document.

        If no parent_doc_id is provided this is the first upload → version 1.
        Otherwise it is the parent's version + 1.
        """
        if parent_doc_id is None:
            return 1

        result = await db.execute(
            select(Document.version).where(Document.id == parent_doc_id)
        )
        parent_version = result.scalar_one_or_none()
        if parent_version is None:
            return 1
        return parent_version + 1

    async def get_version_chain(
        self,
        doc_id: UUID,
        db: AsyncSession,
    ) -> list[Document]:
        """Return all versions of a document (oldest first).

        Walks the parent_doc_id chain upward to find the root, then
        queries for all documents sharing that root.
        """
        # Find the root document
        root_id = await self._find_root(doc_id, db)

        # Collect all documents that are descendants of the root (including root)
        result = await db.execute(
            select(Document)
            .where(
                (Document.id == root_id) | (Document.parent_doc_id == root_id)
            )
            .order_by(Document.version)
        )
        return list(result.scalars().all())

    async def _find_root(self, doc_id: UUID, db: AsyncSession) -> UUID:
        """Walk parent_doc_id links to find the original root document."""
        current_id = doc_id
        visited: set[UUID] = set()

        while True:
            if current_id in visited:
                break
            visited.add(current_id)

            result = await db.execute(
                select(Document.parent_doc_id).where(Document.id == current_id)
            )
            parent_id = result.scalar_one_or_none()
            if parent_id is None:
                break
            current_id = parent_id

        return current_id


document_version_manager = DocumentVersionManager()
