# Demo Scenario B — Escalation Path: HIGH_RISK KYC → Human Review → Resume

**Hackathon criteria demonstrated:** #5, #6, #11 (plus all of Scenario A)

---

## Overview

Same client Aarav Mehta, same two products — but this time the KYC agent returns a
**HIGH_RISK** result (PEP match, low name-match confidence, undisclosed source of funds).
This triggers the human-in-the-loop compliance review workflow:

1. KYC agent escalates → `ESCALATION_TRIGGERED` socket event
2. Evidence packet assembled and stored in `human_reviews`
3. Compliance officer reviews the evidence in the UI
4. Officer **approves** the case → workflow resumes from product onboarding
5. Full compliance audit trail confirmed

---

## Pre-flight Checklist

Same as Scenario A, plus:

```bash
# After creating the case and starting onboarding (Step 3 of Scenario A),
# activate the HIGH_RISK KYC fixture for this specific case:

curl -X POST http://localhost:8000/api/demo/cases/<CASE_ID>/kyc-scenario \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <advisor_token>" \
     -d '{"scenario": "high_risk"}'
```

Or use the **Admin Config → Demo → Set KYC Scenario** panel in the UI
(only visible when `DEMO_MODE=True`).

---

## Step-by-Step Walkthrough

### 1–3 — Same as Scenario A

Follow Scenario A Steps 1–3 to create the case and complete conversational onboarding.

---

### 4 — Trigger HIGH_RISK KYC (Criterion #11: Evidence packet)

- Set the KYC scenario to `high_risk` via the demo endpoint (see pre-flight above)
- The data collection completion fires the KYC agent
- Pre-canned `high_risk` fixture returns:
  - `name_match_confidence: 0.62` (below threshold)
  - `pep_match: true`
  - `aml_risk_factors: [politically_exposed_person, high_income, undisclosed_source_of_funds]`
  - `aml_risk_level: HIGH`

The **KYC Compliance Agent** computes a composite score that exceeds the escalation threshold
and routes to `ESCALATE`.

**Agent Trace Canvas:**

```
customer_service → orchestrator  (ADVANCE_STAGE → KYC)
orchestrator     → kyc_compliance (RUN_KYC_CHECK)
kyc_compliance   → orchestrator  (ESCALATE)
orchestrator     → collaboration  (CREATE_COLLABORATION_ROOM)
```

- `ESCALATION_TRIGGERED` socket event fires
- Case stage changes to **ESCALATED** (amber node on canvas)
- Progress bar halts at 70%

---

### 5 — Compliance officer reviews the evidence (Criterion #5: Human-in-the-loop)

- Log out of advisor account
- Log in as: `admin@glide-gate.local` | `Admin123!`
- Navigate to **Advisor Workspace** → **Compliance Review** tab (or **Reviews** in nav)
- The **Escalation Queue** shows Aarav Mehta's pending review

Click the review to open **Evidence Packet Panel**:

| Section | Content |
|---|---|
| KYC Scores | identity 0.42, AML 0.90, profile 0.60 (heatmapped by risk) |
| Escalation Reasons | PEP match, name confidence 0.62 below 0.70 threshold, undisclosed source of funds |
| Client Profile | Name, nationality, income, occupation — PII-minimised |
| Document Summary | Missing identity documents; compliance docs present |
| Compliance Audit Trail | Full decision log from KYC agent |

---

### 6 — Officer decision: Approve (Criterion #5 + #11)

- In **Review Action Bar**, click **Approve**
- Add a note: `"PEP confirmed as low-risk public official; name discrepancy acceptable."`
- Click **Confirm Approve** in the modal
- `REVIEW_DECIDED` socket event fires
- Case stage resumes to **PARALLEL_PRODUCTS**
- Both product onboarding tracks start (green nodes on Agent Trace)
- Progress bar resumes from 70% → 100%

---

### 7 — Contact Centre view (Criterion #6: AI call summary)

- Navigate to **Contact Centre**
- Find Aarav Mehta in the client table
- Open **Client Detail Panel** → **AI Call Summary Card**
- Pre-canned summary shows:
  - Stage label, key points (escalation, review outcome), recommended actions
  - Both product track progress bars

---

### 8 — Verify full compliance audit trail (Criterion #11)

```bash
curl -H "Authorization: Bearer <admin_token>" \
     "http://localhost:8000/api/reviews/<REVIEW_ID>/evidence"
```

Response includes:
- `evidence_packet` — full structured evidence
- `compliance_audit_trail` — up to 50 `COMPLIANCE_DECISION` events for the case:
  - `KYC_ESCALATED_FOR_REVIEW` (automated)
  - `REVIEW_APPROVED_BY_HUMAN` (human reviewer)

---

## Expected Outcome

| Checkpoint | Expected |
|---|---|
| KYC result | HIGH_RISK → ESCALATED |
| Human review created | Yes — evidence packet persisted |
| Review decision | APPROVED |
| Case stage after approval | PARALLEL_PRODUCTS → COMPLETE |
| Compliance audit trail entries | ≥ 2 COMPLIANCE_DECISION events |
| `is_compliance_event` rows in event_logs | ≥ 2 |
| Product tracks | Both COMPLETE after resume |

---

## Resetting for a Re-run

```bash
# Reset the demo state for a case (turn counter + KYC scenario)
curl -X POST http://localhost:8000/api/demo/cases/<CASE_ID>/reset \
     -H "Authorization: Bearer <advisor_token>"
```

Or simply create a new case and use a fresh `case_id`.
