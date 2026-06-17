from __future__ import annotations

"""DecisionLogService — append-only, hash-chained audit trail (FR-AU-01).

Every agent decision and compliance event must call DecisionLogService.append().
This is the authoritative tamper-evident record. EventLog continues to exist for
operational telemetry and does not replace this.

Chain structure:
    payload_hash = SHA-256(canonical JSON of payload)
    chain_hash   = SHA-256(prev_chain_hash + payload_hash)
    genesis prev_hash = '0' * 64

Concurrent safety: append() uses SELECT ... FOR UPDATE on the last row so that
concurrent writers serialize their chain-link reads before inserting.

WORM semantics: this service intentionally exposes no update() or delete().
In production, also REVOKE UPDATE, DELETE ON decision_log FROM <app_role>.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import DecisionLog


_GENESIS_HASH = "0" * 64


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def compute_hashes(
    payload: dict[str, Any], prev_hash: str
) -> tuple[str, str]:
    """Return (payload_hash, chain_hash) for the given payload and previous chain hash."""
    payload_hash = _sha256(_canonical_json(payload))
    chain_hash = _sha256(prev_hash + payload_hash)
    return payload_hash, chain_hash


@dataclass
class DecisionLogEntry:
    agent_id: str
    event_type: str
    payload: dict[str, Any]
    case_id: UUID | None = None
    client_id: UUID | None = None
    is_compliance_event: bool = False
    is_regulatory_breach: bool = False


class DecisionLogService:
    """Append-only writer and chain-verifier for the decision_log table."""

    # ── Append ────────────────────────────────────────────────────────────────

    async def append(
        self,
        entry: DecisionLogEntry,
        db: AsyncSession | None = None,
    ) -> DecisionLog:
        """Insert one hash-linked row. Never updates or deletes."""
        if db is not None:
            return await self._append_in_session(entry, db)

        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            async with session.begin():
                record = await self._append_in_session(entry, session)
            return record

    async def _append_in_session(
        self, entry: DecisionLogEntry, db: AsyncSession
    ) -> DecisionLog:
        # Lock last row to serialize concurrent appends
        last_row = await db.execute(
            select(DecisionLog.chain_hash)
            .order_by(DecisionLog.seq.desc())
            .limit(1)
            .with_for_update()
        )
        prev_hash = last_row.scalar_one_or_none() or _GENESIS_HASH

        payload_hash, chain_hash = compute_hashes(entry.payload, prev_hash)

        record = DecisionLog(
            case_id=entry.case_id,
            client_id=entry.client_id,
            agent_id=entry.agent_id,
            event_type=entry.event_type,
            payload=entry.payload,
            payload_hash=payload_hash,
            prev_hash=prev_hash,
            chain_hash=chain_hash,
            is_compliance_event=entry.is_compliance_event,
            is_regulatory_breach=entry.is_regulatory_breach,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(record)
        await db.flush()
        return record

    # ── Chain verification ────────────────────────────────────────────────────

    async def verify_chain(
        self, db: AsyncSession
    ) -> tuple[bool, int, int | None]:
        """Walk every row and recompute hashes; return (valid, total, broken_at_seq).

        broken_at_seq is None when the chain is valid.
        """
        result = await db.execute(
            select(DecisionLog).order_by(DecisionLog.seq.asc())
        )
        rows: list[DecisionLog] = result.scalars().all()

        if not rows:
            return True, 0, None

        expected_prev = _GENESIS_HASH
        for row in rows:
            expected_payload_hash = _sha256(_canonical_json(row.payload))
            expected_chain_hash = _sha256(expected_prev + expected_payload_hash)

            if (
                row.payload_hash != expected_payload_hash
                or row.chain_hash != expected_chain_hash
                or row.prev_hash != expected_prev
            ):
                return False, len(rows), row.seq

            expected_prev = row.chain_hash

        return True, len(rows), None


# Module-level singleton
decision_log_service = DecisionLogService()
