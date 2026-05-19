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

## Phase 3.5 — Auth (Backend)

### [DONE] STEP-18A — Auth System (Backend)
**Date:** 2026-05-14 | **BRD:** Section 9.1, FR-01, Section 10.2 | **Depends:** STEP-12, STEP-14

**Artifacts produced:**
- `db/schema/011_users.sql` ✓ — users table DDL (UUID PK, unique email, role CHECK constraint, 3 indexes)
- `backend/alembic/versions/0002_users.py` ✓ — migration (down_revision = "0001_initial"; creates users table + 3 indexes)
- `backend/app/models/users.py` ✓ — `User` SQLAlchemy ORM model (email, first/last_name, password_hash, role, is_active, timestamps, full_name property)
- `backend/app/models/__init__.py` ✓ — `User` import added for Alembic autodiscovery
- `backend/app/services/auth/auth_service.py` ✓ — `hash_password`, `verify_password`, `create_access_token` (JWT: sub/email/role/name/exp); `AuthService` with `signup`, `login`, `get_profile`, `update_profile`; module-level `auth_service` singleton
- `backend/app/services/auth/__init__.py` ✓ — re-exports `auth_service` and helpers
- `backend/app/api/routers/auth.py` ✓ — 4 endpoints (POST /auth/signup, POST /auth/login, GET /auth/me, PATCH /auth/me); Pydantic schemas: `SignupRequest` (password strength + match validation), `LoginRequest`, `ProfileUpdateRequest`, `UserOut`, `TokenResponse`
- `backend/app/api/dependencies/auth.py` ✓ — `DEMO_USER["role"]` updated `"Advisor"` → `"advisor"` (lowercase convention)
- `backend/app/main.py` ✓ — `auth.router` registered with `_prefix`
- `db/seeds/07_users.py` ✓ — 3 seed users with bcrypt-hashed passwords (admin / advisor / client)
- `db/seeds/seed.py` ✓ — `07_users.py` added to `SEED_FILES` list

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

### [DONE] STEP-20 — Advisor Workspace View (All 16 Features)
**Date:** 2026-05-14 | **BRD:** Section 5.1, FR-07–10 | **Depends:** STEP-14, STEP-15, STEP-19

**Artifacts produced:**
- `frontend/src/lib/api.ts` ✓ — axios instance + domain types: ClientOut, CaseOut, CaseSummary, ProductTrack, DocumentOut, FindingResult, ValidationResult, DiffResult, DiffSection, CollaborationComment
- `frontend/src/hooks/useDocuments.ts` ✓ — TanStack Query hooks: useCases, useCaseDetail, useCaseProgress, useDocuments, useDocument, useDiffResult, useValidateDocument, useUploadDocument, useUpdateDocumentStatus; cache-patch helpers: applyDocumentStatusUpdate, applyDocumentUploaded, applyValidationResult
- `frontend/src/hooks/useWorkspaceSocket.ts` ✓ — module-level socket.io singleton; joins/leaves case rooms on caseId change; handles DOCUMENT_STATUS_CHANGED, DOCUMENT_UPLOADED, PRODUCT_TRACK_UPDATE, PROGRESS_UPDATE, CASE_STAGE_CHANGED, KYC_RESULT, TASK_COMPLETE; patches TanStack Query cache in-place; increments Zustand badge counts
- `frontend/src/store/workspaceStore.ts` ✓ — updated: added `selectedCaseId`; `setSelectedClient(clientId, caseId)` replaces old single-arg form; selecting a new client resets drawer + active document
- `frontend/src/features/advisor/ClientRailNav.tsx` ✓ — left rail: useCases list; per-case progress bars (stage→% map); upload badge count chips; socket connection indicator (Wifi/WifiOff); loading skeleton; empty-state and error states
- `frontend/src/features/advisor/AIValidationPanel.tsx` ✓ — findings list with pass/warn/fail verdict icons and colour-coded cards; overall verdict badge; "Run AI Check" button wired to useValidateDocument mutation; running spinner; timestamp display
- `frontend/src/features/advisor/VersionDiffPanel.tsx` ✓ — similarity ratio ring; added/modified/removed sections with before/after inline comparison; unchanged sections hidden; computed_at timestamp
- `frontend/src/features/advisor/StatusEditor.tsx` ✓ — mirrors backend 6-state ALLOWED_TRANSITIONS; renders only valid next-state buttons; ConfirmationModal gate before committing; isUpdating loading state
- `frontend/src/features/advisor/ParallelProductTracks.tsx` ✓ — 2-column grid; per-product ProgressBar + steps counter; status icon (CheckCircle/AlertTriangle/Loader/Package); dynamic color variant by status; skeleton loader; empty state
- `frontend/src/features/advisor/DocumentDetailDrawer.tsx` ✓ — 4-tab drawer (Overview, AI Validation, Version Diff, Comments); document meta panel; download link; StatusEditor embedded in Overview tab; AI/Diff tab indicator chips when results exist; CommentThread with mock data (collaboration API wired in later step)
- `frontend/src/features/advisor/DocumentWorkspacePanel.tsx` ✓ — case progress header with overall % and escalation badge; ParallelProductTracks section; 6 CategoryCard sections (identity/financial/legal/insurance/compliance/entity) with DocumentRow list + per-category UploadButton; "Action needed" badge on NEEDS_REVISION categories
- `frontend/src/routes/AdvisorWorkspace.tsx` ✓ — 3-column layout: ClientRailNav | DocumentWorkspacePanel | DocumentDetailDrawer; useWorkspaceSocket wired on active caseId; empty state prompt when no client selected
- `tsc --noEmit` passes with zero errors ✓

### [DONE] STEP-21 — Client Portal View
**Date:** 2026-05-14 | **BRD:** Section 5.1.6–5.1.7, Section 5.2.2, FR-02 | **Depends:** STEP-14, STEP-15, STEP-19

**Artifacts produced:**
- `frontend/src/hooks/useClientDocuments.ts` ✓ — thin wrappers: `useClientDocuments`, `useClientProgress`, `useClientUpload` delegating to existing TanStack Query hooks
- `frontend/src/hooks/useClientChat.ts` ✓ — `useChatHistory(caseId)` (staleTime: Infinity, gcTime: 0 for clean case switching); `useSendMessage(caseId)` mutation with full SSE streaming (fetch + ReadableStream, `data: chunk` parsing, `[DONE]` sentinel, graceful fallback for non-event-stream responses); both wired to `useChatStore`
- `frontend/src/features/client/ClientProgressBar.tsx` ✓ — client-friendly progress card; stage→label map (Getting Started/Identity Verification/Account Setup/Final Review/All Done!); dynamic colour scheme (blue/green/amber) per stage; document approved/total counter
- `frontend/src/features/client/ConversationalChat.tsx` ✓ — user/assistant `MessageBubble` components; animated 3-dot `TypingIndicator`; streaming ghost bubble (`streamingText` state shows in-flight SSE content); Enter-to-send (Shift+Enter for newline); auto-scroll to bottom on every message update
- `frontend/src/features/client/DocumentUploadCard.tsx` ✓ — per-category card with description, existing doc list with `StatusBadge` + version indicator; drag-and-drop + click upload zone; MIME allowlist guard; uploading spinner + new-version label when docs already exist
- `frontend/src/features/client/ClientDocumentHub.tsx` ✓ — 2-column grid of 6 `DocumentUploadCard` instances; approved/total summary header; loading skeleton; null guard for caseId
- `frontend/src/routes/ClientPortal.tsx` ✓ — replaces placeholder; 440px fixed chat rail (progress bar + ConversationalChat) + flex-1 document panel; auto-selects first case; case-selector dropdown when multiple cases exist; hydrates chatStore from server history on case change; `useWorkspaceSocket` for real-time document/progress updates; `tsc --noEmit` passes with zero errors ✓

### [DONE] STEP-22 — Contact Centre Dashboard
**Date:** 2026-05-14 | **BRD:** Section 7.3, FR-05, Hackathon Criterion #6 | **Depends:** STEP-14, STEP-15, STEP-19

**Artifacts produced:**
- `frontend/src/lib/socket.ts` ✓ — shared `getSocket()` singleton; eliminates duplicate socket connections when multiple hooks coexist; `useWorkspaceSocket` updated to import from here
- `frontend/src/lib/api.ts` ✓ — `CallSummary` interface added (summary, key_points[], recommended_actions[], stage_label, generated_at)
- `frontend/src/hooks/useAllCases.ts` ✓ — `useAllCases()` (60s refetchInterval for live CC dashboard), `useClientDetail(caseId)` → `CaseSummary`
- `frontend/src/hooks/useCallSummary.ts` ✓ — `useCallSummary(caseId)` → `CallSummary`; `retry: false` so missing backend endpoint degrades gracefully; exports `ccQk` for cache invalidation
- `frontend/src/features/contact-centre/ProductTrackSummary.tsx` ✓ — compact inline product track rows (icon + label + ProgressBar + %) for CC context
- `frontend/src/features/contact-centre/CallSummaryCard.tsx` ✓ — AI call summary card with key_points and recommended_actions lists; loading skeleton; graceful "not yet available" empty state with refresh button
- `frontend/src/features/contact-centre/CCActionBar.tsx` ✓ — Log Call / Send Email / Open Case buttons; conditional Escalate / Mark Resolved toggle based on `summary.escalated`
- `frontend/src/features/contact-centre/ClientStatusTable.tsx` ✓ — real-time searchable client list (filter by name/stage/product); stage badge + ProgressBar per row; escalation and complete icons; Zustand `ccStore` for selection and filter text
- `frontend/src/features/contact-centre/ClientDetailPanel.tsx` ✓ — client header (avatar, name, case ID, stage badge); stats row (overall %, docs approved/total, escalation flag); CCActionBar; ProductTrackSummary; CallSummaryCard; loading skeleton and empty-state prompt
- `frontend/src/routes/ContactCentre.tsx` ✓ — 2-panel layout (320px client list + flex detail); CC-specific socket hook (ref-based callback avoids stale closure); top bar with live/reconnecting indicator and case count; `tsc --noEmit` passes with zero errors ✓

### [DONE] STEP-23 — Agent Trace Canvas & Admin Config View
**Date:** 2026-05-14 | **BRD:** FR-11, Section 5.1.12–5.1.14, Hackathon Criterion #10 | **Depends:** STEP-14, STEP-15, STEP-19

