# ADR-010 — Single-Tenant Per Deployment

**Status:** Accepted  
**Date:** 2026-06-11  
**Deciders:** GlideGate Architecture Team  
**Related to:** ADR-009 (Temporal + LangGraph), Phase 11 (Retail/Deposit parallel deployment)

---

## Context

The CADF framework's generalization goal is to support multiple onboarding domains (Wealth
Management, Retail/Deposit, Loans, Mortgage, etc.) configured through an admin portal without
engineer code changes. The question is whether a single deployed instance should serve multiple
domains simultaneously (multi-tenant) or whether each domain is a separate deployment
(single-tenant per domain).

---

## Decision

**Each domain is a separate deployment. No runtime domain-switching within a single instance.**

A "deployment" is one running stack: one FastAPI process, one Temporal worker, one Postgres
schema (or database), one React frontend build. Each deployment is configured with exactly one
`domain_code` (e.g., `wealth_management`, `retail_deposit`).

The genericity of the framework is proven by standing up the Retail/Deposit domain as a parallel
deployment in Phase 11, configured entirely through the admin portal — not by changing code.

---

## Rationale

### Multi-tenant was rejected for the following reasons

1. **Security boundary complexity.** In a multi-tenant instance, a misconfigured permission
   check or a bug in the domain-routing middleware could expose one client's data to another
   domain's operators. Single-tenant eliminates the entire class of cross-domain data leakage
   bugs at the infrastructure level.

2. **Regulatory isolation.** Wealth management (FINRA, BSA), retail deposit (FDIC), and loan
   origination (ECOA, TILA) each carry distinct compliance obligations. Separate deployments
   enable separate audit trails, separate retention policies, and separate regulatory reporting
   — with no risk that one domain's audit log is contaminated by events from another.

3. **Temporal namespace isolation.** Temporal's multi-tenancy model uses namespaces. Sharing a
   Temporal cluster across domains requires namespace-aware routing in every workflow and
   activity. Single-tenant eliminates this complexity: the Temporal cluster serves one domain,
   and all workflow IDs are globally unique without domain-prefix disambiguation.

4. **Simpler admin portal.** A single-tenant admin portal has no concept of "which domain am I
   editing". Every configuration row belongs to the current deployment. Multi-tenant would
   require domain-scoping on every admin API endpoint, every DB query, and every UI screen.

5. **Failure isolation.** A Temporal worker crash or Postgres maintenance window in one domain
   does not affect any other domain. Deployments are independently scalable and independently
   restartable.

6. **Operational simplicity.** Each deployment is a standard Docker Compose stack (or Kubernetes
   Helm release). Adding a new domain is a new stack instantiation + admin portal configuration,
   not a code change or a schema migration on a shared database.

### What single-tenant does NOT mean

- It does not mean one deployment per client. All clients within a domain (e.g., all
  wealth-management clients) share one deployment.
- It does not mean the framework cannot run multiple deployments on the same physical host.
  Docker Compose namespacing (`.env`-driven) supports multiple stacks on one machine.
- It does not foreclose multi-tenancy in a future version. The `domain_*` DB tables (Phase 1)
  are designed with a `domain_id` FK on every domain-scoped table. If a future business case
  requires multi-tenancy (e.g., a SaaS offering), the schema is compatible; the routing layer
  would be added then.

---

## Consequences

**Positive:**
- Security: cross-domain data leakage is architecturally impossible.
- Compliance: each deployment has its own isolated audit trail and retention policy.
- Simplicity: no domain-routing logic anywhere in the codebase.
- Temporal: workflow IDs are globally unique without domain disambiguation.

**Negative / trade-offs:**
- Infrastructure overhead: each domain requires its own Postgres instance, Temporal cluster,
  and FastAPI process. For operators running many domains, this multiplies the managed resource
  count.
- Shared users: a user who has access to both Wealth Management and Retail/Deposit must
  authenticate to two separate deployments. Phase 7's configurable persona model should include
  SSO/IdP federation guidance to mitigate this.

---

## Proof of genericity (Phase 11)

The Retail/Deposit domain will be stood up as an independent deployment in Phase 11 with:
- All stage definitions, agent pipeline composition, and SLA windows configured through the
  admin portal (no code changes).
- A separate Postgres schema with only `retail_deposit`-specific reference data.
- A separate Temporal namespace (`retail-deposit`) on the same self-hosted Temporal cluster,
  or a separate cluster depending on isolation requirements at that time.

Successful Phase 11 completion is the acceptance criterion for this ADR.

---

## Related ADRs

- **ADR-009**: Temporal + LangGraph adoption — Temporal namespace-per-deployment follows from this decision.
- **ADR-001**: Self-hosted Temporal — single-tenant per deployment supports data-residency requirements.
