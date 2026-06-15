"""Config-driven StageDispatcher (Phase 3).

Replaces the hardcoded if/elif stage-routing chain previously in
orchestrator_agent.py and the equivalent stage-dispatch logic in
onboarding_workflow.py.  Given a stage_code and the routing data from a
DomainDefinition, the dispatcher returns the Temporal activity name to invoke.

Design note: StageDispatcher intentionally works with plain dicts internally
(not with DomainDefinition Pydantic objects) so that OnboardingWorkflow can
construct a dispatcher from the raw dict returned by load_domain_definition_activity
without importing any SQLAlchemy-laden module inside the Temporal sandbox.
Use from_domain_def() in test code; use from_domain_dict() in workflow code.

Also contains SLAHook — a no-op stub called on every stage transition in
Phase 3.  Phase 5 activates the real implementation by writing to the
case_sla_tracking table introduced by that migration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from app.agents.base.a2a_types import OnboardingStateDict

if TYPE_CHECKING:
    from app.domain.domain_definition import DomainDefinition


# ── Activity registry ──────────────────────────────────────────────────────────
# Maps task_type values (from domain_task_routing rows) to Temporal activity
# name strings.  The names match the name= argument on each @activity.defn in
# onboarding_workflow.py.  To add a new task type (e.g. in Phase 5 or 6),
# add one row here — no workflow code changes required.

_TASK_TYPE_TO_ACTIVITY_NAME: dict[str, str] = {
    "collect_client_data":       "customer_service_kickoff_activity",
    "create_collaboration_room": "collaboration_kickoff_activity",
    "sales_manager_review":      "sales_manager_kickoff_activity",
    "run_kyc_check":             "kyc_compliance_activity",
    "onboard_product":           "product_onboarding_activity",
    "send_notification":         "notification_activity",
    "send_escalation_alert":     "escalation_alert_activity",
}


# ── Dispatch result ────────────────────────────────────────────────────────────


@dataclass
class StageDispatch:
    """Resolved dispatch specification returned by StageDispatcher.resolve().

    activity_name is the Temporal @activity.defn name string, which is looked
    up in onboarding_workflow._ACTIVITY_LOOKUP to get the callable reference.

    action_spec is a SimpleNamespace providing attribute access to the routing
    row fields: .task_type, .target_agent, .priority, .payload_template,
    .notification_templates.  Tests can access these directly.

    resolved_payload carries template-substituted values ready for use by the
    calling activity.
    """

    stage_code: str
    action_spec: Any  # SimpleNamespace: .task_type, .target_agent, .priority
    activity_name: str
    resolved_payload: dict[str, Any] = field(default_factory=dict)


# ── Dispatcher ─────────────────────────────────────────────────────────────────


class StageDispatcher:
    """Maps domain stage_code → Temporal activity dispatch spec.

    Internally stores task_routing and stages as plain dicts so it can be
    constructed from the raw dict returned by load_domain_definition_activity
    inside the Temporal workflow sandbox (where SQLAlchemy imports are
    restricted).

    Construction:
      - In workflow code:  StageDispatcher.from_domain_dict(domain_dict)
      - In test/non-sandbox code: StageDispatcher.from_domain_def(domain_def)
    """

    def __init__(
        self,
        task_routing: dict[str, dict[str, Any]],
        stages: dict[str, dict[str, Any]],
    ) -> None:
        # stage_code → {task_type, target_agent, priority, payload_template, ...}
        self._task_routing = task_routing
        # stage_code → {is_human_pending, is_terminal}
        self._stages = stages

    # ── Constructors ──────────────────────────────────────────────────────────

    @classmethod
    def from_domain_def(cls, domain_def: "DomainDefinition") -> "StageDispatcher":
        """Construct from a loaded DomainDefinition.  Use in tests and non-sandbox code."""
        return cls(
            task_routing={
                code: {
                    "stage_code":             spec.stage_code,
                    "target_agent":           spec.target_agent,
                    "task_type":              spec.task_type,
                    "priority":               spec.priority,
                    "payload_template":       spec.payload_template,
                    "notification_templates": spec.notification_templates,
                }
                for code, spec in domain_def.task_routing.items()
            },
            stages={
                code: {
                    "stage_code":        spec.stage_code,
                    "is_human_pending":  spec.is_human_pending,
                    "is_terminal":       spec.is_terminal,
                }
                for code, spec in domain_def.stages.items()
            },
        )

    @classmethod
    def from_domain_dict(cls, data: dict[str, Any]) -> "StageDispatcher":
        """Construct from the raw dict returned by load_domain_definition_activity.

        Uses this constructor inside OnboardingWorkflow.run() to avoid importing
        domain_definition.py (which brings in SQLAlchemy) inside the sandbox.
        The dict structure matches DomainDefinition.model_dump() output.
        """
        # task_routing is stored as dict[stage_code → StageActionSpec-dict] in model_dump()
        raw_routing = data.get("task_routing", {})
        raw_stages = data.get("stages", {})
        return cls(task_routing=raw_routing, stages=raw_stages)

    # ── Resolution ────────────────────────────────────────────────────────────

    def resolve(
        self, stage_code: str, state: OnboardingStateDict
    ) -> StageDispatch | None:
        """Return the StageDispatch for the given stage, or None if not routable.

        None is returned for stages with no task_routing entry.  Callers must
        handle None and fall back to their hardcoded activity reference.
        """
        spec_dict = self._task_routing.get(stage_code)
        if spec_dict is None:
            return None
        task_type = spec_dict.get("task_type", "")
        activity_name = _TASK_TYPE_TO_ACTIVITY_NAME.get(task_type)
        if activity_name is None:
            return None
        action_spec = SimpleNamespace(
            stage_code=stage_code,
            target_agent=spec_dict.get("target_agent", ""),
            task_type=task_type,
            priority=spec_dict.get("priority", "NORMAL"),
            payload_template=spec_dict.get("payload_template", {}),
            notification_templates=spec_dict.get("notification_templates", {}),
        )
        return StageDispatch(
            stage_code=stage_code,
            action_spec=action_spec,
            activity_name=activity_name,
            resolved_payload=_resolve_payload_template(
                spec_dict.get("payload_template", {}), state
            ),
        )

    def is_human_pending(self, stage_code: str) -> bool:
        """True if the domain marks this stage as requiring a human signal."""
        spec_dict = self._stages.get(stage_code)
        return bool(spec_dict.get("is_human_pending", False)) if spec_dict else False

    def is_terminal(self, stage_code: str) -> bool:
        """True if the domain marks this stage as a terminal state."""
        spec_dict = self._stages.get(stage_code)
        return bool(spec_dict.get("is_terminal", False)) if spec_dict else False


# ── Payload template resolver ──────────────────────────────────────────────────


def _resolve_payload_template(
    template: dict[str, Any], state: OnboardingStateDict
) -> dict[str, Any]:
    """Substitute {placeholder} strings in a payload_template from state values.

    Supported placeholders: case_id, client_id, products, stage, priority_tier.
    Non-string values are passed through unchanged.  Unrecognised placeholders
    are left as-is rather than raising a KeyError.
    """
    if not template:
        return {}
    ctx: dict[str, Any] = {
        "case_id":       state.get("case_id", ""),
        "client_id":     state.get("client_id", ""),
        "products":      state.get("selected_products", []),
        "stage":         state.get("stage", ""),
        "priority_tier": state.get("priority_tier", "standard"),
    }
    result: dict[str, Any] = {}
    for key, val in template.items():
        if isinstance(val, str):
            try:
                result[key] = val.format(**ctx)
            except (KeyError, ValueError):
                result[key] = val
        else:
            result[key] = val
    return result


# ── SLA hook stub ──────────────────────────────────────────────────────────────


class SLAHook:
    """SLA integration point called synchronously on every stage transition.

    Phase 3: guaranteed no-op stub.

    Phase 5 activates the real implementation: it will write a row to the
    case_sla_tracking table (created by the Phase 5 migration) and start a
    Temporal Timer for the SLA window.  At that point the call site in each
    _handle_* method of OnboardingWorkflow will be replaced by a Temporal
    activity call so that the DB write is durable and crash-safe.

    The stub is safe to call even when case_sla_tracking does not exist.
    """

    @staticmethod
    def on_stage_entered(
        case_id: str,
        stage_code: str,
        domain_def: "DomainDefinition | None",
    ) -> None:
        """Called before each stage's primary activity runs. No-op until Phase 5."""
