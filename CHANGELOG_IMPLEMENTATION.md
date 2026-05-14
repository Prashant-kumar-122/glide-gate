# GlideGate CADF — Implementation Changelog

> **Execution model:** Read this file → find the first step that is not `[DONE]` → execute it → mark it `[DONE]` → commit.
> Every step is atomic. A step is DONE only when **all** listed artifacts exist on disk.

---

## Phase 1 — Foundation & Architecture

### [DONE] STEP-01 — Repository Scaffold & Project Structure
**Date:** 2026-05-11 | **BRD:** Section 9.1, Section 13.3

**Artifacts produced:**
- `backend/pyproject.toml` ✓
- `backend/alembic.ini` ✓
- `backend/alembic/env.py` ✓
- `frontend/package.json` ✓
- `frontend/vite.config.ts` ✓
- `frontend/tailwind.config.ts` ✓
- `frontend/tsconfig.json` + `tsconfig.app.json` + `tsconfig.node.json` ✓
- `frontend/postcss.config.js` ✓
- `frontend/index.html` ✓
- `.env.example` ✓
- `.gitignore` ✓
- `CHANGELOG_IMPLEMENTATION.md` ✓
- All 54 directories from plan folder structure ✓
- 41 Python `__init__.py` package stubs ✓
- `.gitkeep` in 29 empty leaf directories ✓

---

### [DONE] STEP-02 — Backend Setup (FastAPI + SQLAlchemy + python-socketio)
**Date:** 2026-05-11 | **BRD:** Section 9.2, Section 10.2 NFRs | **Depends:** STEP-01

**Artifacts produced:**
- `backend/app/main.py` ✓ — FastAPI app + socketio ASGIApp mount at `/ws`
- `backend/app/config.py` ✓ — Pydantic `Settings` (all env vars, CORS parser, properties)
- `backend/app/database.py` ✓ — async SQLAlchemy engine, `AsyncSessionLocal`, `Base`, `get_db`
- `backend/app/api/routers/health.py` ✓ — GET /api/health (DB ping, status, version)
- `backend/app/models/__init__.py` ✓ — exports `Base` for Alembic autodiscovery

---

### [DONE] STEP-03 — Frontend Setup (React 18 + Vite + Tailwind + Zustand + TanStack Query)
**Date:** 2026-05-11 | **BRD:** Section 9.1, Section 5.1 | **Depends:** STEP-01

**Artifacts produced:**
- `frontend/src/index.css` ✓ — Tailwind base/components/utilities
- `frontend/src/main.tsx` ✓ — React root: QueryClientProvider + BrowserRouter + StrictMode
- `frontend/src/App.tsx` ✓ — NavBar + Routes to 5 pages (/, /client, /contact-centre, /agent-trace, /admin)
- `frontend/src/routes/AdvisorWorkspace.tsx` ✓ — placeholder
- `frontend/src/routes/ClientPortal.tsx` ✓ — placeholder
- `frontend/src/routes/ContactCentre.tsx` ✓ — placeholder
- `frontend/src/routes/AgentTrace.tsx` ✓ — placeholder
- `frontend/src/routes/AdminConfig.tsx` ✓ — placeholder
- `frontend/src/store/index.ts` ✓ — re-exports all 4 store hooks
- `frontend/src/store/workspaceStore.ts` ✓ — Zustand (selectedClient, drawer, badges, socket)
- `frontend/src/store/chatStore.ts` ✓ — Zustand (messages, typingIndicator, sessionId)
- `frontend/src/store/ccStore.ts` ✓ — Zustand (selectedClient, filterText, socketStatus)
- `frontend/src/store/traceStore.ts` ✓ — Zustand (nodeStates, edgeQueue, messageLog, selectedAgent)
- `npm install` completed (344 packages) ✓
- `tsc --noEmit` passes with zero errors ✓

---

## Phase 2 — Agent Design

### [DONE] STEP-04 — Orchestrator Agent + A2A Framework
**Date:** 2026-05-12 | **BRD:** Section 6.1, Section 6.2, FR-03 | **Depends:** STEP-02

