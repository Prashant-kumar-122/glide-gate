# AI-DLC Execution Playbook
## Agentic Multi-Product Client Onboarding Platform

**Purpose:** Drive the full **AI-Driven Development Lifecycle (AI-DLC)** — Inception → Construction → Operations — for the onboarding platform, using the **BRD**, **Technical Architecture (with diagrams)**, and **Architecture Decision Records (ADRs)** as the authoritative, persistent context.

**Companion to:** BRD v1.0 · Technical Architecture v1.0 · Architecture Decision Records v1.0
**Version:** 1.0 (Draft) · June 2026

---

## How to use this playbook

1. **Attach the three source documents** (BRD, Technical Architecture, ADRs) to your AI coding agent / IDE assistant.
2. **Run the Master Prompt once** to establish context and working agreements. Let the agent surface its gap list before proceeding — that list is where the real value is.
3. **Run each phase prompt in sequence** (Inception → Construction → Operations), validating each stage/unit before moving on. This human-in-the-loop validation is the core of AI-DLC ("mob elaboration" in Inception, "mob construction" in Construction).
4. **Treat the ADRs as a fence:** the agent must propose a *new* ADR rather than silently deviating from an existing decision.
5. *(Optional)* If your tool supports steering rules, drop in AWS's open `awslabs/aidlc-workflows` alongside these prompts.

> **Tip:** Keep the loop tight. Validate each stage/unit before the next; resist letting the agent run multiple phases unsupervised.

---

## Project context (quick reference for every prompt)

- **What:** Agentic, multi-product onboarding across **Retail/Deposit, Loans, Wealth/Mortgage**, run **in parallel**, with **first-to-complete go-live**.
- **How agents work:** On-the-fly onboarding via a **declarative registry** + **criteria-driven blackboard activation** (no static central graph). Shared-core documents collected once, reused many times.
- **Build posture:** Fully **in-house, self-hosted** — hybrid **on-prem core + private-cloud Kubernetes**.
- **Stack:** JVM/Spring Boot core · Python/LangGraph agents · Temporal · Kafka · PostgreSQL · Redis · MinIO · pgvector · OPA · MCP gateway · Keycloak/SPIFFE/SPIRE · Vault · Kubernetes/OpenShift + Istio · OpenTelemetry/Prometheus/Grafana/Loki/Tempo · self-hosted model gateway.
- **Compliance (US):** BSA/FinCEN, CIP, CDD/beneficial ownership, OFAC, GLBA, FCRA, ECOA, TRID, SEC/FINRA, CCPA. US data residency; BSA 5-year/WORM retention.
- **Targets:** 99.95% availability (dual-AZ active-active), RTO ≤ 15 min, RPO ≈ 0 for critical state.

---

## 0. Master Prompt (set up once)

> You are the AI engineering lead running the **AI-Driven Development Lifecycle (AI-DLC)** for an in-house banking platform. We will work through three phases — **Inception, Construction, Operations** — using human-in-the-loop validation ("mob elaboration" in Inception, "mob construction" in Construction). You propose; I and the team validate before anything is finalized.
>
> **Authoritative context (your single source of truth — do not contradict these; ingest them fully before acting):**
> 1. **BRD** — business requirements, scope, document matrix, workflow comparison, compliance obligations, acceptance criteria, roadmap.
> 2. **Technical Architecture** — component design, criteria-driven blackboard activation, data/consistency model, scalability, resilience/DR, security, the reference stack, and Figures 1–3 (component, sequence, deployment).
> 3. **Architecture Decision Records (ADR-001…008)** — the binding technical decisions and their rationale.
>
> **Project facts you must honor:** agentic, multi-product onboarding (Retail/Deposit, Loans, Wealth/Mortgage) with parallel journeys and first-to-complete go-live; on-the-fly agent onboarding via a declarative registry + criteria-driven blackboard; fully **in-house, self-hosted** (hybrid on-prem core + private-cloud Kubernetes); polyglot stack (JVM/Spring Boot core, Python/LangGraph agents, Temporal, Kafka, PostgreSQL, Redis, MinIO, OPA, MCP gateway, Keycloak/SPIFFE, Vault); US regulatory regime (BSA/FinCEN, CIP, CDD, OFAC, GLBA, FCRA, ECOA, TRID, SEC/FINRA, CCPA).
>
> **Working agreements (apply in every phase):**
> - **ADR conformance:** never silently deviate from an ADR. If you believe a decision should change, stop and propose a new ADR (Context/Decision/Consequences/Alternatives) for approval.
> - **Traceability:** tie every requirement, story, design element, and test back to BRD requirement IDs (FR-xx, NFR-xx, OBJ-x). Maintain a living traceability matrix.
> - **Human checkpoints:** at the end of each stage, present your output and your open questions, then **wait for my validation** before proceeding. Surface assumptions explicitly; ask rather than guess.
> - **Persistent context:** carry decisions and artifacts forward across phases; keep a running decision log.
> - **Compliance-by-design:** for any feature touching KYC/CDD/OFAC/credit/disclosures, state which regulation applies and how the design satisfies and evidences it.
> - **Definition of Done:** code is accompanied by tests, security checks, observability hooks, and traceability links; nothing is "done" otherwise.
>
> Confirm you've ingested all three documents, then summarize the system in your own words and list the top 10 ambiguities or gaps you need clarified before Inception. Do not start designing yet.

