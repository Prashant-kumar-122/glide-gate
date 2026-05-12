from __future__ import annotations

import difflib
import re
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel


DiffChangeType = Literal["added", "modified", "removed", "unchanged"]


class DiffSection(BaseModel):
    section: str            # field name or paragraph heading
    change_type: DiffChangeType
    old_value: str | None = None
    new_value: str | None = None
    line_number: int | None = None


class DiffResult(BaseModel):
    diff_id: UUID
    document_id: UUID | None
    old_version: int
    new_version: int
    sections: list[DiffSection]
    added_count: int
    modified_count: int
    removed_count: int
    unchanged_count: int
    similarity_ratio: float     # 0.0–1.0
    summary: str
    computed_at: str


def _tokenise(text: str) -> dict[str, str]:
    """
    Split document text into labelled sections by looking for 'Key: Value' lines.
    Falls back to line-numbered segments when the document lacks labelled fields.
    """
    sections: dict[str, str] = {}
    pattern = re.compile(r"^([A-Za-z][A-Za-z0-9 _/\-]{1,40}):\s*(.+)$")

    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            key = match.group(1).strip().lower().replace(" ", "_")
            sections[key] = match.group(2).strip()
        else:
            sections[f"line_{i}"] = line

    return sections


class VersionDiffDetector:
    """
    Detects field-level differences between two document versions (BRD FR-09).

    Accepts raw extracted text or structured field dicts.
    Uses Python difflib for similarity scoring and change detection.
    """

    def compute(
        self,
        document_id: UUID | None,
        old_version: int,
        new_version: int,
        old_text: str,
        new_text: str,
    ) -> DiffResult:
        old_sections = _tokenise(old_text)
        new_sections = _tokenise(new_text)

        all_keys = sorted(set(old_sections) | set(new_sections))
        sections: list[DiffSection] = []

        for key in all_keys:
            old_val = old_sections.get(key)
            new_val = new_sections.get(key)

            if old_val is None and new_val is not None:
                sections.append(DiffSection(
                    section=key,
                    change_type="added",
                    new_value=new_val,
                ))
            elif old_val is not None and new_val is None:
                sections.append(DiffSection(
                    section=key,
                    change_type="removed",
                    old_value=old_val,
                ))
            elif old_val != new_val:
                sections.append(DiffSection(
                    section=key,
                    change_type="modified",
                    old_value=old_val,
                    new_value=new_val,
                ))
            else:
                sections.append(DiffSection(
                    section=key,
                    change_type="unchanged",
                    old_value=old_val,
                    new_value=new_val,
                ))

        added = sum(1 for s in sections if s.change_type == "added")
        modified = sum(1 for s in sections if s.change_type == "modified")
        removed = sum(1 for s in sections if s.change_type == "removed")
        unchanged = sum(1 for s in sections if s.change_type == "unchanged")

        ratio = difflib.SequenceMatcher(None, old_text, new_text).ratio()
        summary = self._summarise(added, modified, removed, unchanged, ratio)

        return DiffResult(
            diff_id=uuid4(),
            document_id=document_id,
            old_version=old_version,
            new_version=new_version,
            sections=sections,
            added_count=added,
            modified_count=modified,
            removed_count=removed,
            unchanged_count=unchanged,
            similarity_ratio=round(ratio, 4),
            summary=summary,
            computed_at=datetime.utcnow().isoformat(),
        )

    def compute_from_fields(
        self,
        document_id: UUID | None,
        old_version: int,
        new_version: int,
        old_fields: dict[str, str],
        new_fields: dict[str, str],
    ) -> DiffResult:
        old_text = "\n".join(f"{k}: {v}" for k, v in sorted(old_fields.items()))
        new_text = "\n".join(f"{k}: {v}" for k, v in sorted(new_fields.items()))
        return self.compute(document_id, old_version, new_version, old_text, new_text)

    @staticmethod
    def _summarise(
        added: int, modified: int, removed: int, unchanged: int, ratio: float
    ) -> str:
        total_changes = added + modified + removed
        if total_changes == 0:
            return "No changes detected between versions."

        parts: list[str] = []
        if modified:
            parts.append(f"{modified} field{'s' if modified > 1 else ''} modified")
        if added:
            parts.append(f"{added} field{'s' if added > 1 else ''} added")
        if removed:
            parts.append(f"{removed} field{'s' if removed > 1 else ''} removed")

        similarity_pct = round(ratio * 100, 1)
        return f"{'; '.join(parts)}. Documents are {similarity_pct}% similar."