**Artifacts produced:**
- `backend/app/agents/base/a2a_types.py` ✓ — AgentID, TaskType, OnboardingStage, TaskPacket, TaskResponse, OnboardingState, ProductTrackState
- `backend/app/agents/base/base_agent.py` ✓ — abstract BaseAgent with timed_process, attach_bus, send_task
- `backend/app/agents/base/agent_event_bus.py` ✓ — asyncio.Queue-based A2A bus, register/subscribe/publish/dispatch_loop, Redis-ready stub
- `backend/app/agents/base/__init__.py` ✓ — re-exports all public types
- `backend/app/agents/orchestrator/workflow_state_machine.py` ✓ — WorkflowStateMachine FSM (INTAKE → KYC → PARALLEL_PRODUCTS → REVIEW → COMPLETE | ESCALATED) with InvalidTransitionError, restore(), on_transition callbacks
- `backend/app/agents/orchestrator/orchestrator_agent.py` ✓ — OrchestratorAgent: START_ONBOARDING, RESUME_ONBOARDING, ADVANCE_STAGE, ESCALATE, HEALTH_CHECK handlers; _route_to_stage per-product fan-out
- `backend/app/agents/orchestrator/__init__.py` ✓ — re-exports OrchestratorAgent, WorkflowStateMachine, InvalidTransitionError
- `configs/agents/orchestrator.config.json` ✓ — FSM transition table, task routing map, thresholds

---

### [DONE] STEP-05 — Customer Service Agent
**Date:** 2026-05-12 | **BRD:** Section 6.1, Section 8.1 stages 1–2, FR-02, FR-12 | **Depends:** STEP-04

**Artifacts produced:**
- `backend/app/agents/customer_service/conversation_memory.py` ✓ — per-case rolling Message list, `to_anthropic()` formatter
- `backend/app/agents/customer_service/intent_classifier.py` ✓ — rule-based IntentClassifier (PROVIDE_INFO / ASK_QUESTION / CONFIRM / DECLINE / REQUEST_HELP)
- `backend/app/agents/customer_service/data_collection_orchestrator.py` ✓ — 26-field questionnaire across 8 sections, show_if evaluator, typed value extractor, CollectionStatus
- `backend/app/agents/customer_service/customer_service_agent.py` ✓ — CustomerServiceAgent: COLLECT_CLIENT_DATA + CONTINUE_CONVERSATION handlers, Anthropic SDK integration with template fallback, signals ADVANCE_STAGE → KYC on completion
- `backend/app/agents/customer_service/__init__.py` ✓ — re-exports CustomerServiceAgent
- `configs/agents/customer_service.config.json` ✓ — LLM params, section order, show_if rule reference

---

### [DONE] STEP-06 — KYC & Compliance Agent
**Date:** 2026-05-12 | **BRD:** Section 6.1, FR-04, FR-13, FR-14, FR-15 | **Depends:** STEP-04, STEP-05

**Artifacts produced:**
- `backend/app/agents/kyc_compliance/risk_scorer.py` ✓ — `RiskScorer` (identity×0.4 + AML×0.4 + profile×0.2), `RiskScore` Pydantic model, 4 risk bands (LOW/MEDIUM/HIGH/VERY_HIGH)
- `backend/app/agents/kyc_compliance/evidence_packet_builder.py` ✓ — `EvidencePacketBuilder`, `EvidencePacket`, `EvidenceItem` with PII-minimised profile summary and risk-relevant flagging
- `backend/app/agents/kyc_compliance/checkpoint_rule_engine.py` ✓ — `CheckpointRuleEngine` with 5 default rules across 4 dimensions (product_type, risk_level, account_value_band, jurisdiction), extensible via `add_rule`/`remove_rule`
- `backend/app/agents/kyc_compliance/kyc_compliance_agent.py` ✓ — `KYCComplianceAgent`: RUN_KYC_CHECK + VERIFY_IDENTITY handlers, simulated MCP identity verification (deterministic seed for demo), signals ESCALATE or ADVANCE_STAGE to orchestrator
- `backend/app/agents/kyc_compliance/__init__.py` ✓ — re-exports all public types
- `configs/agents/kyc_compliance.config.json` ✓ — weights, band thresholds, simulation params, default rule catalogue

---

### [DONE] STEP-07 — Document Intelligence Agent
**Date:** 2026-05-12 | **BRD:** Section 6.1, FR-06, FR-08, FR-09, Section 5.1.10–5.1.11 | **Depends:** STEP-04, STEP-05

