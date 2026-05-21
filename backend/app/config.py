from __future__ import annotations

import json
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/glide_gate"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/glide_gate"

    # ── AI Providers ─────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    LOCAL_MODEL_ENDPOINT: str = "http://localhost:11434/v1"
    LOCAL_MODEL_NAME: str = "qwen2.5vl:7b"
    VISION_MODEL_NAME: str = "qwen2.5vl:7b"

    # ── Primary LLM Config ───────────────────────────────────────────────────
    PRIMARY_LLM_PROVIDER: Literal["anthropic", "openai", "google", "local"] = "local"
    PRIMARY_LLM_MODEL: str = "qwen2.5vl:7b"
    LLM_TEMPERATURE: float = 0.3
    LLM_TOP_P: float = 0.95
    LLM_SEED: int = 42
    LLM_FREQUENCY_PENALTY: float = 0.0
    LLM_PRESENCE_PENALTY: float = 0.0
    LLM_MAX_TOKENS: int = 4096
    LLM_CACHE_TTL: int = 300
    LLM_MAX_RETRIES: int = 3

    # ── JWT / Auth ────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ── App ───────────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api"

    # ── Demo Mode ─────────────────────────────────────────────────────────────
    DEMO_MODE: bool = False

    # ── Document Storage ─────────────────────────────────────────────────────
    DOCUMENT_STORAGE_BACKEND: Literal["local", "s3"] = "local"
    DOCUMENT_STORAGE_PATH: str = "./uploads"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-southeast-1"
    S3_BUCKET_NAME: str = "glide-gate-docs"

    # ── WebSocket ─────────────────────────────────────────────────────────────
    SOCKETIO_CORS_ORIGINS: str = "http://localhost:5173"

    # ── MCP Connectors ────────────────────────────────────────────────────────
    MCP_IDENTITY_VERIFICATION_URL: str = ""
    MCP_DOCUMENT_MANAGEMENT_URL: str = ""
    MCP_SIMULATED_LATENCY_MIN_MS: int = 100
    MCP_SIMULATED_LATENCY_MAX_MS: int = 800

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
