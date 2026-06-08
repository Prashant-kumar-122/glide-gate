# GlideGate CI/CD Pipeline — KT Document

## Overview

Every push to the `COPS_Agentic_AI_Deploy` branch automatically triggers a 4-stage GitLab CI/CD pipeline that validates, builds, and deploys the application to an AWS EC2 instance.

---

## Architecture

```
Developer Machine          GitLab Server              AWS EC2 (18.60.103.228)
      |                         |                              |
      | git push                |                              |
      |------------------------>|                              |
      |                         | Pipeline Triggered           |
      |                         |                              |
      |                  Stage 1: PREPARE                      |
      |                         | SSH → git fetch + reset      |
      |                         |----------------------------->|
      |                         |      ✓ Code synced           |
      |                         |<-----------------------------|
      |                         |                              |
      |                  Stage 2: VALIDATE                     |
      |                         | SSH → npm install + build    |
      |                         |----------------------------->|
      |                         |      ✓ Frontend validated    |
      |                         |<-----------------------------|
      |                         |                              |
      |                  Stage 3: BUILD                        |
      |                         | SSH → docker-compose build   |
      |                         |----------------------------->|
      |                         |      ✓ Images built & tagged |
      |                         |<-----------------------------|
      |                         |                              |
      |                  Stage 4: DEPLOY                       |
      |                         | SSH → start containers       |
      |                         |----------------------------->|
      |                         |      ✓ App live              |
      |                         |<-----------------------------|
```

---

## Trigger

- **Branch:** `COPS_Agentic_AI_Deploy` only
- **Event:** Any push to this branch (`$CI_PIPELINE_SOURCE == "push"`)

---

## Runner

- **Tag:** `ec2 arm64 ubuntu`
- **Location:** GitLab Runner installed on the same EC2 instance
- **Architecture:** ARM64 (AWS Graviton)

---

## SSH Authentication

Each stage SSHs into the EC2 using:
- **Host:** `18.60.103.228`
- **User:** `ubuntu`
- **Key:** Stored as `EC2_SSH_KEY` GitLab CI/CD Variable (File type, unprotected)
- **Known hosts:** Added dynamically via `ssh-keyscan` in `before_script`

---

## Stages

### Stage 1 — PREPARE
**Purpose:** Force-sync the EC2 deployment directory with the latest remote branch code.

**What it does:**
```bash
cd /home/ubuntu/office_project/glidegate
git fetch origin
git reset --hard origin/COPS_Agentic_AI_Deploy
```

**Why `reset --hard` instead of `git pull`:**
- `git pull` can fail silently if EC2 has local changes or diverged history
- `reset --hard` forces exact match with remote — no stale or missing files

**Failure impact:** Pipeline stops. No code change on EC2.

---

### Stage 2 — VALIDATE (validate-frontend)
**Purpose:** Verify the frontend compiles successfully before spending time on Docker builds.

**What it does:**
```bash
sudo rm -rf frontend/node_modules   # clear root-owned modules from previous Docker run
cd frontend
npm install --legacy-peer-deps      # install dependencies (Node.js 18)
npm run build                       # tsc -b && vite build (strict TypeScript check)
```

**Environment:** Node.js 18 installed on EC2 (matches `node:18-alpine` in Dockerfile)

**Why `npm run build` and not `npm run dev`:**
- `npm run build` runs `tsc -b` (strict TypeScript compiler) + `vite build`
- Catches type errors, missing imports, unused variables
- `npm run dev` is lenient and only shows errors in the browser

**Failure impact:** Pipeline stops. Docker build never starts. Running containers untouched.

---

### Stage 3 — BUILD
**Purpose:** Build production Docker images for backend and frontend, tag with git commit SHA.

**What it does:**
```bash
mkdir -p db/data
sudo chown -R 999:999 db/data          # set correct ownership for Postgres container
DOCKER_BUILDKIT=0 docker-compose build # build backend + frontend images

# Tag images with git commit SHA for versioning
docker tag glidegate_backend:latest glidegate_backend:<SHA>
docker tag glidegate_frontend:latest glidegate_frontend:<SHA>

# Keep only last 3 versions, prune older images
docker images glidegate_backend --format "{{.Tag}}" | grep -v latest | sort -r | tail -n +4 | xargs docker rmi
```

**Docker build steps per service:**

| Service | Base Image | Build Steps |
|---------|-----------|-------------|
| Backend | `python:3.12-slim` | Poetry install → import check (`from app.main import app`) → copy code |
| Frontend | `node:18-alpine` | npm install → `npm run build` (compile check) → copy code |

**Image versioning:**
- Each build creates `glidegate_backend:<git-SHA>` and `glidegate_frontend:<git-SHA>`
- Last 3 versions kept on EC2 for rollback
- `latest` tag always points to current build