**Artifacts produced:**
- `backend/app/agents/document_intelligence/document_classifier.py` ✓ — Rule-based `DocumentClassifier` (21 document types across 6 categories), `ClassificationResult` Pydantic model, confidence scoring
- `backend/app/agents/document_intelligence/ocr_extractor.py` ✓ — Simulated `OcrExtractor` with category-keyed field templates, `OcrResult` / `OcrField` Pydantic models, 100–600ms randomised latency
- `backend/app/agents/document_intelligence/ai_completeness_validator.py` ✓ — `AICompletenessValidator`: Anthropic SDK call with editable prompts → `FindingResult[]` (pass/warn/fail); heuristic fallback for no-API runs; `ValidationResult` model
- `backend/app/agents/document_intelligence/version_diff_detector.py` ✓ — `VersionDiffDetector`: difflib-based `DiffResult` with added/modified/removed/unchanged sections, similarity ratio, human-readable summary; supports text or field-dict inputs
- `backend/app/agents/document_intelligence/document_intelligence_agent.py` ✓ — `DocumentIntelligenceAgent`: CLASSIFY_DOCUMENT, EXTRACT_OCR, VALIDATE_DOCUMENT, COMPUTE_DIFF handlers
- `backend/app/agents/document_intelligence/__init__.py` ✓ — re-exports all public types
- `configs/agents/document_intelligence.config.json` ✓ — classification thresholds, OCR params, validation LLM settings, diff thresholds, all 6 default validation prompts

### [DONE] STEP-08 — Product Onboarding, Collaboration, Contact Centre & Notification Agents
**Date:** 2026-05-12 | **BRD:** Section 6.1, FR-05, Section 7.3–7.4, Section 8.1 stages 5–8 | **Depends:** STEP-04–07

**Artifacts produced:**
- `backend/app/agents/product_onboarding/suitability_assessor.py` ✓ — `SuitabilityAssessor` (weighted 40/30/20/10 scoring), `SuitabilityOutcome` Pydantic model, risk/income/age/horizon checks
- `backend/app/agents/product_onboarding/product_onboarding_agent.py` ✓ — `ProductOnboardingAgent`: ONBOARD_PRODUCT + ASSESS_SUITABILITY handlers; parameterised by product_code; per-product step sequences with simulated latency; signals ADVANCE_STAGE + SEND_NOTIFICATION on completion
- `backend/app/agents/product_onboarding/__init__.py` ✓ — re-exports public types
- `backend/app/agents/collaboration/collaboration_agent.py` ✓ — `CollaborationAgent`: CREATE_COLLABORATION_ROOM + ADD_COMMENT handlers; in-memory `CollaborationRoom` (DB-backed in STEP-12+); visibility levels, participant roles
- `backend/app/agents/collaboration/__init__.py` ✓ — re-exports CollaborationAgent
- `backend/app/agents/contact_centre/status_summariser.py` ✓ — `StatusSummariser`: rule-based `CallSummary` generation (stage/KYC/documents/products/escalation); no LLM dependency
- `backend/app/agents/contact_centre/contact_centre_agent.py` ✓ — `ContactCentreAgent`: SUMMARISE_CALL + GET_CLIENT_STATUS handlers; AI-enhanced summaries via Anthropic SDK with heuristic fallback
- `backend/app/agents/contact_centre/__init__.py` ✓ — re-exports all public types
- `backend/app/agents/notification/notification_templates.py` ✓ — 11 `NotificationTemplate` instances across email/in-app channels; `Template.safe_substitute` rendering; `get_template()` / `list_templates()` helpers
- `backend/app/agents/notification/notification_agent.py` ✓ — `NotificationAgent`: SEND_NOTIFICATION + SEND_ESCALATION_ALERT handlers; simulated dispatch (50–300ms latency); `is_simulated=True` in all records; full dispatch log
- `backend/app/agents/notification/__init__.py` ✓ — re-exports public types
- `configs/agents/product_onboarding.config.json` ✓ — product steps, suitability weights/thresholds, step latency ranges
- `configs/agents/collaboration.config.json` ✓ — visibility levels, participant roles, comment config
- `configs/agents/contact_centre.config.json` ✓ — LLM params, stage/KYC label maps
- `configs/agents/notification.config.json` ✓ — 11 template names, channel routing, dispatch config

---

## Phase 2.5 — Database Design & Schema

### [DONE] STEP-09 — Core Tables DDL (10 Tables)
**Date:** 2026-05-13 | **BRD:** Section 15.2.1 | **Depends:** STEP-01

**Artifacts produced:**
- `db/schema/001_clients.sql` ✓ — clients, client_profiles, client_addresses (3 tables)
- `db/schema/002_onboarding_cases.sql` ✓ — onboarding_cases, products, case_products, case_product_steps (4 tables)
- `db/schema/003_documents.sql` ✓ — documents with 6-state lifecycle ENUM (1 table)
- `db/schema/004_kyc_human_reviews.sql` ✓ — kyc_checks, human_reviews (2 tables)