---

## 1. Inception Phase Prompt

> Begin the **Inception** phase. Using the BRD, Architecture, and ADRs as context, work through these stages, pausing for my validation (mob elaboration) after each:
> 1. **Reverse-engineering & scope confirmation** — restate the domain, bounded contexts, products, and the shared-core vs. product-specific model.
> 2. **Requirements analysis** — decompose the BRD into atomic, testable requirements mapped to FR/NFR/OBJ IDs; flag conflicts or gaps.
> 3. **User stories** — write stories with acceptance criteria (Given/When/Then) for each persona (client, RM, ops, compliance, credit, risk), grouped by capability.
> 4. **Units of work** — slice stories into independently buildable units sized for short iterations ("bolts"), with dependencies and sequencing aligned to the BRD roadmap phases.
> 5. **Workflow & application design** — confirm the per-product workflows, the criteria-driven activation model, and the declarative agent definition contract; identify the first end-to-end vertical slice to build (recommend Retail/Deposit happy path with shared-core reuse).
>
> Deliver: a requirements catalog, a story backlog with acceptance criteria, a unit-of-work plan with sequencing, and an updated traceability matrix. End with open questions for me.

**Exit criteria:** Validated requirements catalog, story backlog, sequenced unit-of-work plan, traceability matrix, and an agreed first vertical slice.

---

## 2. Construction Phase Prompt

> Begin the **Construction** phase for the unit(s) of work I approve. For each unit, proceed and pause for validation (mob construction) at the design checkpoint before writing code:
> 1. **Logical design & domain model** — propose the domain model, APIs/contracts, data schemas (blackboard entities, event schemas), and agent definitions, strictly conforming to the ADRs and Figures 1–3. Call out any ADR tension as a proposed new ADR.
> 2. **Implementation plan** — list files/modules/services to create, the tech per component (JVM/Spring for core, Python/LangGraph for agents, Temporal workflows, Kafka topics, OPA policies, MCP servers), and how this slice runs end to end.
> 3. **Code** — implement the unit with production-quality, idempotent, observable code; wire authentication (SPIFFE/mTLS), secrets (Vault), and the MCP gateway boundary; no direct integration calls.
> 4. **Tests** — unit, integration, and contract tests, plus compliance assertions (e.g., no activation before all checks pass; shared-core doc reused, not re-requested). Include a runnable end-to-end test of the vertical slice.
> 5. **Review** — produce a self-review against the ADRs, the Definition of Done, and the traceability matrix; list residual risks.
>
> Deliver code + tests + design notes + updated traceability, and a short changelog per unit. Stop after each unit for my review before the next.

**Exit criteria:** Approved code + tests per unit, design notes, updated traceability, passing end-to-end vertical slice, self-review against ADRs and Definition of Done.

---

## 3. Operations Phase Prompt

> Begin the **Operations** phase. Translate the deployed architecture (Figure 3: hybrid, dual-AZ active-active, on-prem zone, active-passive DR) into operational reality:
> 1. **Infrastructure as Code** — Terraform for infra and Helm/Kustomize for workloads on Kubernetes/OpenShift; Argo CD GitOps; environment promotion dev→test→sandbox→staging→prod.
> 2. **CI/CD** — pipelines with automated tests, SAST/dependency scanning, image signing, and progressive rollout.
> 3. **Observability & SLOs** — OpenTelemetry instrumentation; Prometheus/Grafana/Loki/Tempo dashboards; error-budget SLOs from the NFR targets (99.95%, p95 latency, throughput); alerting and runbooks.
> 4. **Resilience operations** — backup, replication validation, and DR failover drills against RTO ≤ 15 min / RPO ≈ 0.
> 5. **Compliance operations** — audit-log integrity checks, retention enforcement (BSA 5-year/WORM), and access reviews.
>
> Deliver IaC, pipeline definitions, observability config, runbooks, and a go-live readiness checklist mapped to the NFRs. Flag anything requiring human approval before production.

**Exit criteria:** IaC, CI/CD pipelines, observability/SLO config, DR-tested runbooks, and a signed-off go-live readiness checklist mapped to the NFRs.

---

## Cross-phase guardrails (keep visible throughout)

| Guardrail | Rule |
|---|---|
| ADR conformance | Never deviate silently — propose a new ADR for any change. |
| Traceability | Every artifact links to a BRD ID (FR/NFR/OBJ). |
| Human checkpoints | Validate each stage/unit before proceeding. |
| Compliance-by-design | Name the regulation and how it's satisfied + evidenced. |
| MCP boundary | Agents never call integrations directly — only via the gateway. |
| Activation gating | No product activates before all its checks pass (reads strong-consistency store). |
| Definition of Done | Code + tests + security + observability + traceability, or it isn't done. |

---

## References

- AI-Driven Development Life Cycle — AWS DevOps Blog: https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle/
- AWS AI-DLC workflow steering rules for AI coding agents: https://github.com/awslabs/aidlc-workflows
