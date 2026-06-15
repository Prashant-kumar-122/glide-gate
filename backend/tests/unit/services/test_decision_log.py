"""Phase 2.5 — unit tests for DecisionLogService hash-chain.

These tests are pure Python (no DB required). They cover:
  - compute_hashes produces correct SHA-256 values
  - Genesis entry uses '0'*64 as prev_hash
  - verify_chain passes on a valid chain
  - verify_chain detects a corrupted payload_hash
  - verify_chain detects a corrupted chain_hash
  - verify_chain detects a tampered prev_hash
  - Service has no update() or delete() method (WORM enforcement at Python layer)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.audit.decision_log_service import (
    _GENESIS_HASH,
    _canonical_json,
    _sha256,
    compute_hashes,
    DecisionLogEntry,
    DecisionLogService,
)


# ── Hash helpers ──────────────────────────────────────────────────────────────


def test_sha256_is_deterministic() -> None:
    assert _sha256("hello") == _sha256("hello")


def test_canonical_json_is_sorted() -> None:
    a = _canonical_json({"z": 1, "a": 2})
    b = _canonical_json({"a": 2, "z": 1})
    assert a == b


def test_compute_hashes_genesis() -> None:
    payload = {"agent_id": "kyc", "decision": "PASS"}
    payload_hash, chain_hash = compute_hashes(payload, _GENESIS_HASH)

    expected_payload_hash = hashlib.sha256(_canonical_json(payload).encode()).hexdigest()
    expected_chain_hash = hashlib.sha256((_GENESIS_HASH + expected_payload_hash).encode()).hexdigest()

    assert payload_hash == expected_payload_hash
    assert chain_hash == expected_chain_hash


def test_compute_hashes_chained() -> None:
    payload1 = {"step": 1}
    p1_hash, c1_hash = compute_hashes(payload1, _GENESIS_HASH)

    payload2 = {"step": 2}
    p2_hash, c2_hash = compute_hashes(payload2, c1_hash)

    # c2_hash must incorporate c1_hash (chain links)
    expected_c2 = hashlib.sha256((c1_hash + p2_hash).encode()).hexdigest()
    assert c2_hash == expected_c2


# ── Service WORM contract ─────────────────────────────────────────────────────


def test_decision_log_service_has_no_update_method() -> None:
    service = DecisionLogService()
    assert not hasattr(service, "update"), "DecisionLogService must not expose update()"


def test_decision_log_service_has_no_delete_method() -> None:
    service = DecisionLogService()
    assert not hasattr(service, "delete"), "DecisionLogService must not expose delete()"


# ── verify_chain with mocked DB ───────────────────────────────────────────────


def _make_row(seq: int, payload: dict, prev_hash: str) -> MagicMock:
    """Build a mock DecisionLog row with correct hashes."""
    payload_hash, chain_hash = compute_hashes(payload, prev_hash)
    row = MagicMock()
    row.seq = seq
    row.payload = payload
    row.payload_hash = payload_hash
    row.prev_hash = prev_hash
    row.chain_hash = chain_hash
    return row


def _mock_db_with_rows(rows: list) -> AsyncMock:
    """Return an AsyncSession mock whose execute().scalars().all() yields the given rows."""
    db = AsyncMock()
    sync_result = MagicMock()
    sync_result.scalars.return_value.all.return_value = rows
    db.execute.return_value = sync_result
    return db


@pytest.mark.asyncio
async def test_verify_chain_empty() -> None:
    service = DecisionLogService()
    db = _mock_db_with_rows([])

    valid, total, broken_at = await service.verify_chain(db)
    assert valid is True
    assert total == 0
    assert broken_at is None


@pytest.mark.asyncio
async def test_verify_chain_valid() -> None:
    service = DecisionLogService()

    payload1 = {"event": "KYC_PASSED"}
    payload2 = {"event": "STAGE_ADVANCED"}
    _, c1 = compute_hashes(payload1, _GENESIS_HASH)

    row1 = _make_row(1, payload1, _GENESIS_HASH)
    row2 = _make_row(2, payload2, c1)
    db = _mock_db_with_rows([row1, row2])

    valid, total, broken_at = await service.verify_chain(db)
    assert valid is True
    assert total == 2
    assert broken_at is None


@pytest.mark.asyncio
async def test_verify_chain_detects_corrupted_payload_hash() -> None:
    service = DecisionLogService()

    row1 = _make_row(1, {"event": "KYC_PASSED"}, _GENESIS_HASH)
    row1.payload_hash = "deadbeef" * 8  # tampered
    db = _mock_db_with_rows([row1])

    valid, total, broken_at = await service.verify_chain(db)
    assert valid is False
    assert broken_at == 1


@pytest.mark.asyncio
async def test_verify_chain_detects_corrupted_chain_hash() -> None:
    service = DecisionLogService()

    row1 = _make_row(1, {"event": "KYC_PASSED"}, _GENESIS_HASH)
    row1.chain_hash = "cafebabe" * 8  # tampered
    db = _mock_db_with_rows([row1])

    valid, total, broken_at = await service.verify_chain(db)
    assert valid is False
    assert broken_at == 1


@pytest.mark.asyncio
async def test_verify_chain_detects_tampered_prev_hash() -> None:
    service = DecisionLogService()

    payload1 = {"event": "KYC_PASSED"}
    _, c1 = compute_hashes(payload1, _GENESIS_HASH)
    payload2 = {"event": "STAGE_ADVANCED"}

    row1 = _make_row(1, payload1, _GENESIS_HASH)
    row2 = _make_row(2, payload2, c1)
    row2.prev_hash = _GENESIS_HASH  # wrong: should be c1

    db = _mock_db_with_rows([row1, row2])

    valid, total, broken_at = await service.verify_chain(db)
    assert valid is False
    assert broken_at == 2


@pytest.mark.asyncio
async def test_verify_chain_reports_seq_of_first_broken_row() -> None:
    """Chain breaks at row 5; rows 1-4 are valid."""
    service = DecisionLogService()

    rows = []
    prev = _GENESIS_HASH
    for i in range(1, 6):
        payload = {"step": i}
        row = _make_row(i, payload, prev)
        _, c = compute_hashes(payload, prev)
        prev = c
        rows.append(row)

    rows[4].payload_hash = "00" * 32  # corrupt row 5

    db = _mock_db_with_rows(rows)

    valid, total, broken_at = await service.verify_chain(db)
    assert valid is False
    assert total == 5
    assert broken_at == 5