All tables: UUID PKs, JSONB flexible columns, FK constraints with named keys, CHECK constraints on all enums, lookup indexes on status/created_at columns.

---

### [DONE] STEP-10 — Agent/Event Tables DDL (4 Tables)
**Date:** 2026-05-13 | **BRD:** Section 15.2.2, FR-03, FR-14 | **Depends:** STEP-09

**Artifacts produced:**
- `db/schema/005_agents.sql` ✓ — agents (1 table)
- `db/schema/006_agent_tasks.sql` ✓ — agent_tasks (1 table; persists TaskPacket + response)
- `db/schema/007_event_logs.sql` ✓ — event_logs (1 table; append-only, no updated_at)
- `db/schema/008_mcp_tool_calls.sql` ✓ — mcp_tool_calls with `is_simulated BOOLEAN DEFAULT TRUE` (1 table)

---

### [DONE] STEP-11 — Communication/Summary & Questionnaire Tables DDL (11 Tables)
**Date:** 2026-05-13 | **BRD:** Section 15.2.3–15.2.4, Section 15.3 | **Depends:** STEP-09, STEP-10

**Artifacts produced:**
- `db/schema/009_communications.sql` ✓ — notifications, case_summaries, collaboration_rooms, collaboration_participants, collaboration_comments, conversation_messages (6 tables)
- `db/schema/010_questionnaire.sql` ✓ — onboarding_questionnaires, onboarding_questions, onboarding_question_rules, onboarding_answers, onboarding_question_sessions (5 tables)

Total: 10 + 4 + 11 = **25 tables** across Phase 2.5.

---

### [DONE] STEP-12 — SQLAlchemy Models, Alembic Migration & Seed Data
**Date:** 2026-05-13 | **BRD:** Section 15.2.5, Section 15.3 | **Depends:** STEP-09–11

**Artifacts produced:**
- `backend/app/models/clients.py` ✓ — Client, ClientProfile, ClientAddress ORM models
- `backend/app/models/cases.py` ✓ — OnboardingCase, Product, CaseProduct, CaseProductStep
- `backend/app/models/documents.py` ✓ — Document (self-referential parent_doc_id for versioning)
- `backend/app/models/kyc_reviews.py` ✓ — KYCCheck, HumanReview
- `backend/app/models/agents.py` ✓ — Agent, AgentTask, EventLog, MCPToolCall
- `backend/app/models/communications.py` ✓ — Notification, CaseSummary, CollaborationRoom, CollaborationParticipant, CollaborationComment, ConversationMessage
- `backend/app/models/questionnaire.py` ✓ — OnboardingQuestionnaire, OnboardingQuestion, OnboardingQuestionRule, OnboardingAnswer, OnboardingQuestionSession
- `backend/app/models/__init__.py` ✓ — imports all 25 models for Alembic autodiscovery
- `backend/alembic/versions/0001_initial.py` ✓ — authoritative migration: 25 tables, all FKs, indexes, CHECK constraints
- `db/seeds/seed_constants.py` ✓ — shared UUID constants
- `db/seeds/01_products.py` ✓ — 2 products (cash_account, retirement_account)
- `db/seeds/02_agents.py` ✓ — 8 agents matching AgentID enum
- `db/seeds/03_questionnaire.py` ✓ — 30 questions across 12 sections with 3 conditional show_if rules
- `db/seeds/04_client_aarav_mehta.py` ✓ — client, profile, address
- `db/seeds/05_sample_case.py` ✓ — 2-product onboarding case, 12 product steps, questionnaire session
- `db/seeds/06_sample_events.py` ✓ — 23 event log entries covering full happy-path journey
- `db/seeds/seed.py` ✓ — master runner (importlib-based, digit-prefix safe)

---

## Phase 3 — Backend & Integration

### [DONE] STEP-13 — Context Store Service & Shared OnboardingState
**Date:** 2026-05-13 | **BRD:** FR-12, Paused Journey Resumption | **Depends:** STEP-04, STEP-12

**Artifacts produced:**
- `backend/app/services/context_store/onboarding_state_schema.py` ✓ — `ContextSnapshot` (point-in-time immutable copy), `OptimisticLockError`; re-exports `OnboardingState` from a2a_types
- `backend/app/services/context_store/state_repository.py` ✓ — `StateRepository` with async `load()`, `persist()`, `exists()` targeting `onboarding_cases.shared_context` JSONB; also updates `current_stage` on every persist
- `backend/app/services/context_store/context_store_service.py` ✓ — `ContextStoreService` singleton (`context_store`): in-memory dict cache + per-case `asyncio.Lock`; `initialise()`, `get()` (cache-then-DB), `update()` with optimistic locking (version check + increment + persist), `lock()` async context manager, `snapshot()`, `restore()` (bumps version), `evict()`
- `backend/app/services/context_store/__init__.py` ✓ — re-exports all public symbols

