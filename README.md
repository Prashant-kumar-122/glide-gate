# GlideGate CADF

AI-powered wealth management onboarding platform.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker Desktop | 4.x+ | Run Temporal, PostgreSQL, and the full stack |
| Python | 3.12+ | Backend runtime |
| Poetry | latest | Python dependency management |
| Node.js | 18+ | Frontend runtime |
| npm | 9+ | Frontend package management |

---

## 0. Install Docker Desktop (Windows)

Docker Desktop is required to run PostgreSQL and Temporal locally.

### Step 1 — Enable WSL 2

Open PowerShell **as Administrator** and run:

```powershell
wsl --install
```

Restart your machine when prompted. WSL 2 will be set as the default after restart.

> If you already have WSL installed but on version 1, upgrade it:
> ```powershell
> wsl --set-default-version 2
> ```

### Step 2 — Download and install Docker Desktop

1. Download from **[https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)**
2. Run the installer (`Docker Desktop Installer.exe`)
3. On the configuration screen, make sure **"Use WSL 2 instead of Hyper-V"** is checked
4. Complete the install and restart when prompted

### Step 3 — Verify

Open a new PowerShell window and run:

```powershell
docker --version
docker compose version
```

You should see something like:
```
Docker version 27.x.x
Docker Compose version v2.x.x
```

> **Troubleshooting:** If Docker Desktop shows "WSL 2 installation is incomplete", run
> `wsl --update` in PowerShell (as Administrator) then restart Docker Desktop.

---

## 1. Environment Setup

Copy the example env file and fill in your values:

```bash
cp .env.example backend/.env
```

At minimum, set:
- `DATABASE_URL` — PostgreSQL connection string
- `ANTHROPIC_API_KEY` — required for AI features
- `SECRET_KEY` — generate with `openssl rand -hex 32`

---

## 2. Temporal (workflow orchestration)

Temporal is the durable workflow engine. It **must be running** before the backend starts —
the service will not start if Temporal is unreachable.

### Option A — Docker Compose (recommended)

```bash
# Start PostgreSQL + Temporal + Temporal Web UI together
docker compose up -d postgres temporal temporal-ui
```

This starts:
- **Temporal server** on `localhost:7233` (gRPC, used by the backend worker)
- **Temporal Web UI** on `http://localhost:8080` — inspect running workflows, signal them,
  view history and activity retries

Wait ~15 seconds for Temporal to finish bootstrapping its schema in PostgreSQL, then verify:
```bash
docker compose logs temporal | grep "temporal server started"
```

### Option B — Temporal CLI (dev mode, no Docker)

**Install the CLI first (one-time):**

```powershell
# Windows — Scoop
scoop install temporal

# Windows — Chocolatey
choco install temporal

# Windows — direct download (no package manager)
# Download the latest temporal_cli_windows_amd64.zip from:
# https://github.com/temporalio/cli/releases/latest
# Extract temporal.exe and add it to your PATH
```

Then start a dev server:

```powershell
temporal server start-dev --port 7233 --ui-port 8233
```

> Dev mode uses an in-memory store — workflow history is lost on restart. Use Option A for
> any session longer than a quick smoke test.

### Temporal Web UI

| Mode | URL |
|------|-----|
| Docker Compose (Option A) | `http://localhost:8080` |
| CLI dev mode (Option B) | `http://localhost:8233` |

The worker connects to `localhost:7233` by default. To override:
```bash
TEMPORAL_HOST=my-server:7233 poetry run uvicorn app.main:socket_app --reload --port 8000
```

---

## 3. Database

### Option A — Docker Compose

```bash
docker compose up -d postgres
```

### Option B — Local PostgreSQL

Ensure PostgreSQL is running and the database exists:

```sql
CREATE DATABASE glide_gate;
```

Run migrations:

```bash
cd backend
poetry run alembic upgrade head
```

---

## 4. Seed Data

Populate the database with demo products, agents, questionnaire, a sample client (Aarav Mehta), a sample case, and a full event log:

