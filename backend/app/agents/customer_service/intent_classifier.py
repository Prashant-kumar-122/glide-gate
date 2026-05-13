from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class Intent(StrEnum):
    PROVIDE_INFO = "provide_info"
    ASK_QUESTION = "ask_question"
    CONFIRM = "confirm"
    DECLINE = "decline"
    REQUEST_HELP = "request_help"
    IRRELEVANT = "irrelevant"


class ClassificationResult(BaseModel):
    intent: Intent
    confidence: float
    extracted_text: str
    field_hint: str | None = None


_CONFIRM_RE = re.compile(
    r"\b(yes|yeah|yep|correct|right|sure|ok|okay|confirmed|agree|that'?s?\s+(right|correct))\b",
    re.IGNORECASE,
)
_DECLINE_RE = re.compile(
    r"\b(no|nope|nah|not?\s+really|i\s+(don'?t|do\s+not)\s+(want|wish|have)|skip|refuse|n/a|none)\b",
    re.IGNORECASE,
)
_HELP_RE = re.compile(
    r"\b(help|what\s+do\s+you\s+mean|can\s+you\s+explain|i'?m?\s+(not\s+sure|confused|lost)|"
    r"how\s+do\s+i|what\s+is|clarif|don'?t\s+understand)\b",
    re.IGNORECASE,
)
_QUESTION_RE = re.compile(
    r"\?$|\b(what|why|how|when|where|who|can\s+you|could\s+you|would\s+you)\b",
    re.IGNORECASE,
)


class IntentClassifier:
    """
    Rule-based intent classifier — no LLM calls, runs in-process.

    Sufficient for structured data collection flows; a full LLM-based
    classifier is wired in STEP-24/26 via the Skills Framework.
    """

    def classify(
        self, message: str, context: dict[str, Any] | None = None
    ) -> ClassificationResult:
        stripped = message.strip()
        words = stripped.split()

        if _CONFIRM_RE.search(stripped) and len(words) <= 6:
            return ClassificationResult(
                intent=Intent.CONFIRM, confidence=0.90, extracted_text=stripped
            )

        if _DECLINE_RE.search(stripped) and len(words) <= 8:
            return ClassificationResult(
                intent=Intent.DECLINE, confidence=0.85, extracted_text=stripped
            )

        if _HELP_RE.search(stripped):
            return ClassificationResult(
                intent=Intent.REQUEST_HELP, confidence=0.80, extracted_text=stripped
            )

        if _QUESTION_RE.search(stripped):
            return ClassificationResult(
                intent=Intent.ASK_QUESTION, confidence=0.75, extracted_text=stripped
            )

        return ClassificationResult(
            intent=Intent.PROVIDE_INFO, confidence=0.70, extracted_text=stripped
        )