### [DONE] STEP-14 — REST API Layer (FastAPI Routers)
**Date:** 2026-05-13 | **BRD:** Section 9.1, FR-01, FR-05, FR-07 | **Depends:** STEP-02, STEP-12, STEP-13

**Artifacts produced:**
- `backend/app/api/dependencies/auth.py` ✓ — JWT verify dependency (`get_current_user`); demo-mode passthrough returns DEMO_USER
- `backend/app/api/dependencies/role_guard.py` ✓ — `require_role(*roles)` dependency factory; 403 on role mismatch
- `backend/app/api/error_handlers.py` ✓ — `NotFoundError`, `ConflictError`, `UnprocessableError`, `ServiceUnavailableError`; `register_error_handlers(app)` wired into main.py
- `backend/app/api/routers/clients.py` ✓ — POST /clients, GET /clients/{id}, PATCH /clients/{id}
- `backend/app/api/routers/cases.py` ✓ — POST /cases (initiate), GET /cases/{id}, GET /cases/{id}/summary, POST /cases/{id}/resume (202 stub for STEP-17)
- `backend/app/api/routers/documents.py` ✓ — POST /cases/{id}/documents (UploadFile), GET /cases/{id}/documents, GET /documents/{id}, POST /documents/{id}/validate (202 stub for STEP-28), GET /documents/{id}/diff
- `backend/app/api/routers/conversations.py` ✓ — POST /cases/{id}/message (SSE StreamingResponse placeholder for STEP-27), GET /cases/{id}/messages
- `backend/app/api/routers/reviews.py` ✓ — GET /reviews, GET /reviews/{id}, GET /reviews/{id}/evidence, POST /reviews/{id}/decide
- `backend/app/api/routers/agents.py` ✓ — GET /agents, GET /agents/{agent_id}, GET /agents/trace/{case_id}
- `backend/app/api/routers/audit.py` ✓ — GET /audit/logs (paginated, filtered), GET /audit/logs.csv (StreamingResponse CSV export)
- `backend/app/api/routers/admin/llm_config.py` ✓ — GET/PUT/DELETE /admin/llm-config (in-memory overrides; DB-backed in STEP-24)
- `backend/app/api/routers/admin/validation_prompts.py` ✓ — GET/PUT/DELETE /admin/validation-prompts/{category} (in-memory; DB-backed in STEP-28)
- `backend/app/main.py` ✓ — updated to register all 10 routers + error handlers (35 routes total)
- **Bug fix (STEP-12 carry-over):** renamed `metadata` → `extra_metadata` (with `mapped_column("metadata", ...)`) across all 14 ORM models and all seed files to resolve SQLAlchemy 2.0 reserved-name conflict

**Notes:** Orchestration stubs (resume, validate, SSE) return 202 Accepted — full wiring happens in STEP-17 (AgentOrchestrationService) and STEP-27/STEP-28.

### [DONE] STEP-15 — WebSocket Layer (python-socketio)
**Date:** 2026-05-13 | **BRD:** FR-11, Section 5.1.9, FR-13 | **Depends:** STEP-02, STEP-04, STEP-13

**Artifacts produced:**
- `backend/app/websocket/socket_events.py` ✓ — `SocketEvent` StrEnum: 12 typed event constants (AGENT_MESSAGE, TASK_ASSIGNED, TASK_COMPLETE, DOCUMENT_STATUS_CHANGED, DOCUMENT_UPLOADED, KYC_RESULT, ESCALATION_TRIGGERED, REVIEW_DECIDED, PRODUCT_TRACK_UPDATE, NOTIFICATION_SENT, CASE_STAGE_CHANGED, PROGRESS_UPDATE) + JOIN/LEAVE_CASE_ROOM + ERROR
- `backend/app/websocket/socket_server.py` ✓ — `sio` singleton AsyncServer; `connect`/`disconnect`/`join_case_room`/`leave_case_room` event handlers; `emit_to_case(case_id, event, data)` targeting `case:{id}` rooms; `room_size()` helper; `_case_rooms` dict tracks per-case sids
- `backend/app/websocket/socket_emitter.py` ✓ — `SocketEmitter` class with typed async helper per event; module-level `socket_emitter` singleton for agents/services to import
- `backend/app/websocket/__init__.py` ✓ — re-exports `SocketEvent`, `sio`, `emit_to_case`, `room_size`, `socket_emitter`
- `backend/app/main.py` ✓ — updated to import `sio` from `socket_server` (removed inline AsyncServer construction)