**Artifacts produced:**
- `frontend/src/lib/api.ts` ✓ — `AgentOut`, `AgentTaskOut`, `AgentTraceOut`, `LLMConfig`, `ValidationPrompt` interfaces added
- `frontend/src/hooks/useAgentTrace.ts` ✓ — `useAgents()`, `useAgentTrace(caseId)` with `agentQk` query keys; 15s refetchInterval for live trace data
- `frontend/src/hooks/useLLMConfig.ts` ✓ — `useLLMConfig()` with placeholder defaults; `useUpdateLLMConfig()` mutation wired to PUT /admin/llm-config
- `frontend/src/hooks/useValidationPrompts.ts` ✓ — `useValidationPrompts()` parallel fetches all 6 categories (graceful fallback to defaults); `useUpdateValidationPrompt()` mutation
- `frontend/src/features/agent-trace/agentPositions.ts` ✓ — `AGENT_IDS` (8), `AGENT_LABELS`, `AGENT_POSITIONS` layout (3-row hierarchy), `STATIC_EDGES` (9 structural connections)
- `frontend/src/features/agent-trace/AgentNode.tsx` ✓ — Custom React Flow node: icon per agent type (Lucide), state-driven colour (idle grey → active blue → escalated amber → complete green), animated status dot, state badge; uses `AgentNodeData` type
- `frontend/src/features/agent-trace/AgentDetailPopover.tsx` ✓ — Right-panel agent detail: node state badge, description from trace data, recent task list with status icons and duration_ms
- `frontend/src/features/agent-trace/MessageLog.tsx` ✓ — Scrollable A2A message log from `traceStore.messageLog`: from→to arrows, status colour badges, time display; empty state prompt
- `frontend/src/features/agent-trace/useAgentTraceSocket.ts` ✓ — Socket hook: joins case room, handles `agent_message` (enqueue edge + active node), `task_assigned`, `task_complete` (complete/idle node), `escalation_triggered` (escalated node), `case_stage_changed`; leaves room on caseId change with full store reset
- `frontend/src/features/agent-trace/AgentTraceCanvas.tsx` ✓ — Full React Flow canvas: 8 agent nodes at fixed positions, `NODE_TYPES` registration, static edges (grey/smoothstep) + animated in-flight edges (blue/animated, auto-expire after 2s via `window.setTimeout`), case selector dropdown, state legend, MiniMap with colour-coded nodes, `AgentDetailPopover` + `MessageLog` in right panel (320px); `@xyflow/react/dist/style.css` imported
- `frontend/src/features/admin/LLMProviderConfig.tsx` ✓ — Provider selector (4 providers: Anthropic, OpenAI, Google, Local) with preset model lists + custom model text input; saves to PUT /admin/llm-config
- `frontend/src/features/admin/DeterministicControls.tsx` ✓ — Sliders + inputs for all 7 controls (temperature, top_p, frequency_penalty, presence_penalty, seed, max_retries, cache_ttl); tooltip descriptions via hover; saves to PUT /admin/llm-config
- `frontend/src/features/admin/ValidationPromptEditor.tsx` ✓ — Per-category vertical tab (6 categories); goal textarea + factors list with add (Enter key) / remove (×); saves per-category to PUT /admin/validation-prompts/{category}
- `frontend/src/features/admin/CheckpointRulesEditor.tsx` ✓ — Table of 5 default checkpoint rules (4 dimensions: product_type, risk_level, account_value_band, jurisdiction); inline add-rule form; local state with note that DB persistence is wired in STEP-30
- `frontend/src/routes/AgentTrace.tsx` ✓ — Full-height layout: header bar + `AgentTraceCanvas` filling remaining viewport height
- `frontend/src/routes/AdminConfig.tsx` ✓ — Vertical tab nav (LLM Provider | Deterministic Controls | Validation Prompts | Checkpoint Rules) + scrollable content pane
- `tsc --noEmit` passes with zero errors ✓

---

## Phase 4.5 — Auth (Frontend)

### [DONE] STEP-23A — Auth UI (Frontend)
**Date:** 2026-05-14 | **BRD:** Section 5.1, Section 5.2, FR-01 | **Depends:** STEP-18A, STEP-19, STEP-03

**Artifacts produced:**
- `frontend/src/store/authStore.ts` ✓ — Zustand `AuthState` with `persist` middleware → `localStorage` key `gg_auth`; `AuthUser` interface; `setAuth` / `clearAuth` actions
- `frontend/src/store/index.ts` ✓ — `useAuthStore` + `AuthUser` re-exported
- `frontend/src/lib/api.ts` ✓ — `UserOut`, `TokenResponse` interfaces added; request interceptor attaches `Authorization: Bearer <token>`; response interceptor clears auth + redirects to `/login` on 401
- `frontend/src/hooks/useAuth.ts` ✓ — `useSignup()`, `useLogin()` (both call `setAuth` + navigate to role default route on success), `useProfile()` (enabled when authenticated), `useUpdateProfile()` (patches query cache + refreshes store)
- `frontend/src/components/ProtectedRoute.tsx` ✓ — redirects unauthenticated users to `/login`; redirects wrong-role users to their default route
- `frontend/src/features/auth/LoginForm.tsx` ✓ — email + password form; `useLogin` mutation; error display
- `frontend/src/features/auth/SignupForm.tsx` ✓ — first/last name + email + password + confirm; `useSignup` mutation; error display
- `frontend/src/features/auth/ProfileCard.tsx` ✓ — read-only info rows (all roles); edit mode restricted to `client` role; `ConfirmationModal` gate before password change; `useUpdateProfile` mutation
- `frontend/src/features/auth/UserMenu.tsx` ✓ — click-outside-dismissible dropdown in NavBar right; shows full name + role; links to `/profile`; Sign Out clears store + navigates to `/login`
- `frontend/src/routes/Login.tsx` ✓ — branding header + `LoginForm`; redirects already-authenticated users to their default route
- `frontend/src/routes/Signup.tsx` ✓ — branding header + `SignupForm`; redirects already-authenticated users
- `frontend/src/routes/Profile.tsx` ✓ — `ProfileCard` page at `/profile`
- `frontend/src/App.tsx` ✓ — all routes wrapped with `ProtectedRoute` (correct `allowedRoles`); NavBar filters links by role; `<UserMenu />` mounted on right side; `/login` + `/signup` public; catch-all → `/login`
- `tsc --noEmit` passes with zero errors ✓

---

### [DONE] STEP-23B — Phase 4 API Contract & Type-Shape Remediation
**Date:** 2026-05-15 | **BRD:** Section 9.1, FR-07, FR-08, FR-09, FR-11 | **Depends:** STEP-14, STEP-18, STEP-20–23A

**Root cause:** A comprehensive audit identified 10 frontend↔backend contract mismatches causing API failures (HTTP 404/422) and a hard `TypeError` crash in the Agent Trace canvas. All fixes are backward-compatible and targeted — no surrounding code was refactored.

**Artifacts produced / modified:**

`backend/app/api/routers/documents.py` ✓
- `DocumentOut` — added `name` (alias for `original_filename`), `has_validation_result` (bool), `has_diff` (bool) as `@computed_field` properties; frontend was receiving `undefined` for these, causing blank names and non-functional tab badges
- `DiffOut` — added `parent_id`, `similarity_ratio`, `sections`, `summary`, `computed_at` as `@computed_field` properties unwrapping the nested `diff_result` dict; `VersionDiffPanel` was reading all-undefined fields from the raw dict wrapper
- Added `UpdateDocumentStatusRequest` Pydantic model
- Added `PATCH /documents/{document_id}` route (role-guarded Advisor/Admin); `useUpdateDocumentStatus` was calling this endpoint but it did not exist, causing every advisor status-change to 404

`backend/app/api/routers/cases.py` ✓
- Added `_STAGE_PROGRESS` and `_PRODUCT_STATUS_PROGRESS` lookup dicts
- `ProductTrackOut` — added `product_name` (str, default ""), `progress` (int, default 0), `steps_total` (int, default 0), `steps_completed` (int, default 0); old fields kept with defaults for backward compat
- `CaseProgressOut` — renamed `product_tracks` → `products`, `documents_required` → `documents_total`; added `client_id`, `client_name`, `overall_progress`, `escalated`; frontend `CaseSummary` type was fully mismatched causing "…" placeholders, 0% progress, and always-empty product tracks
- Added `_build_product_track(cp)` helper (constructs with full product + step data)
- `get_case_summary` — replaced `_get_case_or_404` with a comprehensive query using `selectinload(client)`, `selectinload(case_products).selectinload(product)`, `selectinload(case_products).selectinload(steps)` to populate all new fields without N+1 queries

`backend/app/api/routers/agents.py` ✓
- `AgentOut` — added `status` (`"active"` / `"inactive"` mapped from `is_active`) and `last_active` (`None` stub) as `@computed_field` properties
- `AgentTraceOut` — added `agents: list[AgentOut]` field; `AgentDetailPopover.tsx` was calling `traceData.agents.find(...)` which crashed with `TypeError` because backend returned no `agents` array
- `get_agent_trace` — queries all agents from the `agents` table and includes them in the response alongside tasks

`backend/app/api/routers/conversations.py` ✓
- Added `CallSummaryOut` Pydantic model
- Added `GET /cases/{case_id}/call-summary` stub endpoint returning a placeholder response; `useCallSummary` was hitting a 404 on every Contact Centre page load

`frontend/src/hooks/useClientChat.ts` ✓
- Fixed request body field name: `{ text }` → `{ message: text }` (backend `MessageRequest` declares `message: str`; Pydantic was returning 422 on every chat submission)
- Added `Authorization: Bearer <token>` header to raw `fetch()` call via `useAuthStore.getState().token` (missing header caused 401 Unauthorized when `DEMO_MODE=False`)
- Fixed SSE chunk parser: added `parsed.token` to the fallback chain (`parsed.chunk ?? parsed.text ?? parsed.token ?? ''`) to match the backend placeholder stream format `{"type":"token","token":"word"}`

