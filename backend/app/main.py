from __future__ import annotations

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.api.routers import health

# ── Socket.IO ─────────────────────────────────────────────────────────────────
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.SOCKETIO_CORS_ORIGINS,
    logger=False,
    engineio_logger=False,
)

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

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix=settings.API_PREFIX)

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


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("GlideGate API shutting down")