### [DONE] STEP-16 — MCP Connectors (Simulated)
**Date:** 2026-05-13 | **BRD:** Section 5.3, Section 6.3, FR-04, FR-06, Section 13.1 | **Depends:** STEP-10, STEP-12, STEP-13

**Artifacts produced:**
- `backend/app/mcp/mcp_connector.py` ✓ — `MCPConnector` abstract base, `MCPToolDefinition` Pydantic model, `MCPRegistry` (register/get/list/invoke), module-level `mcp_registry` singleton
- `backend/app/mcp/mcp_logger.py` ✓ — `MCPLogger.log()` persists every invocation to `mcp_tool_calls` with `is_simulated=True`; graceful failure so logging never breaks callers
- `backend/app/mcp/connectors/identity_verification/simulator.py` ✓ — deterministic-seed simulators for `verify_identity` (confidence + flags), `check_sanctions` (sanctions-fragment matching, UN/OFAC/EU/HMT lists), `score_aml_risk` (4 weighted factors: PEP 0.35, country 0.30, SoW 0.20, occupation 0.15 → LOW/MEDIUM/HIGH/VERY_HIGH)
- `backend/app/mcp/connectors/identity_verification/connector.py` ✓ — `IdentityVerificationConnector`: 100–800ms random latency, MCPLogger wired, `identity_verification_connector` singleton
- `backend/app/mcp/connectors/document_management/simulator.py` ✓ — in-memory `_DOCUMENT_STORE`; simulators for `upload_document` (UUID + S3-style URL + SHA-256 checksum), `retrieve_document`, `get_document_status`, `extract_ocr` (6-category field templates + bounding boxes)
- `backend/app/mcp/connectors/document_management/connector.py` ✓ — `DocumentManagementConnector`: 100–800ms random latency, MCPLogger wired, `document_management_connector` singleton
- `backend/app/mcp/connectors/identity_verification/__init__.py` ✓ — re-exports connector + simulator functions
- `backend/app/mcp/connectors/document_management/__init__.py` ✓ — re-exports connector + simulator functions
- `backend/app/mcp/connectors/__init__.py` ✓ — re-exports both connector singletons
- `backend/app/mcp/__init__.py` ✓ — imports and registers both connectors into `mcp_registry` at import time; 7 tools across 2 connectors confirmed

### [DONE] STEP-17 — Agent Orchestration Service (Wire All 8 Agents)
**Date:** 2026-05-13 | **BRD:** Section 8.1, FR-03, FR-12 | **Depends:** STEP-04–08, STEP-13, STEP-15, STEP-16

**Artifacts produced:**
- `backend/app/services/orchestration/agent_registry.py` ✓ — `AgentRegistry` dict-backed registry; `register`, `get`, `all`, `agent_ids`
- `backend/app/services/orchestration/parallel_product_launcher.py` ✓ — `ParallelProductLauncher`: custom asyncio dispatch loop that batches ONBOARD_PRODUCT tasks from the bus queue, groups by case_id, and runs one `ProductOnboardingAgent` per product via `asyncio.gather`; `launch_for_case` for direct invocation; emits `PROGRESS_UPDATE` socket events on start and completion
- `backend/app/services/orchestration/agent_orchestration_service.py` ✓ — `AgentOrchestrationService` singleton (`orchestration_service`): boots all 8 agents, registers 7 on the bus dispatch loop + 1 placeholder for the ProductOnboarding queue; `start()`/`stop()` lifecycle; `start_onboarding(case_id, client_id, selected_products)` — initialises ContextStore + emits socket event + publishes START_ONBOARDING; `resume_onboarding(case_id)` — loads state + publishes RESUME_ONBOARDING; `active_cases` and `registry` introspection properties
- `backend/app/services/orchestration/__init__.py` ✓ — re-exports all public symbols
- `backend/app/main.py` ✓ — updated: `on_startup` calls `orchestration_service.start()`; `on_shutdown` calls `orchestration_service.stop()`
- `backend/app/api/routers/cases.py` ✓ — `POST /cases` fires `asyncio.create_task(orchestration_service.start_onboarding(...))` after DB commit; `POST /cases/{id}/resume` fires `asyncio.create_task(orchestration_service.resume_onboarding(...))` — both return immediately (202 pattern)

