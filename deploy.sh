#!/bin/bash
set -e

echo "Starting deployment..."

# Get current git commit SHA
GIT_SHA=$(git rev-parse --short HEAD)
echo "Deploying commit: $GIT_SHA"

# Pull latest code
echo "Pulling latest code from COPS_Agentic_AI_Deploy..."
git pull origin COPS_Agentic_AI_Deploy

# Ensure required directories exist with correct permissions for postgres container
mkdir -p db/data
sudo chown -R 999:999 db/data

# Stop old containers
echo "Stopping old containers..."
docker-compose down

# Build new images
echo "Building Docker images..."
DOCKER_BUILDKIT=0 docker-compose build

# Tag images with git commit SHA
echo "Tagging images with commit: $GIT_SHA"
docker tag glidegate_backend:latest glidegate_backend:$GIT_SHA
docker tag glidegate_frontend:latest glidegate_frontend:$GIT_SHA

# Keep only last 3 versions (current + 2 previous), delete older ones
echo "Pruning old images, keeping last 3..."
docker images glidegate_backend --format "{{.Tag}}" | grep -v latest | sort -r | tail -n +4 | xargs -I {} docker rmi glidegate_backend:{} 2>/dev/null || true
docker images glidegate_frontend --format "{{.Tag}}" | grep -v latest | sort -r | tail -n +4 | xargs -I {} docker rmi glidegate_frontend:{} 2>/dev/null || true

# Start containers via startup script
echo "Starting containers..."
bash docker-startup.sh

echo "Deployment complete! Deployed commit: $GIT_SHA"
docker-compose ps
