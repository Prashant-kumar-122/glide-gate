# Demo Scenario A — Happy Path: Aarav Mehta, Two Products, No Escalation

**Hackathon criteria demonstrated:** #1, #2, #3, #4, #7, #8, #9, #10

---

## Overview

Aarav Mehta is a prospective GlideGate client who wants to open both a **Cash Account** and a
**Retirement Account**. His profile is straightforward — no PEP flags, no sanctions matches,
low AML risk — so the entire onboarding completes automatically without any human review.

**Expected end-to-end duration (demo mode):** ≈ 4–6 minutes

---

## Pre-flight Checklist

```bash
# 1. Backend
cd backend
cp ../.env.example .env
# Set: DEMO_MODE=True  (disables live LLM calls; uses pre-canned responses)
# Set: ANTHROPIC_API_KEY=  (can be empty in demo mode)
poetry run uvicorn app.main:app --reload --port 8000

# 2. Frontend
cd frontend
npm run dev
# → http://localhost:5173

# 3. Seed the database (first run only)
cd backend
poetry run alembic upgrade head
poetry run python db/seeds/seed.py
```

---

## Step-by-Step Walkthrough

### 1 — Log in as Demo Advisor (Criterion #1: Role-based access)

- Open [http://localhost:5173/login](http://localhost:5173/login)
- Email: `advisor@glide-gate.local` | Password: `Advisor123!`
- The navbar shows **Advisor Workspace**, **Contact Centre**, and **Agent Trace** (advisor role)

---

### 2 — Create a new onboarding case (Criterion #3: Parallel product tracks)

- In the **Advisor Workspace**, click **New Case**
- Select client **Aarav Mehta**
- Tick **Cash Account** and **Retirement Account**
- Click **Start Onboarding**
- The left rail shows Aarav's progress bar at 0%

---

### 3 — Client completes conversational onboarding (Criterion #4: < 5 min intake)

- In a new browser tab, log in as the client:  
  Email: `aarav.mehta@demo.glide-gate.local` | Password: `Client123!`
- Open the **Client Portal** — the chat greeting fires automatically
- Answer each question as prompted (pre-scripted responses shown in demo notes below)
- After ~19 exchanges the assistant confirms all data is collected
- The progress bar advances from 0 → 60% as answers are recorded

**Sample client inputs for demo:**

| Prompt | Input |
|---|---|
| Full name | Aarav Mehta |
| Date of birth | 15/03/1985 |
| Nationality | Indian |
| Email | aarav.mehta@example.com |
| Phone | +44 7700 900123 |
| Occupation | Software Engineer |
| Annual income | £95,000 |
| Source of funds | Employment income |
| Address | 12 Baker Street, London, W1U 6TN |
| ID type | Passport |
| Document number | P1234567 |
| Products | Cash Account, Retirement Account |
| Investment experience | Moderate |
| Risk tolerance | Moderate |
| Investment horizon | Long |
| Tax residency | United Kingdom |
| US person | No |
| Regulatory question | No |

---

### 4 — Identity Verification & KYC (Criterion #2: AI agent decision)

- After data collection the **Orchestrator** automatically triggers the **KYC Agent**
- Progress bar advances to 70% (KYC stage)
- In demo mode the KYC result is **PASSED** (pre-canned fixture: `kyc_high_risk.json → passing`)
- The **Agent Trace Canvas** shows:
  - `customer_service` → `orchestrator` (ADVANCE_STAGE)
  - `orchestrator` → `kyc_compliance` (RUN_KYC_CHECK)
  - `kyc_compliance` → `orchestrator` (ADVANCE_STAGE → PARALLEL_PRODUCTS)

---

### 5 — Parallel product onboarding (Criterion #3: Two independent tracks)

- The **Orchestrator** fans out to two `product_onboarding` agents simultaneously
- Advisor Workspace shows two independent progress bars (Cash Account | Retirement Account)
- Contact Centre dashboard also shows both tracks
- Both tracks complete and emit `PRODUCT_TRACK_UPDATE` socket events

---

### 6 — Document upload & AI validation (Criteria #8, #9)

Back in the **Advisor Workspace**:

- Select Aarav Mehta → **Identity** category → drag-drop a sample PDF
- The upload badge increments immediately (socket event)
- Click **Run AI Check** on the uploaded document
  - Pre-canned findings show: 5× pass, 1× warn (photo slightly blurry)
  - `AIValidationPanel` renders colour-coded pass/warn/fail cards
- Re-upload a revised document (triggers version diff automatically)
  - `VersionDiffPanel` shows similarity ratio, added/removed sections

---

### 7 — Agent Trace Canvas (Criterion #10: Live animated graph)

- Navigate to **Agent Trace** in the nav
- Select Aarav Mehta's case from the dropdown
- Observe: animated blue edges during in-flight A2A messages (2 s visible)
- Node colours: grey (idle) → blue (active) → green (complete)
- Message Log panel on the right lists every A2A packet with from/to/status/duration

---

### 8 — Verify audit trail

```bash
# All 100% of decisions logged
curl -H "Authorization: Bearer <advisor_token>" \
     "http://localhost:8000/api/audit/logs?case_id=<case_id>"
```

Or open **Admin Config → Audit** in the UI.

---

## Expected Outcome

| Checkpoint | Expected |
|---|---|
| Case stage after conversation | PARALLEL_PRODUCTS (or REVIEW) |
| KYC result | PASSED |
| Product tracks | Both COMPLETE |
| Document validation | pass/warn mix (no fail) |
| Escalation | None |
| Human review queue | Empty |
| Audit events | ≥ 15 events for the case |
