#!/bin/bash
set -e

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: bash rollback.sh <git-commit-sha>"
    echo ""
    echo "Available versions:"
    docker images glidegate_backend --format "{{.Tag}}" | grep -v latest | sort -r
    exit 1
fi

echo "Rolling back to commit: $VERSION"

# Re-tag the requested version as latest
docker tag glidegate_backend:$VERSION glidegate_backend:latest
docker tag glidegate_frontend:$VERSION glidegate_frontend:latest

# Restart containers with the rolled-back image
docker-compose down
docker-compose up -d

echo "Rollback to $VERSION complete!"
docker-compose ps
