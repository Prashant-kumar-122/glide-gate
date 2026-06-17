# Traceability Matrix

Living map from BRD requirements (FR/NFR/OBJ) and ADRs to CADF implementation phases and
test artifacts, per the AI-DLC working agreement. Updated at the end of each phase.

Legend: ✅ implemented & verified · 🟡 partial (phase in progress) · ⬜ planned in a future phase

---

## Functional Requirements

| Req | Description | CADF Phase | Status | Artifact(s) |
|---|---|---|---|---|
| FR-DM-01 | Document taxonomy: shared-core vs product-specific | Phase 4.5 | ⬜ | `Document.scope`, `domain_products.shared_core_types` |
| FR-DM-02 | Collect shared-core once; reuse across all products | Phase 4.5 | ⬜ | `GET /cases/{id}/requirements`, `DocumentRequirementsCenter` |
| FR-DM-03 | Prevent re-requesting valid existing docs | Phase 4.5 | ⬜ | `check_existing_shared_docs` node in DocumentIntelligenceAgent graph |
| FR-DM-04 | Validate completeness/legibility/type/expiry | Existing | 🟡 | `DocumentIntelligenceAgent`, `AICompletenessValidator` |
| FR-DM-05 | Track expiry; re-request on expiry/insufficiency | Existing | 🟡 | `document_status_service.py`, `version_diff_detector.py` |
| FR-DM-06 | Secure upload + versioned storage | Existing | ✅ | `document_storage_adapter.py`, `document_version_manager.py` |
| FR-WF-01 | Per-product configurable workflow | Phase 4 | ✅ | migration `0017_product_pipeline_seed.py`; `_load_pipeline_from_db()` in `product_onboarding_agent.py`; `domain_product_pipelines` rows seeded; `step_config JSONB` per step |
| FR-WF-02 | Per-product configurable rule sets | Phase 4 | ✅ | migration `0017` `suitability_criteria JSONB`; `SuitabilityAssessor.assess_with_criteria()`; `_load_suitability_criteria_from_db()`; 22 parity tests in `test_product_pipeline_config.py` |
| FR-OR-01 | Run product onboardings concurrently | Phase 0.5, Phase 4 | 🟡 | Temporal child workflows per product (`ProductOnboardingWorkflow`) |
| FR-OR-02 | Single client master linking journeys | Existing | ✅ | `Client` model, `OnboardingCase.client_id` FK |
| FR-OR-03 | Share shared-core results across journeys | Phase 4.5 | ⬜ | Document scope + `GET /cases/{id}/requirements` reuse map |
| FR-OR-04 | Delay in one product never blocks another | Phase 0.5, Phase 4.6 | ✅ | Independent Temporal child workflows; per-product activation gate (`ActivationGateService`); products activate independently; `ParallelProductTracks.tsx` "First Live" badge |
| FR-OR-05 | Unified multi-product status view | Existing | 🟡 | `GET /cases/{id}` status; `ParallelProductTracks.tsx` |
| FR-AG-01 | Agents autonomously progress the workflow | Phase 0.5 | ✅ | `OnboardingWorkflow` Temporal FSM + LangGraph `StateGraph` per agent |
| FR-AG-02 | Autonomous document collection and validation | Existing | 🟡 | `DocumentIntelligenceAgent`, `CustomerServiceAgent` |
| FR-AG-03 | Agents validate data, reconcile shared data | Phase 4.5 | ⬜ | Shared-core doc reuse across product tracks |
| FR-AG-04 | Agents trigger compliance/identity checks via integrations | Phase 6 | ✅ | `MCPRegistry.invoke()` grant-checked calls (ADR-007); KYC agent calls `verify_identity`, `check_sanctions`, `score_aml_risk` via `mcp_registry`; grant rows in `domain_agent_tool_grants` (migration 0020) |
| FR-AG-05 | Detect exceptions; escalate to human queue | Existing, Phase 9 | 🟡 | `HumanReview` model; `EscalationQueue.tsx`; admin portal exposes SLA regulated-stage guards that trigger escalation |
| FR-AG-06 | Respect HITL checkpoints + authority limits | Phase 7 | ✅ | `require_permission()` guards across all routers; `domain_permissions` rows per persona; 15-scope catalog (see `docs/specs/permission-model-security-review.md`) |
| FR-AG (fraud) | Fraud/anomaly screening; gates activation | Phase 4.6 | ✅ | `FraudScreeningAgent` (`agents/fraud_screening/graph.py`); runs concurrent with KYC via `asyncio.gather`; `fraud_screened` gate in `_evaluate_policy` |
| FR-GL-01 | Detect product satisfies activation criteria | Phase 4.6 | ✅ | `ActivationGateService` (`services/activation/activation_gate_service.py`); Python policy mirrors `policies/activation.rego`; `product_activation` table (migration 0018) |
| FR-GL-02 | Activate first completed product independently | Phase 4.6 | ✅ | `_activation_gate_node` in `product_onboarding/graph.py`; per-product `CRITERIA_MET → ACTIVATED` transition; account number provisioned immediately |
| FR-GL-03 | Continue remaining products after first activation | Phase 4.6 | ✅ | Independent Temporal child workflows (`ProductOnboardingWorkflow`); sibling workflows unblocked; `ParallelProductTracks.tsx` "First Live" badge |
| FR-CP-01 | Client self-service portal (sign in / resume) | Existing | 🟡 | `ClientPortal` route, `OnboardingWizard`; JWT auth (Keycloak deferred) |
| FR-CP-02 | Document upload capability | Existing | ✅ | `DocumentUploadCard`, `POST /documents/upload` |
| FR-CP-03 | Real-time notifications | Existing | 🟡 | `NotificationAgent`, socket.io; push notifications |
| FR-CP-04 | Collect-once document list per product | Phase 4.5 | ⬜ | `DocumentRequirementsCenter.tsx`, `GET /cases/{id}/requirements` |
| FR-CP-06 | E-signature & consent capture | Deferred (Phase 9+) | ⬜ | Planned for Phase 9 admin portal; consent endpoint TBD |
| FR-AU-01 | Immutable, hash-chained audit trail | Phase 2.5 | ✅ | `decision_log` table (migration 0016); `DecisionLogService`; SHA-256 chain; `GET /audit/verify` |
| FR-AU-02 | Capture human override identity/reason/time | Phase 7 | 🟡 | `reviewer_role` captured on `HumanReview.decide()`; `HUMAN_OVERRIDE` decision_log entry deferred to Phase 9 |
| FR-AU-03 | Operational/compliance reports, exportable | Phase 2.5 | ✅ | `GET /cases/{id}/audit` (paginated, hash-visible); `GET /audit/export` (CSV+JSON) |
| FR-AU-04 | Adverse-action records on credit decline (ECOA) | Phase 4.6 | ✅ | `product_activation.is_adverse_action` + `adverse_action_reason`; `decision_log` entry with `is_regulatory_breach=True` |

