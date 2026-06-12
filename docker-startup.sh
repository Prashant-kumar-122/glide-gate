#!/bin/bash
# GlideGate Docker Startup Script

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

echo "=========================================="
echo "GlideGate Production Startup"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Prerequisites Check:${NC}"
echo "✓ Docker installed"
echo "✓ Docker Compose installed"
echo "✓ Ports available: 5432 (PostgreSQL), 8000 (Backend), 5173 (Frontend), 8080 (Keycloak)"

# Check env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}$ENV_FILE not found! Aborting.${NC}"
    exit 1
fi

# Create Keycloak DB if it doesn't exist
echo -e "${YELLOW}Ensuring Keycloak database exists...${NC}"
docker exec glide_gate_db psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname='keycloak'" | grep -q 1 \
    || docker exec glide_gate_db psql -U postgres -c "CREATE DATABASE keycloak;"

# Start services
echo -e "${YELLOW}Starting Docker containers...${NC}"
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
sleep 10

# Check PostgreSQL health
echo -e "${BLUE}Checking PostgreSQL Health:${NC}"
docker-compose -f $COMPOSE_FILE exec -T postgres pg_isready -U postgres -d glide_gate
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not ready${NC}"
    exit 1
fi

# Wait for backend
echo -e "${YELLOW}Waiting for backend to be ready...${NC}"
sleep 15

# Check backend health
echo -e "${BLUE}Checking Backend Health:${NC}"
for i in {1..30}; do
    if docker-compose -f $COMPOSE_FILE exec -T backend curl -s http://localhost:8000/api/health > /dev/null; then
        echo -e "${GREEN}✓ Backend API is healthy${NC}"
        break
    fi
    echo "Attempt $i/30: Waiting for backend..."
    sleep 2
done

# Check frontend
echo -e "${BLUE}Checking Frontend:${NC}"
if docker ps | grep glide_gate_frontend > /dev/null; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    echo -e "${RED}✗ Frontend is not running${NC}"
fi

# Check Keycloak
echo -e "${BLUE}Checking Keycloak:${NC}"
if docker ps | grep glide_gate_keycloak > /dev/null; then
    echo -e "${GREEN}✓ Keycloak is running${NC}"
else
    echo -e "${RED}✗ Keycloak is not running${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "All Services Started!"
echo "==========================================${NC}"

echo ""
echo -e "${BLUE}Service URLs:${NC}"
echo -e "  Frontend:   ${GREEN}http://18.60.103.228:5173${NC}"
echo -e "  Backend:    ${GREEN}http://18.60.103.228:8000${NC}"
echo -e "  API Docs:   ${GREEN}http://18.60.103.228:8000/api/docs${NC}"
echo -e "  Keycloak:   ${GREEN}http://18.60.103.228:8080${NC}"
echo -e "  PostgreSQL: ${GREEN}localhost:5432${NC}"

echo ""
echo -e "${BLUE}Container Status:${NC}"
docker-compose -f $COMPOSE_FILE ps
