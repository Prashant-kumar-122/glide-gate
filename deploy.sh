#!/bin/bash
set -e

echo "Starting deployment..."

# Pull latest code
echo "Pulling latest code from main..."
git pull origin main

# Build Docker images
echo "Building Docker images..."
docker-compose build

# Start containers in detached mode
echo "Starting containers..."
docker-compose up -d

echo "Deployment complete!"
docker-compose ps