**Why `DOCKER_BUILDKIT=0`:** BuildKit is enabled globally on the EC2 but `buildx` is not installed. Legacy builder is used instead.

**Failure impact:** Pipeline stops. Running containers untouched. Previous images preserved for rollback.

---

### Stage 4 — DEPLOY
**Purpose:** Replace running containers with newly built images.

**What it does:**
```bash
docker-compose down           # gracefully stop all containers
bash docker-startup.sh        # start new containers + health checks
docker-compose ps             # print final container status
```

**docker-startup.sh sequence:**
1. `docker-compose up -d` — start all 3 services (postgres, backend, frontend)
2. Wait for PostgreSQL to be ready (`pg_isready`)
3. Wait for backend health check (`/api/health` returns 200)
4. Confirm frontend container is running
5. Print service URLs and container status

**Services started:**

| Service | Container | Port | Health Check |
|---------|-----------|------|-------------|
| PostgreSQL | `glide_gate_db` | 5432 | `pg_isready` |
| Backend (Gunicorn) | `glide_gate_backend` | 8000 | `GET /api/health` |
| Frontend (Vite) | `glide_gate_frontend` | 5173 | `wget localhost:5173` |

**Failure impact:** If deploy fails, `docker-compose down` has already run. Manual intervention needed to restart containers.

---

## Health Check Endpoints

| Endpoint | Description |
|----------|-------------|
| `http://18.60.103.228:8000/api/health` | Backend health — checks DB connectivity |
| `http://18.60.103.228:5173` | Frontend — Vite dev server |
| `http://18.60.103.228:8000/api/docs` | Swagger API documentation |

**Backend health response:**
```json
{
  "status": "ok",
  "timestamp": "2026-06-02T08:00:00Z",
  "version": "0.1.0",
  "env": "development",
  "database": "connected",
  "demo_mode": false
}
```

---

## Rollback

To roll back to a previous version on EC2:
```bash
ssh ubuntu@18.60.103.228
cd /home/ubuntu/office_project/glidegate

# List available versions
./rollback.sh

# Roll back to specific commit
./rollback.sh <git-commit-sha>
```

`rollback.sh` re-tags the selected version as `latest` and restarts containers.

---

## Data Persistence

- **PostgreSQL data:** Stored at `/home/ubuntu/office_project/glidegate/db/data/` on EC2
- **Mounted as:** `./db/data:/var/lib/postgresql/data` in docker-compose
- **Permission:** `700` owned by uid `999` (postgres container user) — intentional security restriction
- **Excluded from Docker build context:** via `.dockerignore` entry `db/data`

---

## Key Files

| File | Purpose |
|------|---------|
| `.gitlab-ci.yml` | Pipeline definition |
| `docker-compose.yml` | Service orchestration |
| `Dockerfile` | Backend image build |
| `frontend/Dockerfile` | Frontend image build |
| `deploy.sh` | Deployment script (called by pipeline) |
| `docker-startup.sh` | Container startup + health checks |
| `rollback.sh` | Rollback to previous image version |
| `.env.docker` | Environment variables for Docker services |
| `backend/.dockerignore` | Excludes Python cache, venv from backend build |
| `.dockerignore` | Excludes `db/data`, `node_modules` from build context |

---

## Completed

1. ✅ Move SSH key to GitLab CI/CD Variable (`EC2_SSH_KEY`, File type)
2. ✅ Fix Alembic migration `0005` FK seed issue — re-enabled in `docker-compose.yml`
3. ✅ Upgrade Node.js to `20.20.2` on EC2 and `frontend/Dockerfile`
4. ✅ Pin Poetry to `2.4.1` in `Dockerfile`
5. ✅ Fix ASGI entrypoint to use `socket_app`
6. ✅ Remove `./backend:/app` volume mount shadowing image
7. ✅ Enable `depends_on` with `service_healthy` for backend → postgres

---

## Pending TODOs

**High Priority**
- Secrets (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SECRET_KEY`) in `.env.docker` — move to AWS Secrets Manager
- `SECRET_KEY` still default — generate with `openssl rand -hex 32`
- SSL/TLS — add HTTPS with domain + AWS Certificate Manager
- PostgreSQL persistence — switch to RDS (current `db/data/` lost if EC2 terminated)

**Medium Priority**
- `APP_ENV=development` → change to `production`
- DB password `Root` is weak
- CORS origins — lock down to actual domain
- Container resource limits — no memory/CPU limits in `docker-compose.yml`
- Rate limiting — no API rate limiting

**Lower Priority**
- Centralized logging (CloudWatch)
- Error monitoring (Sentry)
- Frontend — Vite dev server not suitable for high traffic (nginx recommended)
- DB backups — no automated backup strategy
- Staging environment