### [DONE] STEP-18 — Document Upload & Storage Service
**Date:** 2026-05-13 | **BRD:** FR-06, FR-07, FR-09, Section 5.1.7–5.1.8 | **Depends:** STEP-09, STEP-13, STEP-15, STEP-16

**Artifacts produced:**
- `backend/app/services/document/document_storage_adapter.py` ✓ — `DocumentStorageAdapter` ABC; `LocalStorageAdapter` (stores to `DOCUMENT_STORAGE_PATH/{case_id}/{doc_id}/{filename}`, SHA-256 checksum); `S3StorageAdapter` stub (raises `NotImplementedError`); `StorageAdapterFactory.get()` picks backend from settings; module-level `storage_adapter` singleton
- `backend/app/services/document/document_version_manager.py` ✓ — `DocumentVersionManager`: `next_version(parent_doc_id, db)` returns 1 for new uploads or `parent.version + 1` for resubmissions; `get_version_chain(doc_id, db)` walks `parent_doc_id` chain to root then returns all versions ordered by version number; module-level `document_version_manager` singleton
- `backend/app/services/document/document_status_service.py` ✓ — `DocumentStatusService`: enforces `_ALLOWED_TRANSITIONS` state machine (6-state lifecycle); `update_status(doc_id, new_status, db)` validates transition, persists, emits `DOCUMENT_STATUS_CHANGED` socket event with badge count; `get_upload_badge_count(case_id, db)` counts RECEIVED + UNDER_REVIEW docs; module-level `document_status_service` singleton
- `backend/app/services/document/document_upload_service.py` ✓ — `DocumentUploadService.upload()`: (1) `_preprocess_file()` dispatches on three explicit MIME groups — images (`_IMAGE_MIMES`): Pillow EXIF strip + orientation fix; PDFs (`_PDF_MIMES`): pass-through; Word docs (`_WORD_MIMES`): pass-through; unknown MIME raises `ValueError` (defence-in-depth behind router's `ALLOWED_MIME_TYPES` gate); (2) persist to `storage_adapter`; (3) `document_version_manager.next_version()`; (4) create `Document` ORM record with `storage_path` + `checksum_sha256`; (5) `asyncio.create_task(_trigger_document_intelligence(...))` — fires `CLASSIFY_DOCUMENT` + `EXTRACT_OCR` tasks to DIA bus queue; (6) emit `DOCUMENT_UPLOADED` with badge count payload; module-level `document_upload_service` singleton
- `backend/app/services/document/__init__.py` ✓ — re-exports all 4 public service classes and singletons
- `backend/app/api/routers/documents.py` ✓ — `POST /cases/{case_id}/documents` updated: reads file bytes, resolves `client_id` from case, delegates to `document_upload_service.upload()`, then commits and returns `DocumentOut`

---

## Phase 4 — Frontend / UI

### [DONE] STEP-19 — Design System & Shared UI Components
**Date:** 2026-05-14 | **BRD:** Section 5.1.15, Section 5.1.3, Section 5.1.16 | **Depends:** STEP-03

**Artifacts produced:**
- `frontend/src/design-system/tokens.ts` ✓ — `DocumentStatus` (6), `TeamRole` (5), `VisibilityLevel`; `DOC_STATUS_COLORS` (bg/text/ring/dot per status), `DOC_STATUS_LABEL`, `ROLE_COLORS`, `ROLE_LABEL`, `PROGRESS_COLOR`
- `frontend/src/components/StatusBadge.tsx` ✓ — pill badge with dot and ring; sm/md sizes; driven by tokens
- `frontend/src/components/RoleBadge.tsx` ✓ — compact role pill; sm/md sizes
- `frontend/src/components/ProgressBar.tsx` ✓ — animated width transition; sm/md/lg heights; auto-green at 100%; ARIA progressbar role
- `frontend/src/components/DocumentRow.tsx` ✓ — Zustand-connected (active doc + drawer); status icon, version, date, AI/DIFF chips, StatusBadge
- `frontend/src/components/CategoryCard.tsx` ✓ — collapsible accordion; ProgressBar header; approved/total counter
- `frontend/src/components/CommentThread.tsx` ✓ — threaded comments with RoleBadge; visibility selector (ALL/ADVISOR_ONLY/CLIENT_VISIBLE); textarea + send
- `frontend/src/components/VisibilityToggle.tsx` ✓ — segmented 3-way toggle (All / Advisor / Client)
- `frontend/src/components/ConfirmationModal.tsx` ✓ — portal overlay; danger/warning/default variants; ESC key + backdrop close; loading state
- `frontend/src/components/UploadButton.tsx` ✓ — drag-and-drop + click; MIME type allowlist guard; disabled + dragging states
- `tsc --noEmit` passes with zero errors ✓

### [ ] STEP-20 — Advisor Workspace View (All 16 Features)
**BRD:** Section 5.1, FR-07–10 | **Depends:** STEP-14, STEP-15, STEP-19

### [ ] STEP-21 — Client Portal View
**BRD:** Section 5.1.6–5.1.7, Section 5.2.2, FR-02 | **Depends:** STEP-14, STEP-15, STEP-19

### [ ] STEP-22 — Contact Centre Dashboard
**BRD:** Section 7.3, FR-05 | **Depends:** STEP-14, STEP-15, STEP-19

### [ ] STEP-23 — Agent Trace Canvas & Admin Config View
**BRD:** FR-11, Section 5.1.12–5.1.14 | **Depends:** STEP-14, STEP-15, STEP-19

---

## Phase 5 — AI / LLM Capabilities

### [ ] STEP-24 — LLM Provider Abstraction Layer
**BRD:** Section 5.1.12, FR-08 | **Depends:** STEP-02, STEP-05–08

### [ ] STEP-25 — Agent Prompt Library
**BRD:** Section 6.4, Section 6.1, FR-08 | **Depends:** STEP-24, STEP-05–08

### [ ] STEP-26 — Skills Framework (6 Shared Skills)
**BRD:** Section 6.4 | **Depends:** STEP-24, STEP-25, STEP-04–08

### [ ] STEP-27 — Streaming Conversational Interface (SSE Backend)
**BRD:** FR-02, Section 9.1 | **Depends:** STEP-14, STEP-24, STEP-05, STEP-13

### [ ] STEP-28 — AI Validation & Version Diff (End-to-End Wire)
**BRD:** FR-08, FR-09, Section 5.1.10–5.1.11 | **Depends:** STEP-07, STEP-14, STEP-15, STEP-24, STEP-25, STEP-18

---

## Phase 6 — Compliance & Audit

### [ ] STEP-29 — Human-in-the-Loop Review Workflow
**BRD:** FR-13 | **Depends:** STEP-06, STEP-09, STEP-13, STEP-14, STEP-15, STEP-26

### [ ] STEP-30 — Configurable Checkpoint Rules (FR-15)
**BRD:** FR-15, Section 10.2 | **Depends:** STEP-06, STEP-12, STEP-14, STEP-29

### [ ] STEP-31 — Append-Only Audit Event Log
**BRD:** FR-14, Section 10.2 | **Depends:** STEP-10, STEP-12, STEP-14

### [ ] STEP-32 — Compliance Decision Logging & Evidence Packet Persistence
**BRD:** FR-14, Section 10.2 | **Depends:** STEP-29, STEP-31

### [ ] STEP-33 — Paused Journey Resumption
**BRD:** FR-12 | **Depends:** STEP-13, STEP-17, STEP-31

---

## Phase 7 — Demo & Visualization

### [ ] STEP-34 — Demo Scenarios, Fixtures & DemoModeService
**BRD:** Section 13.1, Section 11.2 | **Depends:** STEP-12, STEP-17, STEP-29

### [ ] STEP-35 — Agent Trace Canvas: Live Animation & Real-Time Log
**BRD:** FR-11 | **Depends:** STEP-15, STEP-23, STEP-17

### [ ] STEP-36 — Parallel Product Track Visualization
**BRD:** FR-01, Section 7.1 | **Depends:** STEP-20, STEP-22, STEP-35

---

## Phase 8 — Testing & Refinement

### [ ] STEP-37 — Unit Tests (Agents, Services, Skills)
**BRD:** Section 10.2 NFRs | **Depends:** STEP-04–08, STEP-13, STEP-16

### [ ] STEP-38 — Integration Tests (API + Database)
**BRD:** Section 10.2 NFRs | **Depends:** STEP-14, STEP-17, STEP-29, STEP-31, STEP-33, STEP-37

### [ ] STEP-39 — End-to-End Demo Rehearsal & NFR Validation
**BRD:** Section 10.2 NFRs, Section 12 Risk #5 | **Depends:** STEP-34, STEP-37, STEP-38

### [ ] STEP-40 — Final Polish, CHANGELOG Completion & Submission Readiness
**BRD:** Section 11.2 | **Depends:** All prior steps
