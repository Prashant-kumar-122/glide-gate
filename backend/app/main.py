from __future__ import annotations

import socketio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from app.config import settings
from app.api.error_handlers import register_error_handlers
from app.api.routers import health
from app.api.routers import auth
from app.api.routers import clients, cases, documents, conversations, reviews, agents, audit, notifications
from app.api.routers.admin import llm_config, validation_prompts, checkpoint_rules
from app.api.routers import demo
from app.api.routers import collaboration
from app.api.routers import sales_reviews
from app.api.routers import tasks
from app.api.routers import push
from app.websocket.socket_server import sio  # noqa: F401
from app.services.orchestration.agent_orchestration_service import orchestration_service

# FastAPI app
app = FastAPI(
    title="GlideGate CADF API",
    description="Client Agentic Development Framework — AI-powered wealth management onboarding",
    version="0.1.0",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
)

# CSRF double-submit protection — validates that requests carrying the auth cookie
# also carry a matching X-CSRF-Token header. Login/signup are exempt (no cookie yet).
_CSRF_EXEMPT = {"/api/auth/login", "/api/auth/signup", "/api/auth/logout"}
_CSRF_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def csrf_protection(request: Request, call_next):
    if (
        request.method in _CSRF_METHODS
        and request.url.path not in _CSRF_EXEMPT
        and settings.AUTH_COOKIE_NAME in request.cookies
    ):
        cookie_csrf = request.cookies.get(settings.CSRF_COOKIE_NAME)
        header_csrf = request.headers.get("X-CSRF-Token")
        if not cookie_csrf or not header_csrf or cookie_csrf != header_csrf:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid"},
            )
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # CSP: allow service worker and manifest; block unsafe inline/eval
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "   # unsafe-inline needed for Tailwind CSS-in-JS
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "connect-src 'self' ws: wss:; "
        "worker-src 'self'; "
        "manifest-src 'self'; "
        "frame-ancestors 'none'"
    )
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handlers
register_error_handlers(app)

# Routers
_prefix = settings.API_PREFIX

app.include_router(health.router, prefix=_prefix)
app.include_router(auth.router, prefix=_prefix)
app.include_router(clients.router, prefix=_prefix)
app.include_router(cases.router, prefix=_prefix)
app.include_router(documents.router, prefix=_prefix)
app.include_router(conversations.router, prefix=_prefix)
app.include_router(reviews.router, prefix=_prefix)
app.include_router(agents.router, prefix=_prefix)
app.include_router(audit.router, prefix=_prefix)
app.include_router(notifications.router, prefix=_prefix)
app.include_router(llm_config.router, prefix=_prefix)
app.include_router(validation_prompts.router, prefix=_prefix)
app.include_router(checkpoint_rules.router, prefix=_prefix)
app.include_router(demo.router, prefix=_prefix)
app.include_router(collaboration.router, prefix=_prefix)
app.include_router(sales_reviews.router, prefix=_prefix)
app.include_router(tasks.router, prefix=_prefix)
app.include_router(push.router, prefix=_prefix)

# Socket.IO ASGI mount
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


@app.on_event("startup")
async def on_startup() -> None:
    if settings.DEMO_MODE and settings.is_production:
        raise RuntimeError(
            "DEMO_MODE=True is not allowed in production. "
            "Set APP_ENV=development or set DEMO_MODE=False."
        )
    logger.info(
        f"GlideGate API starting — env={settings.APP_ENV} "
        f"demo_mode={settings.DEMO_MODE} "
        f"llm={settings.PRIMARY_LLM_PROVIDER}/{settings.PRIMARY_LLM_MODEL}"
    )
    from app.services.validation.prompt_override_store import (
        load_from_db as load_prompt_overrides,
    )
    from app.services.llm.deterministic_controls_applier import (
        load_from_db as load_llm_config,
    )
    from app.services.compliance.checkpoint_rule_repository import (
        load_from_db as load_checkpoint_rules,
    )
    await load_prompt_overrides()
    await load_llm_config()
    await load_checkpoint_rules()
    await orchestration_service.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await orchestration_service.stop()
    logger.info("GlideGate API shutting down")
