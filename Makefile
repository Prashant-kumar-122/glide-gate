# GlideGate / CADF — Common Development Tasks
# Usage: make <target>
#
# See docs/FRAMEWORK.md for full project documentation.

.PHONY: help up down ps build \
        test test-frontend e2e \
        install-hooks doc-check convert-docs \
        portal portal-build portal-e2e \
        db-migrate db-reset \
        audit-check backup

# ─────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────

help:
	@echo ""
	@echo "GlideGate / CADF — Available targets:"
	@echo ""
	@echo "  Infrastructure"
	@echo "    up              Start all services (docker compose)"
	@echo "    up-obs          Start all services + observability overlay"
	@echo "    down            Stop all services"
	@echo "    ps              Show running services"
	@echo ""
	@echo "  Testing"
	@echo "    test            Run backend pytest suite"
	@echo "    test-frontend   Run frontend type-check + jest"
	@echo "    e2e             Run Playwright E2E suite (full stack must be running)"
	@echo ""
	@echo "  Documentation"
	@echo "    install-hooks   Install pre-commit docs-gate git hook"
	@echo "    doc-check       Verify TRACEABILITY.md is up to date (CI use)"
	@echo "    convert-docs    Convert docs/specs/*.docx to Markdown"
	@echo ""
	@echo "  Frontend"
	@echo "    portal          Start frontend dev server (http://localhost:5173)"
	@echo "    portal-build    Type-check + production build"
	@echo "    portal-e2e      Run Playwright E2E + axe accessibility checks"
	@echo ""
	@echo "  Database"
	@echo "    db-migrate      Run pending Alembic migrations"
	@echo "    db-reset        Drop + recreate all tables (dev only)"
	@echo ""
	@echo "  Operations"
	@echo "    audit-check     Verify decision_log hash chain integrity"
	@echo "    backup          Run database + document store backup"
	@echo ""

# ─────────────────────────────────────────────
# Infrastructure
# ─────────────────────────────────────────────

up:
	docker compose up -d

up-obs:
	docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d

down:
	docker compose down

ps:
	docker compose ps

# ─────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────

test:
	cd backend && poetry run pytest tests/ -v --tb=short

test-frontend:
	cd frontend && npm run typecheck && npm test -- --run

e2e:
	cd frontend && npm run test:e2e

# ─────────────────────────────────────────────
# Documentation
# ─────────────────────────────────────────────

install-hooks:
	@echo "Installing pre-commit docs-gate hook..."
	cp scripts/git-hooks/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "Done. Hook installed at .git/hooks/pre-commit"
	@echo "To enforce blocking: set DOCS_GATE=block before committing."

doc-check:
	@echo "Checking for unstaged TRACEABILITY.md changes..."
	@if git diff --name-only HEAD -- docs/TRACEABILITY.md | grep -q TRACEABILITY; then \
		echo "WARNING: TRACEABILITY.md has uncommitted changes."; \
	else \
		echo "TRACEABILITY.md is up to date."; \
	fi
	@echo "Checking for stale phase markers in cadf-framework-plan.md..."
	@python3 -c "\
import re, sys; \
content = open('docs/planning/cadf-framework-plan.md').read(); \
planned = re.findall(r'\[ \] \*\*Phase', content); \
done = re.findall(r'\[x\] \*\*Phase', content); \
print(f'Phases planned: {len(planned)}, completed: {len(done)}');"

convert-docs:
	@echo "Converting docs/specs/*.docx to Markdown..."
	@if command -v uv >/dev/null 2>&1; then \
		for f in docs/specs/*.docx; do \
			out="docs/specs/$$(basename "$$f" .docx).md"; \
			echo "  $$f → $$out"; \
			uv run --with python-docx python scripts/convert_docx.py "$$f" "$$out"; \
		done; \
	else \
		echo "uv not found. Install with: pip install uv"; \
		echo "Or: pip install python-docx && python scripts/convert_docx.py <in.docx> <out.md>"; \
	fi

# ─────────────────────────────────────────────
# Frontend
# ─────────────────────────────────────────────

portal:
	cd frontend && npm install && npm run dev

portal-build:
	cd frontend && npm run typecheck && npm run build

portal-e2e:
	cd frontend && npm run test:e2e

# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────

db-migrate:
	cd backend && poetry run alembic upgrade head

db-reset:
	@echo "WARNING: This will drop and recreate all tables. Press Ctrl+C to cancel."
	@sleep 3
	cd backend && poetry run alembic downgrade base && poetry run alembic upgrade head

# ─────────────────────────────────────────────
# Operations
# ─────────────────────────────────────────────

audit-check:
	@if [ -f scripts/ops/audit_integrity_check.sh ]; then \
		bash scripts/ops/audit_integrity_check.sh; \
	else \
		echo "audit_integrity_check.sh not yet created (Phase 13)."; \
	fi

backup:
	@if [ -f scripts/ops/backup.sh ]; then \
		bash scripts/ops/backup.sh; \
	else \
		echo "backup.sh not yet created (Phase 13)."; \
	fi
