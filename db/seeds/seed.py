"""Master seed runner — executes all seed scripts in order.

Usage (from repo root):
    cd backend && python ../db/seeds/seed.py
"""
from __future__ import annotations

import asyncio
import importlib.util
import io
import sys
from pathlib import Path

# Force UTF-8 output so box-drawing characters work on Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure backend/app is importable
_backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

_seeds_dir = Path(__file__).parent

from app.database import AsyncSessionLocal  # noqa: E402 — after sys.path setup


def _load_seed(filename: str):
    """Dynamically load a seed module by filename (works even with digit prefixes)."""
    path = _seeds_dir / filename
    spec = importlib.util.spec_from_file_location(filename.replace(".py", ""), path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


SEED_FILES = [
    ("01 — Products",             "01_products.py"),
    ("02 — Agents",               "02_agents.py"),
    ("03 — Questionnaire",        "03_questionnaire.py"),
    ("04 — Client: Aarav Mehta",  "04_client_aarav_mehta.py"),
    ("05 — Sample Case",          "05_sample_case.py"),
    ("06 — Sample Events",        "06_sample_events.py"),
    ("07 — Auth Users",           "07_users.py"),
    ("08 — Admin Config",         "08_admin_config.py"),
]


async def run_all() -> None:
    print("═" * 60)
    print("GlideGate CADF — Seed Runner")
    print("═" * 60)
    async with AsyncSessionLocal() as session:
        for label, filename in SEED_FILES:
            print(f"\n▶ {label}")
            mod = _load_seed(filename)
            await mod.seed(session)
    print("\n" + "═" * 60)
    print("Seed complete.")
    print("═" * 60)


if __name__ == "__main__":
    asyncio.run(run_all())
