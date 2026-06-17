# activation.rego — Product activation gate policy (ADR-006 / FR-GL-01)
#
# This policy is evaluated in-process by ActivationGateService._evaluate_policy()
# (backend/app/services/activation/activation_gate_service.py).
#
# For production deployments requiring an external OPA server, deploy this file
# to the OPA bundle and replace the Python in-process call with:
#   POST http://opa:8181/v1/data/activation/allow
#   body: {"input": <activation_input>}
#
# Input schema (matches ActivationGateService.evaluate payload):
#   input.kyc_status          string  — "PASSED" | "FAILED" | "PENDING"
#   input.fraud_screened      string  — "CLEARED" | "FLAGGED" | "PENDING"
#   input.track_status        string  — "COMPLETE" | "FAILED" | "UNSUITABLE"
#   input.activation_criteria object  — per-product config from domain_products
#     .min_risk_level           string  — "low" | "medium" | "high" (optional)
#     .is_credit_product        bool    — true triggers ECOA adverse-action flag

package activation

default allow = false

# Allow activation when all hard gates pass
allow {
    input.track_status == "COMPLETE"
    input.kyc_status == "PASSED"
    not fraud_flagged
}

# Fraud gate: FLAGGED blocks activation regardless of KYC
fraud_flagged {
    input.fraud_screened == "FLAGGED"
}

# Optional risk-level gate (only evaluated when min_risk_level is set)
deny_reason["risk_level_below_minimum"] {
    input.activation_criteria.min_risk_level
    risk_rank[input.kyc_risk_band] < risk_rank[input.activation_criteria.min_risk_level]
}

deny_reason["kyc_not_passed"] {
    input.kyc_status != "PASSED"
}

deny_reason["fraud_flagged"] {
    fraud_flagged
}

deny_reason["pipeline_not_complete"] {
    input.track_status != "COMPLETE"
}

# Risk ordinal mapping
risk_rank := {
    "low":    1,
    "medium": 2,
    "high":   3,
}