---

## Non-Functional Requirements

| Req | Description | CADF Phase | Status | Artifact(s) |
|---|---|---|---|---|
| NFR-01 | Encryption + RBAC + least-privilege + secrets | Phase 7 | ✅ | `require_permission()` + 15-scope catalog; `domain_permissions` DB-backed; SPIFFE/Vault deferred to Phase 13 |
| NFR-02 | Crash recovery and workflow resumption | Phase 0.5 | ✅ | Temporal durable workflows; `OnboardingWorkflow` resumes from last activity checkpoint |
| NFR-03 | 99.95% availability; RTO ≤ 15 min; RPO ≈ 0 | Phase 13 | ⬜ | Helm dual-AZ topology; DR runbook |
| NFR-06 | Decisions explainable/reproducible from logs | Phase 2.5 | ✅ | `decision_log` captures inputs/rationale/agent version per decision; `GET /audit/verify` confirms chain integrity |
| NFR-07 | Idempotent, retryable integration calls | Phase 6 | 🟡 | `MCPRegistry.invoke()` routes through connector simulators; Temporal activity retries provide bounded retry at the workflow level |
| NFR-08 | US residency + BSA 5-yr retention | Phase 2.5, Phase 13 | 🟡 | `decision_log` WORM semantics enforced at app layer (`DecisionLogService` has no update/delete); `is_regulatory_breach` field; DB-role REVOKE documented in migration 0016; retention policy in Phase 13 |
| NFR-09 | WCAG 2.1 AA accessibility | Phase 10 | 🟡 | `useDomainConfig` hook serves vocabulary; Playwright + axe full-suite checks deferred to Phase 13 |
| NFR-10 | Centralized OTel/Prometheus/Grafana/Loki/Tempo | Phase 13 | ⬜ | OTel SDK; `docker-compose.observability.yml`; Helm subchart |

---

## Objectives