**Bugs resolved:**
- CRASH-1: `TypeError: Cannot read properties of undefined (reading 'find')` on agent node click — fixed ✓
- API-1: `PATCH /api/documents/{id}` 404 on document status change — fixed ✓
- API-2: `POST /api/cases/{id}/message` 422 on chat send — fixed ✓
- API-3: `POST /api/cases/{id}/message` 401 without auth header — fixed ✓
- API-4: `GET /api/cases/{id}/call-summary` 404 on Contact Centre — fixed ✓
- API-5: SSE token chunks silently swallowed, always showing fallback message — fixed ✓
- DATA-1: All document names showing as `undefined`/`'Document'` — fixed ✓
- DATA-2: Validation/diff tab badges never appearing — fixed ✓
- DATA-3: Case summary showing "…" name, 0% progress, empty product tracks — fixed ✓
- DATA-4: `VersionDiffPanel` all-undefined fields (similarity, sections, summary) — fixed ✓
- DATA-5: `AgentDetailPopover` crash + no agent info — fixed ✓
- DATA-6: Agent status always `undefined` — fixed ✓

---

## Phase 5 — AI / LLM Capabilities

### [DONE] STEP-24 — LLM Provider Abstraction Layer
**Date:** 2026-05-15 | **BRD:** Section 5.1.12, FR-08 | **Depends:** STEP-02, STEP-05–08

**Artifacts produced:**
- `backend/app/services/llm/llm_provider.py` ✓ — `LLMMessage`, `LLMRequest`, `LLMResponse`, `LLMStreamChunk` Pydantic models; `LLMProvider` abstract base class with `complete()`, `stream()`, `is_available()` interface
- `backend/app/services/llm/providers/anthropic_provider.py` ✓ — `AnthropicProvider`: Anthropic SDK, prompt caching via ephemeral `cache_control` on system block, `stream()` via `client.messages.stream()` async context manager, `cached` flag from `cache_read_input_tokens`
- `backend/app/services/llm/providers/openai_provider.py` ✓ — `OpenAIProvider`: `AsyncOpenAI`, `seed`/`frequency_penalty`/`presence_penalty` params, `stream=True` async iterator
- `backend/app/services/llm/providers/google_provider.py` ✓ — `GoogleProvider`: `google-generativeai` SDK (sync wrapped in `run_in_executor`), `GenerationConfig` for temperature/top_p/max_output_tokens
- `backend/app/services/llm/providers/local_model_provider.py` ✓ — `LocalModelProvider`: `httpx.AsyncClient` against OpenAI-compatible `/chat/completions`; SSE line parsing for streaming
- `backend/app/services/llm/llm_provider_factory.py` ✓ — `LLMProviderFactory.create()` reads provider/model from settings + runtime overrides; `create_fallback_ordered()` returns primary-first list of available providers; module-level `llm_provider_factory` singleton
- `backend/app/services/llm/llm_fallback_chain.py` ✓ — `LLMFallbackChain.complete()` / `.stream()`: rebuilds provider list from factory on each call (picks up admin overrides live), logs per-provider failures, raises only when all fail; module-level `llm_fallback_chain` singleton
- `backend/app/services/llm/deterministic_controls_applier.py` ✓ — `DeterministicControlsApplier.apply()` stamps 5 deterministic params (temperature, top_p, seed, frequency_penalty, presence_penalty) from merged settings+overrides onto an `LLMRequest` copy; module-level `set_overrides()` / `clear_overrides()` / `get_all_overrides()` shared by factory and admin router; `controls_applier` singleton
- `backend/app/services/llm/__init__.py` ✓ — re-exports all public symbols
- `backend/app/services/llm/providers/__init__.py` ✓ — re-exports all 4 provider classes
- `backend/app/api/routers/admin/llm_config.py` ✓ — updated to use `set_overrides()` / `clear_overrides()` / `get_all_overrides()` from `deterministic_controls_applier`; dropped local `_overrides` dict so admin UI changes immediately affect all LLM calls

### [DONE] STEP-25 — Agent Prompt Library
**Date:** 2026-05-15 | **BRD:** Section 6.4, Section 6.1, FR-08 | **Depends:** STEP-24, STEP-05–08

**Artifacts produced:**
- `prompts/orchestrator/system.txt` ✓ — workflow stages, routing rules, FSM responsibilities
- `prompts/customer_service/system.txt` ✓ — conversational persona, 12-section sequencing, extraction rules
- `prompts/customer_service/data_collection.txt` ✓ — structured data extraction task prompt with field normalisation rules and template variables
- `prompts/kyc_compliance/system.txt` ✓ — risk scoring model (identity×0.4 + AML×0.4 + profile×0.2), band thresholds, driver lists
- `prompts/kyc_compliance/risk_assessment.txt` ✓ — LLM risk narrative task prompt; JSON schema with APPROVE/ESCALATE/REQUEST_MORE_INFO recommendation
- `prompts/document_intelligence/system.txt` ✓ — 6-category taxonomy, 4-step processing pipeline, FindingResult schema, classification confidence thresholds
- `prompts/document_intelligence/completeness_validation.txt` ✓ — completeness validation task prompt with category-specific factor injection via template variables
- `prompts/product_onboarding/cash_account.txt` ✓ — Cash Account suitability criteria, 7-step onboarding sequence, SuitabilityAssessor weight configuration
- `prompts/product_onboarding/retirement_account.txt` ✓ — Retirement Account suitability criteria, 8-step onboarding sequence, near-retirement enhanced review flag
- `prompts/contact_centre/call_summary.txt` ✓ — call summary task prompt; CallSummary JSON schema with summary/key_points/recommended_actions
- `prompts/validation_defaults/identity.json` ✓ — 6 validation factors
- `prompts/validation_defaults/financial.json` ✓ — 5 validation factors
- `prompts/validation_defaults/legal.json` ✓ — 5 validation factors
- `prompts/validation_defaults/insurance.json` ✓ — 5 validation factors
- `prompts/validation_defaults/compliance.json` ✓ — 6 validation factors
- `prompts/validation_defaults/entity.json` ✓ — 5 validation factors

### [DONE] STEP-26 — Skills Framework (6 Shared Skills)
**Date:** 2026-05-15 | **BRD:** Section 6.4, Hackathon Criterion #7 | **Depends:** STEP-24, STEP-25, STEP-04–08

**Artifacts produced:**
- `backend/app/agents/skills/base_skill.py` ✓ — `BaseSkill` ABC: `invoke(agent_id, case_id, client_id, **kwargs)` times execution + appends `SKILL_INVOKED` record to `event_logs` (graceful-fail on DB error); `_execute(**kwargs)` abstract
- `backend/app/agents/skills/information_extraction_skill.py` ✓ — `InformationExtractionSkill`: LLM extracts requested fields from unstructured text → `{extracted: {field: value}, provider, model}`
- `backend/app/agents/skills/decision_reasoning_skill.py` ✓ — `DecisionReasoningSkill`: LLM chain-of-thought over context + options → `{decision, reasoning, confidence, key_factors}`
- `backend/app/agents/skills/status_summarisation_skill.py` ✓ — `StatusSummarisationSkill`: rule-based stage→label/progress mapping + optional LLM enhancement → `{stage_label, completion_percent, summary, key_points, recommended_actions}`
- `backend/app/agents/skills/clarification_skill.py` ✓ — `ClarificationSkill`: LLM generates up to 5 prioritised clarification questions for missing/ambiguous fields → `{questions: [{field, question, rationale}]}`
- `backend/app/agents/skills/escalation_skill.py` ✓ — `EscalationSkill`: heuristic fast-path (score ≥ threshold → always escalate) + LLM narrative when profile available → `{should_escalate, severity, reason, risk_factors, recommended_action}`
- `backend/app/agents/skills/product_suitability_skill.py` ✓ — `ProductSuitabilitySkill`: LLM assesses product vs client profile with heuristic fallback (risk-tolerance index comparison) → `{suitable, score, reasoning, concerns, conditions}`
- `backend/app/agents/skills/__init__.py` ✓ — re-exports all 6 skill classes + module-level singletons (`information_extraction`, `decision_reasoning`, `status_summarisation`, `clarification`, `escalation`, `product_suitability`)

---

### [DONE] STEP-27 — Streaming Conversational Interface (SSE Backend)
**Date:** 2026-05-15 | **BRD:** FR-02, Section 9.1, NFR < 3s | **Integration:** REAL (Anthropic streaming) | **Depends:** STEP-14, STEP-24, STEP-05, STEP-13

**Artifacts produced:**
- `backend/app/services/conversation/session_manager.py` ✓ — `ConversationSession` owns a per-case `DataCollectionOrchestrator` + `ConversationMemory` + `collection_complete` / `_advance_sent` flags; `SessionManager` singleton (get_or_create, get, evict)
- `backend/app/services/conversation/streaming_response_service.py` ✓ — `StreamingResponseService.stream_reply()`: async generator that calls `llm_fallback_chain.stream()` and yields SSE-formatted strings (`start → token... → end`); `stream_text()` typewriter fallback for pre-computed text; `CSA_SYSTEM_PROMPT` constant; `streaming_response_service` singleton
- `backend/app/services/conversation/conversation_coordinator.py` ✓ — `ConversationCoordinator.handle_message()` async generator: (1) resolves/creates session seeded with `selected_products` + prior `client_data` from `ContextStoreService`; (2) extracts field value from user message via DCO + fires `asyncio.create_task` to persist to ContextStore; (3) loads DB message history excluding the current user turn (already committed by router); (4) augments user message with `[CONTEXT: next field / completion]` guidance note for LLM steering; (5) delegates to `streaming_response_service.stream_reply()`, yielding all SSE chunks; (6) post-streaming: persists assistant message to `conversation_messages` + signals `ADVANCE_STAGE → KYC` to OrchestratorAgent when all fields are collected; `conversation_coordinator` singleton
- `backend/app/services/conversation/__init__.py` ✓ — re-exports all 3 public singletons and classes
- `backend/app/api/routers/conversations.py` ✓ — `POST /cases/{case_id}/message`: removed `_placeholder_stream`; user message persisted to DB before streaming; delegates to `conversation_coordinator.handle_message()` as `StreamingResponse` body; `metadata={}` → `extra_metadata={}` (STEP-14 ORM convention); unused `asyncio`/`json` imports removed

---

