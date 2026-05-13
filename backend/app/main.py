from __future__ import annotations

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.api.error_handlers import register_error_handlers
from app.api.routers import health
from app.api.routers import clients, cases, documents, conversations, reviews, agents, audit
from app.api.routers.admin import llm_config, validation_prompts
from app.websocket.socket_server import sio  # noqa: F401 — imported for side-effect (event registration)
from app.services.orchestration.agent_orchestration_service import orchestration_service

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="GlideGate CADF API",
    description="Client Agentic Development Framework — AI-powered wealth management onboarding",
    version="0.1.0",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error handlers ────────────────────────────────────────────────────────────
register_error_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────────────
_prefix = settings.API_PREFIX

app.include_router(health.router, prefix=_prefix)
app.include_router(clients.router, prefix=_prefix)
app.include_router(cases.router, prefix=_prefix)
app.include_router(documents.router, prefix=_prefix)
app.include_router(conversations.router, prefix=_prefix)
app.include_router(reviews.router, prefix=_prefix)
app.include_router(agents.router, prefix=_prefix)
app.include_router(audit.router, prefix=_prefix)
app.include_router(llm_config.router, prefix=_prefix)
app.include_router(validation_prompts.router, prefix=_prefix)

# ── Socket.IO ASGI mount ──────────────────────────────────────────────────────
# Mount socket.io at /ws so the FastAPI routes remain at /api/*
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        f"GlideGate API starting — env={settings.APP_ENV} "
        f"demo_mode={settings.DEMO_MODE} "
        f"llm={settings.PRIMARY_LLM_PROVIDER}/{settings.PRIMARY_LLM_MODEL}"
    )
    await orchestration_service.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await orchestration_service.stop()
    logger.info("GlideGate API shutting down")
