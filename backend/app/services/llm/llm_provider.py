from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Literal

from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    messages: list[LLMMessage]
    system_prompt: str = ""
    max_tokens: int = 512
    temperature: float = 0.3
    top_p: float = 0.95
    seed: int | None = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = False
    use_cache: bool = True  # Anthropic prompt caching


class LLMResponse(BaseModel):
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cached: bool = False


class LLMStreamChunk(BaseModel):
    token: str
    is_final: bool = False
    final_response: LLMResponse | None = None


class LLMProvider(ABC):
    provider_name: str = "base"
    default_model: str = ""

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]: ...

    @abstractmethod
    def is_available(self) -> bool: ...