### [DONE] STEP-28 — AI Validation & Version Diff (End-to-End Wire)
**Date:** 2026-05-15 | **BRD:** FR-08, FR-09, Section 5.1.10–5.1.11, Hackathon Criteria #8, #9 | **Integration:** REAL (LLM) | **Depends:** STEP-07, STEP-14, STEP-15, STEP-24, STEP-25, STEP-18

**Artifacts produced / modified:**

`backend/app/services/validation/prompt_override_store.py` ✓ — shared singleton `_prompt_overrides` dict with typed functions (`set_prompt_override`, `get_prompt_override`, `reset_prompt_override`, `is_overridden`); decouples admin router from service layer so no upward imports

`backend/app/services/validation/validation_prompt_repository.py` ✓ — `get_effective_prompt(category)` resolution order: (1) in-memory admin override via `prompt_override_store`, (2) `prompts/validation_defaults/{category}.json` file, (3) hardcoded fallback; all 6 categories + unknown covered

`backend/app/services/validation/validation_orchestrator.py` ✓
- `ValidationOrchestrator.validate_document(document_id, db)`: loads Document → reconstructs `OcrResult` from JSONB (falls back to simulated `OcrExtractor.extract()` when no OCR data stored) → loads effective prompt from repository → `AICompletenessValidator.validate()` (LLM via fallback chain + heuristic fallback) → persists `validation_result` JSONB + advances status `RECEIVED → UNDER_REVIEW` → emits `DOCUMENT_STATUS_CHANGED` socket event → returns `ValidationResult`
- `ValidationOrchestrator.compute_diff(document_id, db)`: loads Document + parent → extracts raw text from both `ocr_result` JSONB fields (field-dict fallback; synthetic demo fallback) → `VersionDiffDetector.compute()` (Python difflib) → persists `diff_result` JSONB → returns `DiffResult`
- `run_validate_in_background(document_id)` / `run_diff_in_background(document_id)`: background task wrappers each acquire their own `AsyncSessionLocal` session; safe for `asyncio.create_task`
- `validation_orchestrator` module-level singleton

`backend/app/services/validation/__init__.py` ✓ — re-exports all public symbols

`backend/app/api/routers/admin/validation_prompts.py` ✓ — updated: local `_prompt_overrides` dict replaced with `prompt_override_store` functions; admin PUT/DELETE now write through the shared store so `ValidationOrchestrator` immediately picks up changes

`backend/app/api/routers/documents.py` ✓ — `POST /documents/{id}/validate`: advances status `RECEIVED → UNDER_REVIEW` then fires `asyncio.create_task(run_validate_in_background(document_id))`; returns 202 immediately; LLM result pushed to frontend via socket event

`backend/app/services/document/document_upload_service.py` ✓ — Step 5b: when `parent_doc_id is not None`, fires `asyncio.create_task(run_diff_in_background(doc.id))` so version diff computed automatically on every document resubmission

`backend/app/agents/document_intelligence/ai_completeness_validator.py` ✓
- `_llm_validate()` refactored: now routes through `LLMFallbackChain.complete()` + `DeterministicControlsApplier.apply()` so admin-configured provider, model, and deterministic parameters take effect; removed direct `anthropic.AsyncAnthropic` client instantiation and `_get_client()` method
- Returns `(findings, llm_used: bool)` tuple so `validate()` can accurately set `llm_used` on the result
- Removed STEP-28 TODO comment; updated `_DEFAULT_PROMPTS` docstring to clarify it is the final in-validator fallback (not the primary prompt source)
- Fixed deprecated `datetime.utcnow()` → `datetime.now(timezone.utc)`

**End-to-end flow:**
1. Advisor clicks "Run AI Check" → `POST /documents/{id}/validate` → 202 returned immediately
2. Background: OCR data reconstructed (or simulated) → effective prompt loaded → `LLMFallbackChain` calls Anthropic (with prompt caching + deterministic controls) → parses `FindingResult[]` JSON → heuristic fallback if all providers fail → persists to `documents.validation_result` JSONB
3. `DOCUMENT_STATUS_CHANGED` socket event → `AIValidationPanel` updates in real time with pass/warn/fail findings
4. Client resubmits document (`parent_doc_id` set) → diff auto-triggered on upload → `VersionDiffDetector.compute()` → persists to `documents.diff_result` JSONB → `VersionDiffPanel` shows similarity ratio + field-level added/modified/removed sections

---

---

## Phase 6 — Compliance & Audit

### [DONE] STEP-29 — Human-in-the-Loop Review Workflow
**Date:** 2026-05-15 | **BRD:** FR-13, Hackathon Criteria #5, #11 | **Depends:** STEP-06, STEP-09, STEP-13, STEP-14, STEP-15, STEP-26

**Artifacts produced / modified:**

`backend/app/services/compliance/evidence_packet_assembler.py` ✓ — `EvidencePacketAssembler.assemble()`: DB-backed assembly of kyc_result + client_summary (Client + ClientProfile join) + document_summary (by_status counts, missing categories) + case_summary; `assemble_from_agent_payload()` convenience wrapper; `evidence_packet_assembler` singleton

`backend/app/services/compliance/human_review_service.py` ✓ — `HumanReviewService`:
- `create_review()`: persists `KYCCheck` + `HumanReview` DB records; assembles evidence packet via `EvidencePacketAssembler`; stamps `onboarding_cases.shared_context["human_review_id"]` + updates stage to ESCALATED; updates in-memory `ContextStoreService`; emits `ESCALATION_TRIGGERED` socket event
- `decide()`: records decision + reviewer role + notes; emits `REVIEW_DECIDED` socket event; fires `_post_decision_workflow` background task
- `_resume_after_approval()`: advances case to PARALLEL_PRODUCTS; calls `orchestration_service.start_product_onboarding()` to fan out product tasks; emits `CASE_STAGE_CHANGED`
- `_terminate_after_rejection()`: marks case REJECTED + COMPLETE; emits `CASE_STAGE_CHANGED`
- `_request_more_info()`: stays ESCALATED; emits `CASE_STAGE_CHANGED`; `human_review_service` singleton

`backend/app/services/compliance/__init__.py` ✓ — re-exports both service classes and singletons

`backend/app/agents/orchestrator/orchestrator_agent.py` ✓ — `_handle_escalate()` now fires `asyncio.create_task(_persist_human_review(...))` which acquires its own `AsyncSessionLocal` session and calls `human_review_service.create_review()` — keeps agent layer DB-free while persisting the review record

`backend/app/services/orchestration/agent_orchestration_service.py` ✓ — added `start_product_onboarding(case_id, client_id, selected_products)`: publishes one `ONBOARD_PRODUCT` task per product directly to the bus; used by `HumanReviewService._resume_after_approval()` to resume workflow without re-running KYC

`backend/app/api/routers/reviews.py` ✓ — `POST /reviews/{review_id}/decide` wired to `human_review_service.decide()`; returns decision-specific message; role guards updated to accept lowercase role names (`advisor`, `admin`); `ValueError` from service layer mapped to `UnprocessableError`

`frontend/src/lib/api.ts` ✓ — added `ReviewOut`, `EvidencePacket`, `DecisionOut` interfaces

`frontend/src/hooks/usePendingReviews.ts` ✓ — TanStack Query hooks: `usePendingReviews()` (15s refetch), `useReviewsByCase(caseId)`, `useReview(reviewId)`, `useEvidencePacket(reviewId)`, `useDecideReview()` mutation (invalidates all review queries on success); `reviewQk` query-key factory

`frontend/src/features/compliance-review/EscalationQueue.tsx` ✓ — scrollable list of pending escalations; risk band colour chips; case ID + escalation reason + timestamp per row; selected-row highlight; loading skeleton; empty-state with green checkmark

`frontend/src/features/compliance-review/EvidencePacketPanel.tsx` ✓ — 4-section evidence display (KYC scores heat-mapped by risk %, escalation reasons list, client profile key-value grid, document summary by status + missing categories, case details); `useEvidencePacket` TanStack Query hook

`frontend/src/features/compliance-review/ReviewActionBar.tsx` ✓ — 3-button action bar (Approve / Reject / Request Info); `ConfirmationModal` gate with optional notes textarea for audit trail; `useDecideReview` mutation with loading/error states; read-only decided view when status ≠ PENDING

`tsc --noEmit` passes with zero errors ✓

### [DONE] STEP-30 — Configurable Checkpoint Rules (FR-15)
**Date:** 2026-05-15 | **BRD:** FR-15, Section 10.2 | **Depends:** STEP-06, STEP-12, STEP-14, STEP-29

**Artifacts produced / modified:**

`backend/app/services/compliance/checkpoint_rule_repository.py` ✓ — In-memory singleton repository initialised with the 5 default rules from `CheckpointRuleEngine`; `get_all()`, `get()`, `add()`, `update()`, `remove()` (blocked for built-in rule IDs), `reset()`, `is_builtin()`, `make_rule_id()`; `_BUILTIN_IDS` frozenset guards against deleting system rules

`backend/app/api/routers/admin/checkpoint_rules.py` ✓ — 5 admin-only endpoints:
- `GET  /admin/checkpoint-rules` → `list[CheckpointRuleOut]`
- `POST /admin/checkpoint-rules` (201) → `CheckpointRuleOut`; auto-generates `rule_id` if omitted
- `PUT  /admin/checkpoint-rules/{rule_id}` → `CheckpointRuleOut`
- `DELETE /admin/checkpoint-rules/{rule_id}` → `{"deleted": rule_id}`; returns 422 for built-in rule attempts
- `POST /admin/checkpoint-rules/reset` → `list[CheckpointRuleOut]`; restores all 5 defaults

`backend/app/agents/kyc_compliance/kyc_compliance_agent.py` ✓ — Removed stored `_rule_engine` instance; `_handle_run_kyc()` now builds a fresh `CheckpointRuleEngine(rules=rule_repo.get_all())` on each KYC run so admin-configured rules take effect immediately without restart

`backend/app/main.py` ✓ — `checkpoint_rules.router` registered with `_prefix`

`backend/app/services/compliance/__init__.py` ✓ — `checkpoint_rule_repository` module re-exported

`frontend/src/lib/api.ts` ✓ — `CheckpointRuleOut` and `CreateCheckpointRuleRequest` interfaces added

