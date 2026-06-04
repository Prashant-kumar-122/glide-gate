#!/bin/bash
# Run Alembic migrations manually on EC2
# Usage: bash migrate.sh
# Run this after deployment when schema changes are needed

set -e

echo "=========================================="
echo "   Running Alembic Migrations"
echo "=========================================="

docker exec glide_gate_backend poetry run alembic upgrade head

echo "=========================================="
echo "   Migration Status"
echo "=========================================="

docker exec glide_gate_backend poetry run alembic current

echo "✓ Migrations complete"
