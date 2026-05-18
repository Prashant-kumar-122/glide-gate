from app.database import Base

# Import all models so Alembic autogenerates the full migration
from app.models.admin_config import AdminConfig
from app.models.users import User
from app.models.clients import Client, ClientAddress, ClientProfile
from app.models.cases import CaseProduct, CaseProductStep, OnboardingCase, Product
from app.models.documents import Document
from app.models.kyc_reviews import HumanReview, KYCCheck
from app.models.agents import Agent, AgentTask, EventLog, MCPToolCall
from app.models.communications import (
    CaseSummary,
    CollaborationComment,
    CollaborationParticipant,
    CollaborationRoom,
    ConversationMessage,
    Notification,
)
from app.models.questionnaire import (
    OnboardingAnswer,
    OnboardingQuestion,
    OnboardingQuestionnaire,
    OnboardingQuestionRule,
    OnboardingQuestionSession,
)

__all__ = [
    "Base",
    # admin config
    "AdminConfig",
    # auth
    "User",
    # clients
    "Client",
    "ClientProfile",
    "ClientAddress",
    # cases
    "OnboardingCase",
    "Product",
    "CaseProduct",
    "CaseProductStep",
    # documents
    "Document",
    # kyc / reviews
    "KYCCheck",
    "HumanReview",
    # agents
    "Agent",
    "AgentTask",
    "EventLog",
    "MCPToolCall",
    # communications
    "Notification",
    "CaseSummary",
    "CollaborationRoom",
    "CollaborationParticipant",
    "CollaborationComment",
    "ConversationMessage",
    # questionnaire
    "OnboardingQuestionnaire",
    "OnboardingQuestion",
    "OnboardingQuestionRule",
    "OnboardingAnswer",
    "OnboardingQuestionSession",
]
