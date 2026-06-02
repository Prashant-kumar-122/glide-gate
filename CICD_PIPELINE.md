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
- **Event:** Any push to this branch
- **Pipeline source:** `$CI_PIPELINE_SOURCE == "push"`

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

## Pending TODOs

1. ✅ ~~**Move SSH key to GitLab CI/CD Variable**~~ — done, stored as `EC2_SSH_KEY` File type variable
2. **Fix Alembic migration** — `0005_trusted_contact_questions.py` has FK seed issue; re-enable in `docker-compose.yml` after fix
3. **Attach EBS volume** — for persistent PostgreSQL storage in production
4. **Upgrade Node.js to 20** — `eslint-visitor-keys` requires Node 20+; update EC2 and `frontend/Dockerfile`
