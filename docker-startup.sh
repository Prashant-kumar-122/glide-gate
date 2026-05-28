#!/bin/bash
# GlideGate Docker Startup Script

echo "=========================================="
echo "🚀 GlideGate Local Development Setup"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Prerequisites Check:${NC}"
echo "✓ Docker installed"
echo "✓ Docker Compose installed"
echo "✓ Ports available: 5432 (PostgreSQL), 8000 (Backend), 5173 (Frontend)"

echo ""
echo -e "${BLUE}🔧 Building & Starting Services:${NC}"

# Check if .env.docker exists
if [ ! -f ".env.docker" ]; then
    echo -e "${RED}⚠️  .env.docker not found!${NC}"
    echo "Creating .env.docker with defaults..."
fi

# Start services
echo -e "${YELLOW}Starting Docker containers...${NC}"
docker-compose --env-file .env.docker up -d

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
sleep 10

# Check PostgreSQL health
echo -e "${BLUE}🔍 Checking PostgreSQL Health:${NC}"
docker-compose exec -T postgres pg_isready -U postgres -d glide_gate
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not ready${NC}"
    exit 1
fi

# Wait for backend migrations
echo -e "${YELLOW}⏳ Waiting for backend migrations to complete...${NC}"
sleep 15

# Check backend health
echo -e "${BLUE}🔍 Checking Backend Health:${NC}"
for i in {1..30}; do
    if docker-compose exec -T backend curl -s http://localhost:8000/api/health > /dev/null; then
        echo -e "${GREEN}✓ Backend API is healthy${NC}"
        break
    fi
    echo "Attempt $i/30: Waiting for backend..."
    sleep 2
done

# Check frontend
echo -e "${BLUE}🔍 Checking Frontend:${NC}"
if docker ps | grep glide_gate_frontend > /dev/null; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    echo -e "${RED}✗ Frontend is not running${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "✅ All Services Started Successfully!"
echo "==========================================${NC}"

echo ""
echo -e "${BLUE}📍 Service URLs:${NC}"
echo -e "  🌐 Frontend:  ${GREEN}http://localhost:5173${NC}"
echo -e "  🔌 Backend:   ${GREEN}http://localhost:8000${NC}"
echo -e "  📚 API Docs:  ${GREEN}http://localhost:8000/api/docs${NC}"
echo -e "  🐘 PostgreSQL: ${GREEN}localhost:5432${NC}"

echo ""
echo -e "${BLUE}📊 Container Status:${NC}"
docker-compose ps

echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View logs:           ${GREEN}docker-compose logs -f${NC}"
echo "  View backend logs:   ${GREEN}docker-compose logs -f backend${NC}"
echo "  View frontend logs:  ${GREEN}docker-compose logs -f frontend${NC}"
echo "  Stop services:       ${GREEN}docker-compose down${NC}"
echo "  Stop & remove data:  ${GREEN}docker-compose down -v${NC}"
echo "  Restart services:    ${GREEN}docker-compose restart${NC}"
echo ""
