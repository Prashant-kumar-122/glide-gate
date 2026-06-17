# ADR-009 — Temporal + LangGraph Adoption

**Status:** Accepted  
**Date:** 2026-06-11  
**Deciders:** GlideGate Architecture Team  
**Supersedes:** Implicit asyncio/AgentEventBus design (no prior ADR)  
**Conforms to:** ADR-001 (self-hosted Temporal), ADR-004 (LangGraph Python agents)

---

## Context

GlideGate's original orchestration substrate was a custom asyncio event loop:
`AgentOrchestrationService` spawned `BaseAgent` subclasses registered on `AgentEventBus`, which
passed `TaskPacket` messages between agents over an `asyncio.Queue`. Stage transitions were
dispatched via an `OrchestratorAgent` ~150-line `if/elif` chain.

**Problems with the asyncio substrate:**

1. **No crash recovery.** A process restart lost all in-flight workflow state. Multi-day
   onboarding cases (7-day INTAKE window, 90-day ESCALATION window) required manual re-entry.
2. **No workflow visibility.** There was no UI to see which stage a given case was in at the
   infrastructure level; only the DB `current_stage` column was observable.
3. **No durable retry.** Transient failures (network, LLM timeout) silently dropped tasks.
4. **No parallel execution visibility.** `asyncio.gather` for parallel product onboarding had
   no per-product isolation; a single product failure aborted all parallel tracks.
5. **ADR non-compliance.** The spec docs (ADR-001, ADR-004) mandated Temporal and LangGraph.
   The asyncio implementation was a temporary placeholder that was never replaced.

---

## Decision

**Adopt self-hosted Temporal (`temporalio` SDK ≥ 1.7) as the orchestration substrate and
LangGraph (`langgraph` ≥ 0.2) as the per-agent execution graph framework.**

### Temporal role

`OnboardingWorkflow` (`@workflow.defn`) replaces `OrchestratorAgent`:
- Each stage transition is a Temporal Activity, persisted to the Temporal history log.
- Stage advancement (client submit, advisor approve, KYC complete) are Temporal Signals
  (`advance_stage`, `human_review_completed`) — durable, survive worker restarts.
- Parallel per-product execution runs as child workflows (`ProductOnboardingWorkflow`), one per
  product code, with deterministic IDs (`onboarding-{case_id}-product-{product_code}`).
- Long-wait stages (INTAKE: 7-day timeout, ESCALATED: 90-day timeout) use
  `workflow.wait_condition()` — no polling, no cron, no DB state machine.

### LangGraph role

Each `BaseAgent` subclass has a `graph.py` that wraps its reasoning logic as a LangGraph
`StateGraph[OnboardingStateDict]`:
- Nodes are the individual reasoning steps (identity verification, risk scoring, document
  classification, etc.) previously buried in private `_handle_*` methods.
- `OnboardingStateDict` (a `TypedDict` mirroring `OnboardingState`) is the shared blackboard
  passed through every node.
- Graphs are invoked from Temporal Activities via `await graph.ainvoke(state)`.
- Agent internal control flow (conditional routing within a single agent's reasoning) uses
  LangGraph's `add_conditional_edges` rather than nested if/elif.

### Backward-compatibility

`AgentEventBus` is preserved for direct per-request agent calls (document intelligence,
notification dispatch). The `AgentOrchestrationService.publish_task()` method routes
stage-advancing task types to Temporal Signals and all other tasks to the legacy bus.
A graceful fallback to the legacy bus is triggered if `temporalio.client.Client.connect()` fails,
enabling tests and local dev without a running Temporal server.

---

## Rationale

| Criterion | asyncio AgentEventBus | Temporal + LangGraph |
|---|---|---|
| Crash recovery | None — state lost on restart | Full — Temporal history is the source of truth |
| Retry / timeout | Manual, per-call | Declarative `retry_policy`, `schedule_to_close_timeout` |
| Parallel products | `asyncio.gather` — single process | Child workflows — independently retryable |
| Long waits (7 d, 90 d) | Polling loop or cron | `wait_condition` with timeout — zero overhead |
| Observability | DB column only | Temporal Web UI shows per-workflow execution history |
| BSA / compliance audit | Separate `EventLog` table | Temporal event history + `EventLog` |
| Agent reasoning visibility | Invisible inside `process()` | LangGraph node-by-node execution trace |

### Self-hosted vs Temporal Cloud

Temporal Cloud was evaluated and rejected for three reasons:
1. **Data residency.** BSA/FINRA compliance requires all client PII to remain within the
   operator's infrastructure boundary. Temporal Cloud sends workflow input/output off-premises.
2. **Cost.** At GlideGate's projected case volume (~1,000 concurrent onboardings), Temporal Cloud
   pricing exceeds self-hosted infrastructure cost within 6 months.
3. **Consistency with existing Docker Compose stack.** The Temporal `auto-setup` image runs
   co-located with the existing Postgres container, requiring no additional managed services.

### Python-first; JVM deferred

ADR-004 originally referenced a JVM/Spring Boot core. This is deferred. The Python
`temporalio` SDK is feature-complete and provides the same workflow guarantees as the Java SDK.
A JVM core will only be introduced if a business case arises that Python cannot satisfy
(e.g., a polyglot micro-service with existing Java codebase, or a Java-native LLM provider SDK).

---

## Consequences

**Positive:**
- Workflow crash recovery verified: kill the worker mid-workflow, restart → resumes from last
  Temporal checkpoint (no DB patching required).
- Per-product parallelism is now visible in Temporal Web UI as child workflow executions.
- Long-wait stages (ESCALATED, INTAKE) consume zero polling resources.
- Each agent's reasoning steps are individually visible as LangGraph node outputs.

**Negative / trade-offs:**
- Temporal adds operational complexity: the `auto-setup` image, Temporal UI, and worker process
  must be healthy for onboarding to proceed. Legacy fallback mitigates dev/test impact.
- `OnboardingStateDict` uses `str` for UUIDs and datetimes (Temporal payload serialization
  constraint) — callers must convert when interacting with SQLAlchemy models.
- LangGraph `ainvoke` adds ~1–2 ms per agent invocation vs a direct `agent.process()` call.
  This is acceptable given that each invocation involves at least one LLM API call (~200–800 ms).

---

## Affected files

| File | Change |
|---|---|
| `backend/app/workflows/onboarding_workflow.py` | New — Temporal workflow + all activities |
| `backend/app/agents/*/graph.py` | New — LangGraph graph per agent (8 files) |
| `backend/app/services/orchestration/agent_orchestration_service.py` | Rewritten — Temporal worker startup + signal routing |
| `backend/app/agents/base/a2a_types.py` | Added `OnboardingStateDict`, signal models |
| `backend/app/api/routers/cases.py` | Added `signal_stage_advance` calls at stage transition points |
| `backend/pyproject.toml` | Added `temporalio`, `langgraph`, `langchain-core` |
| `docker-compose.yml` | Added `temporal` and `temporal-ui` services |

---

## Related ADRs

- **ADR-001**: Temporal self-hosted orchestration — this ADR implements it.
- **ADR-004**: LangGraph Python agents — this ADR implements it.
- **ADR-010**: Single-tenant deployment model — constrains how Temporal namespaces are used.
- **ADR-002**: Criteria-driven activation (OPA) — Phase 4.6 will add an OPA activity node.
- **ADR-007**: MCP gateway sole egress — Phase 6 will replace direct agent calls with MCP activities.