`frontend/src/hooks/useCheckpointRules.ts` ✓ — TanStack Query hooks: `useCheckpointRules()`, `useCreateCheckpointRule()`, `useDeleteCheckpointRule()`, `useResetCheckpointRules()`; all mutations invalidate `checkpointQk.all` on success

`frontend/src/features/admin/CheckpointRulesEditor.tsx` ✓ — Fully rewritten: removed amber "local state only" banner; table now shows description, action chip, dimension chips (Risk/Product/Band/Jurisdiction), Source (Built-in shield / Custom); delete button disabled for built-in rules; add-rule form exposes all 4 dimension fields (risk_level dropdown, product_type text, account_value_band dropdown, jurisdiction text) + action + required docs (comma-separated); Reset to defaults button with confirm dialog; loading/error states throughout; `tsc --noEmit` passes with zero errors ✓

### [DONE] STEP-31 — Append-Only Audit Event Log
**Date:** 2026-05-15 | **BRD:** FR-14, Section 10.2 (100% of decisions logged) | **Depends:** STEP-10, STEP-12, STEP-14

**Artifacts produced / modified:**

`backend/app/services/audit/audit_event_types.py` ✓ — `AuditEventType` StrEnum (64 typed event constants across 10 categories: case lifecycle, client, data collection, KYC, document, product onboarding, human review, compliance, agent task, MCP, notification, auth, admin); `AuditEventCategory` StrEnum (7 categories)

