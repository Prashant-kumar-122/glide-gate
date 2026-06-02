# Product Type & Question Mapping — Implementation Plan

## Context

Two gaps existed in the onboarding platform:

1. **Product-linked questions:** The `DataCollectionOrchestrator` loaded one global questionnaire regardless of which products the client selected. The `onboarding_questions` table had no column to associate a question with a specific product.

2. **Product types + institutional products:** The `products` table had no `product_type` field. All products appeared identical in the API. We needed to distinguish `retail` (existing two products) from `institutional` (four new trading products from `Trading_Field_Metadata.docx`). Institutional products must be visible only to advisor-role users.

---

## Progress

| # | Task | Status |
|---|---|---|
| 1 | Alembic migration — `product_type` on products, `product_id` on questions | ✅ Done |
| 2 | ORM model updates — `Product.product_type`, `OnboardingQuestion.product_id` | ✅ Done |
| 3 | `ProductOut` schema — add `product_type` field | ✅ Done |
| 4 | `GET /cases/products` — role-based filtering (retail for all, institutional for advisors) | ✅ Done |
| 5 | `DataCollectionOrchestrator` — product-filtered question loading | ✅ Done |
| 6 | `seed_constants.py` — UUIDs for institutional products/questionnaires + retail questionnaires | ✅ Done |
| 7 | `01_products.py` — add `product_type: "retail"` to existing products | ✅ Done |
| 8 | `03_questionnaire.py` — explicit `product_id` per question; two retail questionnaires (cash + retirement) | ✅ Done |
| 9 | `09_institutional_products.py` — seed 4 institutional products | ✅ Done |
| 10 | `10_trading_questionnaires.py` — seed 4 questionnaires with ~171 questions | ✅ Done |
| 11 | `seed.py` — register seeds 09 and 10 | ✅ Done |

---

## Design Decisions

### product_id on onboarding_questions (not on questionnaires)
Each `OnboardingQuestion` has a `product_id` FK → `products.id`:
- Every question is explicitly mapped to exactly one product — no `NULL` fallback.
- Retail products each have their own questionnaire with 49 questions mapped via `product_id`.
- Institutional products each have their own questionnaire with their questions mapped via `product_id`.

### Retail question duplication (revised)
The original design used `product_id = NULL` as a "universal retail" marker. This was replaced with explicit duplication:
- `CASH_QUESTIONNAIRE_ID` → 49 questions each with `product_id = CASH_PRODUCT_ID`
- `RETIREMENT_QUESTIONNAIRE_ID` → same 49 questions each with `product_id = RETIREMENT_PRODUCT_ID`

This makes all questions uniformly scoped — no special-casing needed anywhere.

### Simplified DCO filter
Because every question now has an explicit `product_id`, the DCO filter is uniform for all product types:
```python
OnboardingQuestion.product_id.in_(all_product_ids)
```
The previous two-branch logic (retail → `IS NULL`, institutional → `IN (...)`) is gone.

### Per-field questionnaire tracking
Since a case may involve multiple questionnaires (e.g. cash + retirement both selected), `_questionnaire_id_map` (case-level) was replaced by `_question_questionnaire_map` (field-level). The accessor `get_question_questionnaire_id(case_id, field_id)` is used when saving `OnboardingAnswer` rows.

### Institutional product visibility
`GET /cases/products` checks `current_user["role"]`. Non-advisors receive only `product_type = "retail"` products. Advisors receive all active products.

---

## Files Changed

| File | Change |
|---|---|
| `backend/alembic/versions/0009_product_type_and_question.py` | New migration (revision ID ≤ 32 chars) |
| `backend/app/models/cases.py` | `Product.product_type` field + check constraint |
| `backend/app/models/questionnaire.py` | `OnboardingQuestion.product_id` nullable FK |
| `backend/app/api/routers/cases.py` | `ProductOut.product_type`, role-filtered endpoint |
| `backend/app/agents/customer_service/data_collection_orchestrator.py` | Simplified `product_id IN (...)` filter, new accessor |
| `backend/app/agents/customer_service/customer_service_agent.py` | Updated `load_questions_from_db` call sites |
| `backend/app/services/conversation/conversation_coordinator.py` | Updated call sites + `get_question_questionnaire_id` |
| `db/seeds/seed_constants.py` | `CASH_QUESTIONNAIRE_ID`, `RETIREMENT_QUESTIONNAIRE_ID`, 4 institutional UUIDs |
| `db/seeds/01_products.py` | `product_type: "retail"` on existing products |
| `db/seeds/03_questionnaire.py` | Two retail questionnaires; explicit `product_id` on all 49 questions each |
| `db/seeds/09_institutional_products.py` | New — 4 institutional products |
| `db/seeds/10_trading_questionnaires.py` | New — 4 questionnaires, ~171 questions |
| `db/seeds/seed.py` | Seeds 09 + 10 registered |

---

## Verification Steps

1. **Run migration:** `cd backend && poetry run alembic upgrade head`
2. **Run seeds:** `cd backend && python ../db/seeds/seed.py`
3. **Role check:** `GET /cases/products` as non-advisor → 2 retail products. As advisor → 6 products.
4. **DCO filter check:** Case with `selected_products = ["prime_brokerage"]` → only PB questions loaded. With `["cash_account"]` → cash-specific 49 questions loaded. With both retail products → 98 questions (49 × 2).
5. **Seed idempotency:** Run seed twice — all rows `[skip]` on second run (except 03 which purges and re-seeds by design).