| OBJ | Metric | CADF Phase | Status |
|---|---|---|---|
| OBJ-1 | Time to first live product | Phase 4.6 | ✅ |
| OBJ-2 | True parallel onboarding (all products concurrent) | Phase 0.5, Phase 4 | 🟡 |
| OBJ-3 | Zero duplicate document requests | Phase 4.5 | ⬜ |
| OBJ-4 | Admin-configurable domain (no engineer redeploy) | Phase 9 | ✅ | All `domain_*` tables editable via admin portal; `DomainDefinitionLoader.load()` validates; activate/deactivate lifecycle; agent enable/disable toggle |
| OBJ-5 | SLA enforcement with audit trail | Phase 5, Phase 2.5 | ✅ | `SLAMonitorService`; `case_sla_tracking` (migration 0019); Temporal `_watch_sla` timer; `SLA_WARNING`/`SLA_BREACH` in `decision_log` (`is_regulatory_breach=True` on breach) |
| OBJ-6 | Explainable, tamper-evident audit trail | Phase 2.5 | ✅ | `decision_log` hash chain + `GET /audit/verify` tamper detection |

---

## Architecture Decision Records

| ADR | Decision | CADF Phase | Status | Artifact(s) |
|---|---|---|---|---|
| ADR-001 | Self-host Temporal for durable orchestration | Phase 0.5 | ✅ | `docker-compose.yml` Temporal service; `OnboardingWorkflow` |
| ADR-002 | Criteria-driven blackboard activation (no static graph) | Phase 3, Phase 4.6 | ✅ | `StageDispatcher` (Phase 3); `ActivationGateService` policy evaluation (Phase 4.6) |
| ADR-003 | Bespoke differentiators + OSS commodity | All phases | 🟡 | Monorepo + docker-compose |
| ADR-004 | Polyglot — Python/LangGraph agents (JVM deferred) | Phase 0.5 | ✅ | LangGraph `StateGraph` per agent; ADR-009 formalizes Python-first |
| ADR-005 | Dual-AZ active-active + DR | Phase 13 | ⬜ | Helm `values-prod.yaml`; DR runbook |
| ADR-006 | OPA activation gate; strong-consistency reads | Phase 4.6 | ✅ | `policies/activation.rego` (OPA bundle); `ActivationGateService._evaluate_policy` mirrors policy in-process; reads `OnboardingCase` from DB not LangGraph cache |
| ADR-007 | MCP gateway sole egress | Phase 6 | ✅ | `MCPRegistry.invoke()` grant-checks `domain_agent_tool_grants` before dispatch; fails closed on ungrant; `_simulate_identity_verification()` replaced by three `mcp_registry.invoke()` calls in `kyc_compliance/graph.py` |
| ADR-008 | Self-hosted/pluggable LLM | Existing | 🟡 | `LLMProviderFactory`; Anthropic/OpenAI/Google/local providers |
| ADR-009 | Temporal + LangGraph adoption (Python-first) | Phase 0.5 | ✅ | `docs/specs/ADR-009_temporal_langgraph_adoption.md` |
| ADR-010 | Single-tenant per deployment | Phase 0.5 | ✅ | `docs/specs/ADR-010_single_tenant_deployment.md` |

---

## Phase Completion Status

| Phase | Title | Status |
|---|---|---|
| Phase 0 | Audit & wire dead orchestrator config | ✅ |
| Phase 0.5 | Migrate to Temporal + LangGraph | ✅ |
| Phase 1 | DB-backed DomainDefinition model | ✅ |
| Phase 2 | Split OnboardingState into typed core + extension bag | ✅ |
| Phase 2.5 | Hash-chain audit log (FR-AU-01) | ✅ |
| Phase 3 | Config-driven StageDispatcher | ✅ |
| Phase 4 | Config-driven products + per-product agent pipelines | ✅ |
| Phase 4.5 | Shared-core document taxonomy (FR-DM-01/02/03) | ~ (skipped) |
| Phase 4.6 | First-to-complete activation gate (FR-GL-01/02/03) | ✅ |
| Phase 5 | Configurable SLA enforcement | ✅ |
| Phase 6 | Wire Skills & MCP into live execution | ✅ |
| Phase 7 | Configurable persona + permission model | ✅ |
| Phase 8 | Loosen DB CHECK constraints | ✅ |
| Phase 9 | Admin Portal | ✅ |
| Phase 10 | Serve frontend vocabulary from domain API | ✅ |
| Phase 11 | Retail/Deposit acceptance proof | ⬜ |
| Phase 12 | Extract framework/domain package boundary | ⬜ |
| Phase 13 | Observability, IaC & Operations | ⬜ |