`backend/app/services/audit/audit_log_service.py` ✓ — `AuditLogService` append-only service: `log()` core method (no UPDATE/DELETE methods exist); typed convenience helpers: `log_agent_task_completed`, `log_document_status_changed`, `log_review_created`, `log_review_decided`, `log_mcp_tool_called`, `log_compliance_decision`; accepts optional `db` session (adds to caller's transaction when provided; acquires own `AsyncSessionLocal` and commits when omitted); `audit_log_service` module-level singleton

`backend/app/services/audit/__init__.py` ✓ — re-exports `AuditEventType`, `AuditEventCategory`, `AuditLogService`, `audit_log_service`

`backend/app/api/routers/audit.py` ✓ — role guards updated from `"Advisor"/"ComplianceOfficer"/"Admin"` → lowercase `"advisor"/"compliance_officer"/"admin"` (matches JWT convention); `datetime.utcnow()` → `datetime.now(timezone.utc)`; added `GET /audit/event-types` endpoint returning sorted StrEnum values for filter dropdowns; `AuditEventType` import added

`backend/app/services/document/document_status_service.py` ✓ — `update_status()` now calls `audit_log_service.log_document_status_changed()` after every valid transition (within the same DB session); 100% of document status changes are now audited

`backend/app/services/compliance/human_review_service.py` ✓ — `create_review()` calls `audit_log_service.log_review_created()` (within the same DB session, committed with the review record); `decide()` calls `audit_log_service.log_review_decided()` (own session, fire-and-forget after commit) with decision-specific event types (REVIEW_APPROVED / REVIEW_REJECTED / REVIEW_MORE_INFO_REQUESTED)

`backend/app/mcp/mcp_logger.py` ✓ — `log()` now calls `audit_log_service.log_mcp_tool_called()` within the same session as the `MCPToolCall` record; both records committed atomically; 100% of MCP calls are now in event_logs in addition to mcp_tool_calls

`backend/app/agents/base/base_agent.py` ✓ — `timed_process()` fires `asyncio.create_task(audit_log_service.log_agent_task_completed(...))` for both SUCCESS and FAILED outcomes; every agent task decision is now logged to the audit trail without blocking the task response

### [DONE] STEP-32 — Compliance Decision Logging & Evidence Packet Persistence
**Date:** 2026-05-15 | **BRD:** FR-14, Section 10.2, Hackathon Criterion #11 | **Depends:** STEP-29, STEP-31

**Artifacts produced / modified:**

`backend/app/services/compliance/compliance_decision_logger.py` ✓ — `ComplianceDecisionLogger` class with two typed methods:
- `log_automated_kyc_decision()`: logs `COMPLIANCE_DECISION` event for every KYC engine outcome (PASSED → `KYC_APPROVED_AUTOMATED`, ESCALATED → `KYC_ESCALATED_FOR_REVIEW`, FAILED → `KYC_REJECTED_AUTOMATED`); carries full score breakdown (identity/AML/profile/composite), risk_band, escalation_reasons, required_documents, evidence_packet_id; acquires own DB session when no session provided
- `log_human_review_decision()`: logs `COMPLIANCE_DECISION` event for every human reviewer action (APPROVED → `REVIEW_APPROVED_BY_HUMAN`, REJECTED → `REVIEW_REJECTED_BY_HUMAN`, MORE_INFO_REQUESTED → `REVIEW_MORE_INFO_REQUESTED_BY_HUMAN`); carries reviewer_role, decision_notes, risk_band, composite_score from stored evidence packet; graceful-fail with error log on exception
- `compliance_decision_logger` module-level singleton

`backend/app/agents/kyc_compliance/kyc_compliance_agent.py` ✓ — `_signal_outcome()` now fires `asyncio.create_task(compliance_decision_logger.log_automated_kyc_decision(...))` after routing the bus signal; covers all three KYC outcomes; float() casts applied to Decimal-mapped score fields

`backend/app/services/compliance/human_review_service.py` ✓ — `decide()` now calls `compliance_decision_logger.log_human_review_decision()` after `audit_log_service.log_review_decided()`; risk_band and composite_score extracted from `review.evidence_packet["kyc_result"]`

`backend/app/services/compliance/__init__.py` ✓ — `compliance_decision_logger` and `ComplianceDecisionLogger` added to exports

`backend/app/api/routers/reviews.py` ✓ — `GET /reviews/{review_id}/evidence` enhanced: queries `event_logs` for `is_compliance_event=True` rows matching `case_id`, orders by `created_at`, includes up to 50 entries as `compliance_audit_trail` array alongside the existing `evidence_packet`; response now has shape `{review_id, evidence_packet, compliance_audit_trail}`

### [DONE] STEP-33 — Paused Journey Resumption
**Date:** 2026-05-15 | **BRD:** FR-12, Paused Journey Resumption Appendix | **Depends:** STEP-13, STEP-17, STEP-31

**Artifacts produced / modified:**

`backend/app/services/orchestration/journey_resumption_service.py` ✓ — `JourneyResumptionService` with single public entry point `resume_case(case_id)`:
- Loads `OnboardingCase` + `CaseProduct.steps` from DB via a single eager-loaded query
- `_restore_context()`: evicts stale in-memory cache so `ContextStoreService.get()` forces a DB read; falls back to fresh `initialise()` + `update(stage)` when `shared_context` is empty or unparseable
- `_respawn_agents()`: stage-keyed dispatch — INTAKE → `COLLECT_CLIENT_DATA` to CustomerServiceAgent; KYC → `RUN_KYC_CHECK` to KYCComplianceAgent; PARALLEL_PRODUCTS → per-product `ONBOARD_PRODUCT` with `resume_from_step` payload derived from `case_product_steps`; REVIEW → `CREATE_COLLABORATION_ROOM` to CollaborationAgent; ESCALATED / COMPLETE → log-only (no re-spawn)
- `_find_resume_step()`: returns the `step_index` of the first non-COMPLETE/SKIPPED `CaseProductStep`; returns `len(steps)` when all steps are done (triggers REVIEW advance)
- Logs `JOURNEY_RESUMED` audit event via `audit_log_service`
- Emits `CASE_STAGE_CHANGED` WebSocket event via `socket_emitter`
- `journey_resumption_service` module-level singleton

`backend/app/services/orchestration/agent_orchestration_service.py` ✓ — added `publish_task(task: TaskPacket)` public method: clean interface for JourneyResumptionService to push tasks onto the bus without accessing `_bus` directly

`backend/app/services/orchestration/__init__.py` ✓ — `JourneyResumptionService` and `journey_resumption_service` exported

`backend/app/api/routers/cases.py` ✓ — `POST /cases/{case_id}/resume`: switched from `orchestration_service.resume_onboarding()` to `journey_resumption_service.resume_case()`; role guard lowercased (`"Advisor"/"Admin"` → `"advisor"/"admin"` to match JWT convention)

### [DONE] STEP-33A — Conversational Interface Enhancements & Dynamic Progress Bar
**Date:** 2026-05-16 | **Depends:** STEP-21, STEP-27

**Artifacts produced / modified:**

`backend/app/agents/customer_service/data_collection_orchestrator.py` ✓ — upgraded from hardcoded fields to DB-backed question loading (`load_questions_from_db`); `_DB_TYPE_MAP` for question-type conversion; `validation_rules` field on `QuestionnaireField`; `get_question_id`, `get_questionnaire_id`, `is_db_loaded` accessors; hardcoded `_FIELDS` retained as fallback

`backend/app/api/routers/conversations.py` ✓ — added `GET /{case_id}/greet` SSE endpoint to stream the opening greeting for fresh conversations

`backend/app/services/conversation/conversation_coordinator.py` ✓ — added `handle_greeting()` async generator; DB answer persistence (`_persist_field` upserts to `onboarding_answers`; `_upsert_question_session` tracks progress in `onboarding_question_sessions`); emits `{type:"options"}` SSE for choice fields; emits `{type:"progress","questionnaire_pct":<0–100>}` after every reply and greeting so the frontend progress bar updates in real time

`backend/app/services/conversation/session_manager.py` ✓ — `ConversationSession` and `SessionManager.get_or_create` now accept and store `client_id`

`backend/app/services/conversation/streaming_response_service.py` ✓ — `stream_reply()` accepts optional `fallback_text`; streams it word-by-word when all LLM providers fail instead of emitting an error event

`db/seeds/03_questionnaire.py` ✓ — expanded from 30 → 45 questions across 11 sections (added trusted_contact, background, regulatory_questions, identity, tax, acknowledgement, sign sections)

`frontend/src/features/client/ConversationalChat.tsx` ✓ — added `OptionChips` component; wires `pendingOptions` from chatStore to render clickable answer chips after assistant replies; clears options on manual text input

`frontend/src/features/client/CreateCaseModal.tsx` ✓ — added `onClose` prop; `onCreated` now receives `newCase.id` so the portal can auto-switch to the newly created case

`frontend/src/hooks/useClientChat.ts` ✓ — added `useGreeting` hook (SSE stream from `/greet`); both `useGreeting` and `useSendMessage` parse `type:"options"` events → `setPendingOptions` and `type:"progress"` events → `setQuestionnairePct`

`frontend/src/routes/ClientPortal.tsx` ✓ — integrates `useGreeting`; `greetedCases` ref prevents double-greeting on re-render; `CreateCaseModal` receives `onClose` + `onCreated(newCaseId)` and auto-switches case after creation

`frontend/src/store/chatStore.ts` ✓ — added `pendingOptions`, `setPendingOptions`, `clearPendingOptions`; added `questionnairePct`, `setQuestionnairePct`; `clearMessages` resets both

`frontend/src/features/client/ClientProgressBar.tsx` ✓ — replaced static `STAGE_PROGRESS` lookup with live `questionnairePct` from chatStore; INTAKE: `(questionnairePct/100)×60`; KYC: 70; PARALLEL_PRODUCTS: `70+(docs_approved/docs_total)×30`; REVIEW: 95; COMPLETE: 100

---

## Phase 7 — Demo & Visualization

### [DONE] STEP-34 — Demo Scenarios, Fixtures & DemoModeService
**Date:** 2026-05-16 | **BRD:** Section 13.1, Section 11.2 (all 11 criteria) | **Depends:** STEP-12, STEP-17, STEP-29

**Artifacts produced / modified:**

`backend/app/services/demo/demo_mode_service.py` ✓ — `DemoModeService` singleton (`demo_mode_service`):
- `is_enabled()` → gates all intercepts via `settings.DEMO_MODE`
- `stream_canned_turn(case_id)` → async generator that streams the next pre-scripted turn as SSE tokens (~25 ms/word) and advances the per-case turn counter
- `get_validation_findings(category)` → returns pre-canned `FindingResult`-compatible dict for the given document category
- `get_kyc_result(case_id)` → returns the pre-canned KYC verification result for the case's pinned scenario ("passing" or "high_risk")
- `set_kyc_scenario(case_id, scenario)` / `get_kyc_scenario(case_id)` → per-case scenario pin (default "passing")
- `reset_case(case_id)` → clears turn counter + scenario for demo re-runs
- `status()` → admin summary: loaded turn count, categories, available scenarios, active case state

`backend/app/services/demo/__init__.py` ✓ — re-exports `DemoModeService`, `demo_mode_service`

`backend/app/services/demo/fixtures/kyc_high_risk.json` ✓ — Two KYC fixture objects: `passing` (confidence 0.975, no risk factors, aml_risk_level LOW) and `high_risk` (confidence 0.62, pep_match true, 3 AML risk factors, aml_risk_level HIGH)

`backend/app/services/demo/fixtures/conversation_turns.json` ✓ — 19 pre-scripted assistant turns covering the full onboarding conversation from greeting → full-name → DOB → nationality → email → phone → occupation → income → source_of_funds → address → id_type → id_number → products → investment_experience → risk_tolerance → investment_horizon → tax_residency → US_person → regulatory_question → completion acknowledgement

`backend/app/services/demo/fixtures/validation_findings.json` ✓ — Pre-canned findings for all 6 document categories: identity (5 pass + 1 warn, 94%), financial (5 pass, 96%), legal (2 pass + 2 warn, 82%), insurance (4 pass + 1 warn, 91%), compliance (6 pass, 98%), entity (3 pass + 2 warn, 78%)

`backend/app/api/routers/demo.py` ✓ — Demo admin router (`/api/demo/*`; blocked 404 when DEMO_MODE=False):
- `GET /demo/status` — service status + loaded fixture counts
- `POST /demo/cases/{case_id}/reset` — reset turn counter + KYC scenario
- `POST /demo/cases/{case_id}/kyc-scenario` — pin scenario ("passing" | "high_risk") for Scenario B
- `GET /demo/cases/{case_id}/kyc-scenario` — get active scenario

`backend/app/main.py` ✓ — `demo.router` registered with `_prefix`

`backend/app/services/conversation/streaming_response_service.py` ✓ — `stream_reply()` gains optional `case_id: UUID | None = None` param; when `case_id` is provided and `DEMO_MODE=True`, delegates immediately to `demo_mode_service.stream_canned_turn()` and returns — skips all LLM calls

`backend/app/services/conversation/conversation_coordinator.py` ✓ — Both `handle_message()` and `handle_greeting()` now pass `case_id=case_id` to `stream_reply()` so demo intercept fires correctly

`backend/app/agents/document_intelligence/ai_completeness_validator.py` ✓ — `validate()` checks `demo_mode_service.is_enabled()` before any LLM call; when enabled, constructs `ValidationResult` directly from the `validation_findings.json` fixture for the document category; gracefully falls through to normal validation if fixture loading fails

`backend/app/agents/kyc_compliance/kyc_compliance_agent.py` ✓ — `_simulate_identity_verification()` gains `case_id: UUID | None = None` param; when demo mode is enabled, returns pre-canned fixture from `demo_mode_service.get_kyc_result(case_id)` with fixture-specified latency; `_handle_run_kyc()` passes `case_id=task.case_id` to the method

`docs/demo_scenario_a.md` ✓ — Happy path walkthrough: Aarav Mehta, 2 products, PASSED KYC, no escalation; covers criteria #1 #2 #3 #4 #7 #8 #9 #10; includes pre-flight checklist, step-by-step guide, sample client inputs table, expected outcome checklist

`docs/demo_scenario_b.md` ✓ — Escalation path walkthrough: same client, HIGH_RISK KYC → human review → approve → resume; covers criteria #5 #6 #11; includes demo endpoint command, step-by-step guide, evidence packet fields table, expected outcome checklist, reset instructions

**Demo mode summary:**
- Set `DEMO_MODE=True` in `.env` to activate
- Conversation: 19 pre-scripted turns streamed word-by-word at realistic cadence (~25 ms/word)
- Validation: returns fixture findings instantly (< 100 ms) — no LLM latency
- KYC: defaults to "passing"; set to "high_risk" via `POST /api/demo/cases/{id}/kyc-scenario` for Scenario B
- All real agent FSM, DB persistence, socket events, and audit logging still execute normally — only LLM call is bypassed

### [DONE] STEP-35 — Agent Trace Canvas: Live Animation & Real-Time Log
**Date:** 2026-05-16 | **BRD:** FR-11, Hackathon Criterion #10 | **Depends:** STEP-15, STEP-23, STEP-17

**Artifacts produced:**
- `frontend/src/features/agent-trace/AgentTraceCanvas.tsx` ✓ — React Flow canvas: 9 agent nodes (8 + dual product tracks), animated edges, 2s auto-expire, case selector, state-colour legend
- `frontend/src/features/agent-trace/useAgentTraceSocket.ts` ✓ — socket handlers: AGENT_MESSAGE → enqueueEdge + setNodeState; TASK_ASSIGNED/COMPLETE; ESCALATION_TRIGGERED; CASE_STAGE_CHANGED; PROGRESS_UPDATE (parallel_products_started/complete → per-product node state)
- `frontend/src/features/agent-trace/agentPositions.ts` ✓ — 9-node layout, AGENT_NODE_MAP (product_onboarding → both product nodes), PRODUCT_NODE_MAP (product_code → canvas node ID), updated STATIC_EDGES
- `frontend/src/features/agent-trace/AgentNode.tsx` ✓ — icons for product_onboarding_cash and product_onboarding_retirement
- `frontend/src/features/agent-trace/AgentDetailPopover.tsx` ✓ — CANVAS_TO_A2A reverse-map for product track nodes
- `frontend/src/features/agent-trace/MessageLog.tsx` ✓ — reverse-chronological A2A message log with status colours
- `tsc --noEmit` passes with zero errors ✓

---

### [DONE] STEP-36 — Parallel Product Track Visualization
**Date:** 2026-05-16 | **BRD:** FR-01, Section 7.1, Hackathon Criterion #3 | **Depends:** STEP-20, STEP-22, STEP-35

**Artifacts produced:**
- `frontend/src/features/advisor/ParallelProductTracks.tsx` ✓ — two-column grid of `ProductTrackCard` (status indicator, ProgressBar, steps_completed/total); skeleton loader; empty state
- `frontend/src/features/contact-centre/ProductTrackSummary.tsx` ✓ — compact single-row per product with StatusDot + inline ProgressBar for Contact Centre panel
- `frontend/src/hooks/useWorkspaceSocket.ts` ✓ — `PRODUCT_TRACK_UPDATE` invalidates `caseSummary` query; `PROGRESS_UPDATE` handles parallel_products_started/complete events
- Canvas enhancement: dual `product_onboarding_cash` and `product_onboarding_retirement` nodes visible as separate nodes; both activated on parallel launch and individually completed via PROGRESS_UPDATE socket events ✓
- `tsc --noEmit` passes with zero errors ✓

---

### [DONE] STEP-36A — Agent Event Bus: Persist Agent Tasks to DB (Fix Agent Trace Canvas)
**Date:** 2026-05-18 | **BRD:** FR-11, Hackathon Criterion #10 | **Depends:** STEP-35, STEP-36

**Root cause:** `AgentEventBus.dispatch_loop()` processed every `TaskPacket` entirely in-memory. The `agent_tasks` table (created in migration `0001_initial`) was never written to, so `GET /api/agents/trace/{case_id}` always returned zero tasks and the Agent Trace Canvas showed no activity.

**Fix — single file changed:** `backend/app/agents/base/agent_event_bus.py`

- Added `datetime`, `UUID` imports and `TaskResponse` to top-level imports (previously only imported via `TYPE_CHECKING`).
- Added `_save_task_in_progress(packet, started_at)` private async helper: opens its own `AsyncSessionLocal`, inserts an `AgentTask` row with `status="IN_PROGRESS"` and `started_at` timestamp; swallows DB exceptions with `logger.warning` so a DB hiccup never crashes the dispatch loop.
- Added `_update_task_completed(task_id, response)` private async helper: opens its own `AsyncSessionLocal`, issues a SQLAlchemy `update()` to stamp `status`, `result`, `errors`, `duration_ms`, and `completed_at` on the existing row; same graceful-fail pattern.
- Updated `dispatch_loop()`:
  - Captures `started_at = datetime.utcnow()` immediately after `queue.get()`.
  - Awaits `_save_task_in_progress()` before calling `agent.timed_process()`.
  - On unhandled exception: synthesises a `TaskResponse(status="FAILED", errors=[str(exc)], ...)` rather than swallowing the error silently (previous behaviour discarded the response entirely).
  - Awaits `_update_task_completed()` after the `try/except/finally` block so the row is always finalised regardless of success or failure.

**No migrations required** — `agent_tasks` table and `AgentTask` ORM model existed since `0001_initial`.

**Artifacts modified:**
- `backend/app/agents/base/agent_event_bus.py` ✓

**Verification:**
1. Start backend → create a case → trigger onboarding
2. `GET /api/agents/trace/{case_id}` returns populated `AgentTask` rows with `status`, `duration_ms`, and `result`
3. Agent Trace Canvas nodes animate and message log populates via the existing socket events + the 15 s REST poll now also returns data
4. `SELECT id, from_agent, to_agent, task_type, status, duration_ms FROM agent_tasks WHERE case_id = '<uuid>';` shows rows

---

### [DONE] STEP-36B — Persist Admin Config to DB (Fix In-Memory Prompt & LLM Config Loss)
**Date:** 2026-05-18 | **BRD:** Section 5.1.12, FR-08, Section 10.2 | **Depends:** STEP-28, STEP-30, STEP-36A

**Root cause:** Three in-memory stores were lost on every server restart:
- `prompt_override_store._prompt_overrides` — per-category validation prompt edits made via Admin UI
- `deterministic_controls_applier._active_overrides` — LLM provider / model / temperature etc.
- `checkpoint_rule_repository._rules` — custom KYC checkpoint rules added/modified via Admin UI (originally deferred in STEP-30 with an explicit TODO comment)

**Design: write-through cache + single `admin_config` table**

All three stores keep their in-memory state as an L1 cache (synchronous reads — zero latency, no changes to callers). Writes now also fire an async DB upsert. A startup hook warms all caches from DB before the app begins serving requests.

The `admin_config` table uses a single JSONB blob per namespace (`validation_prompts`, `llm_config`, `checkpoint_rules`) — extensible, one migration, no schema change for new admin config areas.

**Artifacts produced / modified:**

`db/schema/012_admin_config.sql` ✓ — DDL reference: `admin_config(namespace PK, config JSONB, updated_at)`

`backend/alembic/versions/0004_admin_config.py` ✓ — migration (`down_revision = "0003_case_percentage"`); creates `admin_config` table

`backend/app/models/admin_config.py` ✓ — `AdminConfig` SQLAlchemy ORM model (namespace PK, config JSONB, updated_at)

`backend/app/models/__init__.py` ✓ — `AdminConfig` import added for Alembic autodiscovery

`backend/app/services/admin/__init__.py` ✓ — new package; re-exports `admin_config_repository`

`backend/app/services/admin/admin_config_repository.py` ✓ — `AdminConfigRepository` with 5 async methods:
- `load(namespace)` → `dict` (returns `{}` on DB error)
- `save(namespace, config)` → full upsert of blob
- `patch(namespace, updates)` → merge partial updates into stored blob
- `delete_key(namespace, key)` → remove one key from blob
- `clear(namespace)` → wipe all overrides for namespace
- All methods swallow DB exceptions with `logger.warning` (never crash callers)
- `admin_config_repository` module-level singleton
- Constants: `NAMESPACE_VALIDATION_PROMPTS = "validation_prompts"`, `NAMESPACE_LLM_CONFIG = "llm_config"`, `NAMESPACE_CHECKPOINT_RULES = "checkpoint_rules"`

`backend/app/services/validation/prompt_override_store.py` ✓ — write-through cache:
- `_prompt_overrides` dict retained as L1 cache; `get_prompt_override()` / `is_overridden()` unchanged (synchronous)
- `set_prompt_override()` → updates cache + `_fire_db_save()` (schedules `_persist_all()` task)
- `reset_prompt_override()` → updates cache + `_fire_db_delete(category)` (schedules `_delete_one()` task)
- `load_from_db()` async startup loader: clears cache, loads from `admin_config_repository.load("validation_prompts")`

`backend/app/services/llm/deterministic_controls_applier.py` ✓ — write-through cache (same pattern):
- `_active_overrides` dict retained as L1 cache; `get_all_overrides()` unchanged (synchronous)
- `set_overrides()` → updates cache + `_fire_db_patch()` (schedules `_persist_patch()` task)
- `clear_overrides()` → clears cache + `_fire_db_clear()` (schedules `_persist_clear()` task)
- `load_from_db()` async startup loader: clears cache, loads from `admin_config_repository.load("llm_config")`

`backend/app/services/compliance/checkpoint_rule_repository.py` ✓ — rewritten with write-through cache:
- `_rules` list retained as L1 cache; `get_all()` / `get()` / `is_builtin()` / `make_rule_id()` unchanged (synchronous)
- `add()` → appends to cache + `_fire_db_save()` (schedules `_persist_all()` task)
- `update()` → replaces in cache + `_fire_db_save()`
- `remove()` → removes from cache + `_fire_db_save()`
- `reset()` → restores cache to `_DEFAULT_RULES` + `_fire_db_clear()` (clears DB row so next startup also loads defaults)
- `load_from_db()` async startup loader: loads `{"rules": [...]}` blob from `admin_config_repository.load("checkpoint_rules")`; deserialises each dict back to `CheckpointRule` via `model_validate()`; falls back to `_DEFAULT_RULES` if DB is empty or deserialisation fails
- Removed stale TODO comment ("replaced by DB-backed store in a future phase")

`backend/app/main.py` ✓ — `on_startup()` now calls `load_prompt_overrides()`, `load_llm_config()`, and `load_checkpoint_rules()` before `orchestration_service.start()`; all imports are local to avoid circular imports at module level

**Zero changes to:**
- `validation_prompt_repository.py` — still calls `get_prompt_override()` synchronously
- `validation_prompts.py` admin router — still calls `set_prompt_override()` / `reset_prompt_override()`
- `llm_config.py` admin router — still calls `set_overrides()` / `clear_overrides()`
- `checkpoint_rules.py` admin router — still calls `rule_repo.add()` / `update()` / `remove()` / `reset()` synchronously
- `kyc_compliance_agent.py` — still builds `CheckpointRuleEngine(rules=rule_repo.get_all())`; now gets the persisted list
- Every other agent or service that reads these configs

`db/seeds/08_admin_config.py` ✓ — seeds all 3 namespace rows with empty `{}` config on fresh install; idempotent (skips rows that already exist)

`db/seeds/seed.py` ✓ — `08 — Admin Config` entry added to `SEED_FILES` list

**Verification:**
1. `alembic upgrade head && python db/seeds/seed.py` → `admin_config` table created; 3 namespace rows seeded
2. Set a validation prompt override in Admin UI → restart backend → override still active
3. Change LLM temperature in Admin UI → restart backend → temperature still applied
4. Add a custom checkpoint rule in Admin UI → restart backend → custom rule still present
5. `SELECT namespace, config FROM admin_config;` → shows 3 rows (`validation_prompts`, `llm_config`, `checkpoint_rules`)
6. Reset checkpoint rules in Admin UI → row shows `{}` blob; next restart loads `_DEFAULT_RULES`

---

### [DONE] STEP-36C — Advisor-to-Client Comment System
**Date:** 2026-05-18 | **BRD:** Section 5.1, Section 5.2.2, FR-05, FR-07 | **Depends:** STEP-14, STEP-20, STEP-21, STEP-36B

**Problem:** Advisors had no way to persist comments to the database, and clients had no way to see advisor notes on their documents. The `DocumentDetailDrawer` used hardcoded `MOCK_COMMENTS`, `onAddComment` only logged to the console, and the client portal had no comment UI at all.

**Visibility model — simplified to two options:**

| Frontend label | DB value | Visible to |
|---|---|---|
| Everyone (`ALL`) | `client_visible` | Advisor + Client |
| Advisor only (`ADVISOR_ONLY`) | `team` | Advisor only |

The previous `CLIENT_VISIBLE` option was redundant and removed from `CommentThread`.

**Backend — `backend/app/api/routers/collaboration.py` (new file)**

Two endpoints under the existing `/cases` prefix:

- `GET /cases/{case_id}/comments?document_id=<uuid>` — lists top-level comments for a case, optionally filtered by document; clients automatically see only `client_visible` rows; advisors see all
- `POST /cases/{case_id}/comments` — creates a `CollaborationComment`; auto-creates an OPEN `CollaborationRoom` for the case if none exists (using `_get_or_create_room` helper with `db.flush()` so the room ID is available before the comment insert); author full name stored in `extra_metadata["author_name"]`; maps frontend `visibility` string to DB constraint value via `_VIS_TO_DB` dict

Both endpoints use `get_current_user` dependency; role is mapped to canonical `TeamRole` casing via `_ROLE_MAP`. No new DB tables or migrations — `collaboration_rooms` and `collaboration_comments` tables already exist since `0001_initial`.

`backend/app/main.py` ✓ — `collaboration.router` imported and registered with `_prefix`

**Frontend — `frontend/src/hooks/useComments.ts` (new file)**

- `useComments(caseId, documentId?)` — TanStack Query `useQuery`; fetches `GET /cases/{caseId}/comments?document_id=...`; maps `CollaborationComment` API response to `Comment` component shape (includes `documentId` field); enabled only when `caseId` is set; 10 s stale time
- `useAddComment(caseId)` — TanStack Query `useMutation`; posts to `POST /cases/{caseId}/comments`; on success invalidates all `['cases', caseId, 'comments']` query keys so both the drawer and the client hub refetch

**`frontend/src/lib/api.ts` ✓**
- `CollaborationComment.visibility` narrowed from `'ALL' | 'ADVISOR_ONLY' | 'CLIENT_VISIBLE'` → `'ALL' | 'ADVISOR_ONLY'`
- `document_id: string | null` field added

**Advisor view changes:**

`frontend/src/components/CommentThread.tsx` ✓
- `Comment.visibility` type narrowed to `'ALL' | 'ADVISOR_ONLY'`
- `VISIBILITY_LABELS` map reduced to two entries
- `CLIENT_VISIBLE` `<option>` removed from the visibility `<select>`

`frontend/src/features/advisor/DocumentDetailDrawer.tsx` ✓
- Removed `MOCK_COMMENTS` constant and `Comment` type import
- Added `useComments(caseId, activeDocumentId)` — fetches only when Comments tab is active; scoped to the currently open document
- Added `useAddComment(caseId)` — called from `onAddComment` callback with `{ body, visibility, document_id: activeDocumentId }`
- Loading spinner shown while comments are fetching

**Client portal changes:**

`frontend/src/features/client/ClientDocumentModal.tsx` (new file)
- Centered overlay modal (max-w-md, max-h 85 vh) with backdrop click and Escape key dismiss
- Two tabs: **Overview** (status, category, version, uploaded date, SHA-256 if present) and **Advisor Notes**
- Advisor Notes tab calls `useComments(caseId, doc.id)` — API already filters to `client_visible` only for the client role; renders author name + `RoleBadge` + timestamp + comment body in the same style as `CommentBubble`; shows empty state with `MessageCircle` icon when no notes exist; shows count badge on tab when notes are present

`frontend/src/features/client/DocumentUploadCard.tsx` ✓
- Removed `commentsByDoc` prop and all inline comment rendering
- Added `onDocumentClick: (doc: DocumentOut) => void` prop
- Added `commentCountByDoc?: Record<string, number>` prop
- Each document row is now a `<button>` (`hover:bg-blue-50`) that fires `onDocumentClick`
- A `💬 N` pill badge (blue, `MessageCircle` icon + count) appears next to the document name when `commentCountByDoc[doc.id] > 0`

`frontend/src/features/client/ClientDocumentHub.tsx` ✓
- Added `useComments(caseId)` — fetches all case comments once (no document filter); API returns only `client_visible` rows for the client role
- Builds `commentCountByDoc` via `reduce` on the comments array keyed by `c.documentId`
- Manages `selectedDoc: DocumentOut | null` state
- Passes `commentCountByDoc` and `onDocumentClick={setSelectedDoc}` to each `DocumentUploadCard`
- Renders `<ClientDocumentModal>` when `selectedDoc` is set

**Artifacts produced / modified:**
- `backend/app/api/routers/collaboration.py` ✓ (new)
- `backend/app/main.py` ✓
- `frontend/src/hooks/useComments.ts` ✓ (new)
- `frontend/src/lib/api.ts` ✓
- `frontend/src/components/CommentThread.tsx` ✓
- `frontend/src/features/advisor/DocumentDetailDrawer.tsx` ✓
- `frontend/src/features/client/ClientDocumentModal.tsx` ✓ (new)
- `frontend/src/features/client/DocumentUploadCard.tsx` ✓
- `frontend/src/features/client/ClientDocumentHub.tsx` ✓

**Verification:**
1. Advisor opens Document Detail Drawer → Comments tab → posts "Please re-upload with better resolution" with visibility **Advisor only** → row saved in `collaboration_comments` with `visibility = 'team'`
2. Same flow with visibility **Everyone** → `visibility = 'client_visible'`
3. Client opens portal → document row shows `💬 1` badge next to name
4. Client clicks document → modal opens → Advisor Notes tab shows the "Everyone" comment; "Advisor only" comment is not visible
5. `SELECT content, visibility FROM collaboration_comments WHERE case_id = '<uuid>';` → rows present with correct visibility values

---

### [DONE] STEP-36D — Client Portal: 3-Panel Layout, Onboarding Form View & Inline Editing
**Date:** 2026-05-18 | **Depends:** STEP-33A, STEP-36B

**Summary:** Transformed the 2-panel client view (chat | documents) into a 3-panel resizable layout: chat (left) | live onboarding details form (centre) | document hub (right). Centre panel shows collected answers grouped by DB section in `order_index` sequence, with full inline click-to-edit capability. Document hub converted to a per-category accordion. Backend extended with three new REST endpoints for questionnaire schema, collected field retrieval, and direct field update.

**Artifacts produced / modified:**

`backend/app/api/routers/cases.py` ✓
- `GET /cases/{case_id}/questionnaire-schema` — returns all questions for the case's active questionnaire ordered by `order_index`; each item includes `question_key`, `section`, `label` (from `extra_metadata.label` or `_fmt_key(question_key)`), `order_index`, `field_type` (mapped via `_DB_TYPE_MAP`: `select→choice`, `multi_select→multi_choice`, `boolean→choice` with auto Yes/No options, `currency→number`), `options`, and `validation_rules`
- `GET /cases/{case_id}/collected-fields` — returns `shared_context.client_data` as `{client_data: {...}}`; client-role access guard matches JWT sub to case `client_id`
- `PATCH /cases/{case_id}/collected-fields` — accepts `{question_key, value}`; fetches current `shared_context`, merges updated key, writes back via SQLAlchemy `sa_update`; preserves all other JSONB keys; returns updated `client_data`
- `QuestionSchemaItem` Pydantic model extended: added `field_type: str`, `options: list[str] | None`, `validation_rules: dict[str, Any] | None`
- `UpdateCollectedFieldRequest` Pydantic model added
- `from sqlalchemy import select, update as sa_update` import updated

`frontend/src/routes/ClientPortal.tsx` ✓
- 3-panel resizable layout: `leftWidth` (default 380 px), `centerWidth` (default 360 px); right panel is flex-1
- `ResizeDivider` component — 5 px strip, `cursor-col-resize`, hover reveals blue line + 5-dot grip; document-level `mousemove`/`mouseup` listeners managed in `useEffect`
- `startResize` memoised with `useCallback([leftWidth, centerWidth])`
- Fetches `collectedData` via `useCollectedFields`, `schemaData` via `useQuestionnaireSchema`
- `questionnairePct` change in chatStore triggers `queryClient.invalidateQueries` on `collected-fields` so the form refreshes after each answer without polling
- `OnboardingFormView` receives `caseId`, `clientData`, `schema`, `isLoading` (removed `onCorrect` / `isQuestionnaireComplete` — edit is always available)
- Removed `setPendingCorrection` / `handleCorrect` (Option 3 re-ask approach fully reverted)

`frontend/src/features/client/OnboardingFormView.tsx` ✓ — new component
- Groups answered fields into sections by iterating the `schema` array (preserves DB `order_index` order); unknown keys appended to an "other" section
- `SYSTEM_KEYS = Set(['selected_products','version','created_at','updated_at'])` excluded from display
- Section headers: snake_case → Title Case via `sectionTitle()`
- Inline edit state: `editingKey`, `editValue` (string), `editMultiValues` (string[]), `editError`
- `startEdit(questionKey)`: initialises edit state from current value; multi_choice fields populate `editMultiValues` from stored array; number fields stringify raw value (commas stripped on save)
- Edit input rendered by `field_type`:
  - `choice` → `<ChoiceInput>` (`<select>` pre-seeded with all options, current value pre-selected)
  - `multi_choice` → `<MultiChoiceInput>` (checkbox list, existing selections pre-checked)
  - `number` → `<input type="number">`
  - `date` → `<input type="text" placeholder="DD/MM/YYYY">`
  - others → `<input type="text">`
- `validateField(value, item)`: client-side validation mirrors backend `validate_value`; checks `min_length` (only when explicitly in rules — no default-1 fallback), `max_length`, `alphanumeric` + `max_alphanumeric`, `min_digits` / `max_digits`, `postal_code` regex, `min_age` (DOB date parse), `future_date`; multi_choice requires ≥ 1 selection
- Validation error rendered inline in red below the input; API call blocked until error-free
- Number values parsed back to `float` before saving to preserve numeric JSONB type
- "Correct" pencil button: `invisible group-hover:visible` — only visible on row hover; rendered for every collected field; not gated by questionnaire completion
- Enter key saves; Escape key cancels
- Signature fields (`question_key` containing `"signature"`): display and edit input both rendered in `Dancing Script` cursive font (1.25 rem, navy `#1e3a5f`); edit placeholder reads "Sign here…"
- Summary bar shows total fields collected count

`frontend/src/features/client/ClientDocumentHub.tsx` ✓
- Replaced flat grid of `DocumentUploadCard` components with per-category accordion
- `AccordionItem`: header shows FolderOpen/CheckCircle/AlertTriangle icon + category title + document count badge + ChevronDown chevron; body contains document list + upload drop zone
- `openCategories: Set<string>` state; `hasOpenedRef` prevents re-expansion on re-render; first data load auto-opens categories that already have documents

`frontend/src/hooks/useDocuments.ts` ✓
- `QuestionSchemaItem` interface extended: `field_type: string`, `options?: string[] | null`, `validation_rules?: Record<string, unknown> | null`
- `useQuestionnaireSchema(caseId)`: fetches `/cases/{caseId}/questionnaire-schema`, `staleTime: 60_000`
- `useCollectedFields(caseId)`: fetches `/cases/{caseId}/collected-fields`, `staleTime: Infinity` (invalidated on `questionnairePct` change only)
- `useUpdateCollectedField(caseId)`: `PATCH /cases/{caseId}/collected-fields`; `onSuccess` invalidates `collected-fields` query key

`frontend/src/store/chatStore.ts` ✓
- `pendingCorrection`, `setPendingCorrection`, `clearPendingCorrection` removed (Option 3 re-ask approach reverted)
- `clearMessages` no longer resets `pendingCorrection`

`frontend/src/features/client/ConversationalChat.tsx` ✓
- Removed `pendingCorrection` import and auto-submit `useEffect` (Option 3 reverted)

`frontend/index.html` ✓
- Added Google Fonts preconnect + `Dancing Script` (weight 600) link for signature field rendering

**Bugs fixed in this step:**
- Datetime mismatch in `ConversationCoordinator._persist_field`: `answered_at` used timezone-aware `datetime.now(timezone.utc)` while DB columns are `TIMESTAMP WITHOUT TIME ZONE`; fixed to `datetime.now(timezone.utc).replace(tzinfo=None)`
- `validateField` default `minLen = 1` fallback caused incorrect "Must be at least 1 character(s)." error on fields whose validation relies solely on `min_digits` / `max_digits` (e.g. phone number); fixed to only enforce `min_length` when explicitly present in `validation_rules`

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