```bash
cd backend
poetry run python ../db/seeds/seed.py
```

The seed is **idempotent** — re-running it skips rows that already exist.

**What gets seeded:**

| Step | Script | Description |
|------|--------|-------------|
| 01 | `01_products.py` | 2 products — Cash Management Account, Retirement Savings Plan |
| 02 | `02_agents.py` | 8 CADF agents (orchestrator, KYC, document, notification, etc.) |
| 03 | `03_questionnaire.py` | Onboarding questionnaire with 30 questions across 12 sections |
| 04 | `04_client_aarav_mehta.py` | Demo client Aarav Mehta with profile and address |
| 05 | `05_sample_case.py` | Sample onboarding case with two product tracks |
| 06 | `06_sample_events.py` | 23 event log entries simulating the full onboarding journey |

> **Note:** Run `alembic upgrade head` (section 2) before seeding — the seed requires the tables to exist.

---

## 5. Backend

```bash
cd backend

# Install dependencies
poetry install

# Start the dev server (hot-reload enabled)
poetry run uvicorn app.main:socket_app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- REST: `http://localhost:8000/api`
- Docs: `http://localhost:8000/docs`
- WebSocket: `ws://localhost:8000/socket.io`

---

## 6. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at `http://localhost:5173`.

The Vite dev server proxies `/api` and `/socket.io` to the backend at `http://localhost:8000` automatically — no CORS config needed during local development.

---

## Running Everything

### Full stack via Docker Compose (simplest)

```bash
docker compose up -d
```

This starts PostgreSQL, Temporal, Temporal Web UI, the backend, and the frontend all together.

| Service | URL |
|---------|-----|
| Frontend | `http://localhost:5173` |
| Backend API | `http://localhost:8000/api` |
| API Docs (Swagger) | `http://localhost:8000/docs` |
| Temporal Web UI | `http://localhost:8080` |
| Temporal gRPC | `localhost:7233` |

### Local dev (hot-reload)

Run infrastructure via Docker, services locally for faster iteration:

```bash
# Step 1 — start infrastructure
docker compose up -d postgres temporal temporal-ui

# Step 2 — backend (hot-reload)
cd backend && poetry run uvicorn app.main:socket_app --reload --port 8000

# Step 3 — frontend (hot-reload, separate terminal)
cd frontend && npm run dev
```

---

## Other Commands

### Backend

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=app

# Lint / format check
poetry run ruff check .
```

### Frontend

```bash
# Type check
npm run type-check

# Lint
npm run lint

# Run tests
npm test

# Production build
npm run build
```

### Database Migrations

```bash
cd backend

# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Roll back one migration
poetry run alembic downgrade -1
```

---

## Project Structure

```
glide-gate/
├── backend/                  # FastAPI + SQLAlchemy + python-socketio
│   ├── app/
│   │   ├── agents/           # LangGraph agent graphs (one graph.py per agent)
│   │   ├── api/              # REST routers and dependencies
│   │   ├── domain/           # DomainDefinition model + DomainDefinitionLoader
│   │   ├── mcp/              # MCP connector integrations
│   │   ├── models/           # SQLAlchemy ORM models (incl. domain_* tables)
│   │   ├── services/         # Business logic services
│   │   ├── websocket/
│   │   └── workflows/        # Temporal workflow + activity definitions
│   ├── alembic/versions/     # Database migrations (0001 → 0014+)
│   └── tests/                # unit / integration / e2e
├── frontend/                 # React 18 + Vite + Tailwind + Zustand + TanStack Query
│   └── src/
│       ├── features/         # Feature-scoped modules
│       ├── components/
│       ├── store/            # Zustand stores
│       └── hooks/
├── configs/agents/           # Agent configuration JSON files
├── db/                       # Raw SQL schema and seed files
├── docs/
│   ├── planning/             # CADF phase plan (start here)
│   ├── FRAMEWORK.md          # Developer reference
│   └── specs/                # BRD, ADRs, Technical Architecture
└── .env.example              # Environment variable reference
```
