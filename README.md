# GlideGate CADF

AI-powered wealth management onboarding platform.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Poetry | latest | Python dependency management |
| Node.js | 18+ | Frontend runtime |
| npm | 9+ | Frontend package management |
| PostgreSQL | 15+ | Database |

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

## 2. Database

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

## 3. Seed Data

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

## 4. Backend

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

## 5. Frontend

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

## Running Both Together

Open two terminals:

**Terminal 1 — Backend**
```bash
cd backend && poetry run uvicorn app.main:socket_app --reload --port 8000
```

**Terminal 2 — Frontend**
```bash
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
├── backend/          # FastAPI + SQLAlchemy + python-socketio
│   ├── app/
│   │   ├── agents/   # AI agent implementations
│   │   ├── api/      # REST routers and dependencies
│   │   ├── mcp/      # MCP connector integrations
│   │   ├── services/ # Business logic
│   │   └── websocket/
│   ├── alembic/      # Database migrations
│   └── tests/
├── frontend/         # React 18 + Vite + Tailwind + Zustand + TanStack Query
│   └── src/
│       ├── features/ # Feature-scoped modules
│       ├── components/
│       ├── store/    # Zustand stores
│       └── hooks/
├── configs/          # Agent configuration files
├── prompts/          # LLM prompt templates
├── db/               # SQL schema and seed files
└── .env.example      # Environment variable reference
```
