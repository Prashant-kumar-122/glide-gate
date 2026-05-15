from app.agents.skills.base_skill import BaseSkill
from app.agents.skills.clarification_skill import ClarificationSkill
from app.agents.skills.decision_reasoning_skill import DecisionReasoningSkill
from app.agents.skills.escalation_skill import EscalationSkill
from app.agents.skills.information_extraction_skill import InformationExtractionSkill
from app.agents.skills.product_suitability_skill import ProductSuitabilitySkill
from app.agents.skills.status_summarisation_skill import StatusSummarisationSkill

# Module-level singletons — import and share across agents
information_extraction = InformationExtractionSkill()
decision_reasoning = DecisionReasoningSkill()
status_summarisation = StatusSummarisationSkill()
clarification = ClarificationSkill()
escalation = EscalationSkill()
product_suitability = ProductSuitabilitySkill()

__all__ = [
    "BaseSkill",
    "InformationExtractionSkill",
    "DecisionReasoningSkill",
    "StatusSummarisationSkill",
    "ClarificationSkill",
    "EscalationSkill",
    "ProductSuitabilitySkill",
    # singletons
    "information_extraction",
    "decision_reasoning",
    "status_summarisation",
    "clarification",
    "escalation",
    "product_suitability",
]
