#!/bin/bash
# =============================================================================
# GlideGate Database Migration Script
# =============================================================================
# Run this manually on EC2 when needed:
#   bash migrate.sh              → apply all pending migrations
#   bash migrate.sh stamp        → mark DB as up-to-date without running migrations
#                                  (use on existing DB that was created via db/schema files)
#   bash migrate.sh status       → check current migration status
#   bash migrate.sh history      → show full migration history
# =============================================================================

set -e

COMMAND=${1:-upgrade}

echo "=========================================="
echo "   GlideGate Database Migration"
echo "=========================================="

case "$COMMAND" in

  upgrade)
    echo "Running all pending migrations..."
    docker exec glide_gate_backend poetry run alembic upgrade head
    echo "✓ Migrations complete"
    ;;

  stamp)
    echo "Stamping DB as at HEAD (no migrations run)..."
    echo "Use this when tables already exist from db/schema files."
    docker exec glide_gate_backend poetry run alembic stamp head
    echo "✓ DB stamped at HEAD"
    ;;

  status)
    echo "Current migration status:"
    docker exec glide_gate_backend poetry run alembic current
    ;;

  history)
    echo "Migration history:"
    docker exec glide_gate_backend poetry run alembic history --verbose
    ;;

  *)
    echo "Unknown command: $COMMAND"
    echo "Usage: bash migrate.sh [upgrade|stamp|status|history]"
    exit 1
    ;;

esac

echo "=========================================="
echo "   Current Status"
echo "=========================================="
docker exec glide_gate_backend poetry run alembic current
