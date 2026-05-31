#!/bin/bash
set -e

echo "Starting deployment..."

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
docker-compose build

# Start containers via startup script
echo "Starting containers..."
bash docker-startup.sh

echo "Deployment complete!"
docker-compose ps
