# GlideGate Docker Setup Guide

## Quick Start

### Windows (PowerShell)
```powershell
cd c:\Users\Prashant Kumar\office_projects\glidegate
.\docker-startup.ps1
```

### macOS / Linux (Bash)
```bash
cd /path/to/glidegate
bash docker-startup.sh
```

### Manual Start (All Platforms)
```bash
docker-compose --env-file .env.docker up -d
```

---

## 📍 Access Points

After startup,  access your services at:

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:5173 | React/Vite UI |
| **Backend API** | http://localhost:8000 | FastAPI server |
| **API Documentation** | http://localhost:8000/api/docs | Swagger UI for APIs |
| **PostgreSQL** | localhost:5432 | Database (psql connection) |

---


## 🔧 Environment Configuration

The setup uses `.env.docker` which contains:
- `DB_USER=postgres`
- `DB_PASSWORD=newpassword`
- `DB_NAME=glide_gate`
- AI provider credentials (optional)

To modify, edit `.env.docker` before running `docker-compose`.

---

## 📊 Useful Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend

# PostgreSQL only
docker-compose logs -f postgres
```

### Stop Services
```bash
# Stop but keep data
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop, remove containers, AND delete database volume
docker-compose down -v
```

### Restart
```bash
# Restart all services
docker-compose restart

# Rebuild images and restart
docker-compose up -d --build
```

### Execute Commands in Container
```bash
# Backend shell
docker-compose exec backend bash

# PostgreSQL shell
docker-compose exec postgres psql -U postgres -d glide_gate

# Run migrations manually
docker-compose exec backend poetry run alembic upgrade head

# Run specific backend command
docker-compose exec backend python -m pytest tests/
```

### Check Container Status
```bash
docker-compose ps
```

---

## 🔍 Troubleshooting

### PostgreSQL Connection Failed
```bash
# Check if postgres service is healthy
docker-compose ps postgres

# View postgres logs
docker-compose logs postgres

# Manually connect to test
docker-compose exec postgres psql -U postgres -d glide_gate
```

### Backend Not Starting
```bash
# Check backend logs
docker-compose logs backend

# Verify database connection
docker-compose exec backend curl http://postgres:5432

# Check if migrations ran
docker-compose logs backend | grep -i alembic
```

### Frontend Not Connecting to Backend
1. Ensure backend is running: `docker-compose ps backend`
2. Check CORS settings in backend `.env.docker`
3. Verify `VITE_API_URL` in frontend environment
4. Check frontend logs: `docker-compose logs frontend`

### Ports Already in Use
If port 5432, 8000, or 5173 is already in use:
1. Stop conflicting services
2. Or change ports in `docker-compose.yml`:
   ```yaml
   ports:
     - "5433:5432"    # PostgreSQL
     - "8001:8000"    # Backend
     - "5174:5173"    # Frontend
   ```

### Need to Clean Start
```bash
# Remove all containers and volumes
docker-compose down -v

# Rebuild from scratch
docker-compose --env-file .env.docker up -d --build
```

---

## 🗄️ Database Management

### Connect to Database
```bash
# From container
docker-compose exec postgres psql -U postgres -d glide_gate

# From your machine (requires psql installed)
psql -h localhost -U postgres -d glide_gate
# Password: newpassword
```

### Run Migrations
```bash
docker-compose exec backend poetry run alembic upgrade head
```

### Reset Database
```bash
docker-compose down -v
docker-compose up -d postgres
# Wait for postgres to start
docker-compose up -d backend
```

### Seed Sample Data
```bash
docker-compose exec backend python db/seeds/seed.py
```

---

## 📦 Docker Compose Services

### postgres
- **Image**: postgres:16-alpine
- **Port**: 5432
- **Volume**: `postgres_data` (persistent)
- **Health Check**: Every 10s
- **Initialization**: Runs SQL files from `db/schema/`

### backend
- **Image**: Custom (built from `Dockerfile`)
- **Port**: 8000
- **Dependencies**: postgres (waits for health check)
- **Volume**: `./backend:/app` (live code reload)
- **Command**: Runs migrations then uvicorn server

### frontend
- **Image**: node:18-alpine
- **Port**: 5173
- **Volume**: `./frontend/src:/app/src` (live code reload)
- **Command**: npm run dev (Vite dev server)

---

## 🚀 Production Build

To build production-ready images:

```bash
# Build backend
docker build -t glide-gate-backend:latest .

# Build frontend
docker build -t glide-gate-frontend:latest ./frontend

# Push to registry (if configured)
docker tag glide-gate-backend:latest your-registry/glide-gate-backend:latest
docker push your-registry/glide-gate-backend:latest
```

---

## 🔐 Security Notes

**⚠️ For Development Only:**
- Password is hardcoded in `.env.docker`
- Use strong passwords in production
- Don't commit `.env.docker` with real credentials
- Use secrets management (Docker Secrets, AWS Secrets Manager, etc.) in production

---

## 📝 File Structure

```
glidegate/
├── docker-compose.yml        # Main orchestration
├── .env.docker              # Docker environment vars
├── docker-startup.ps1       # Windows startup script
├── docker-startup.sh        # Bash startup script
├── Dockerfile               # Backend + Frontend image
├── .dockerignore             # Exclude from build
├── backend/
│   ├── pyproject.toml       # Poetry dependencies
│   ├── alembic/             # Database migrations
│   └── app/                 # FastAPI application
├── frontend/
│   ├── Dockerfile           # Frontend image
│   ├── package.json         # npm dependencies
│   └── src/                 # React/Vite source
└── db/
    ├── schema/              # SQL initialization scripts
    └── init.sql             # PostgreSQL setup
```

---

Need help? Check logs or raise an issue! 🎯
