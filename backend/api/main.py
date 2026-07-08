from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.config.settings import get_settings
from backend.core.logging.logger import configure_logging
from backend.core.logging.middleware import ObservabilityMiddleware
from backend.database.database import Engine
from backend.database.models import Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:  # noqa: ANN401
    """Application lifecycle: create tables on startup, dispose engine on shutdown."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Starting RepoMind API (debug=%s)…", settings.debug)

    # Create all database tables.
    async with Engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Clean shutdown.
    await Engine.dispose()
    logger.info("RepoMind API shut down.")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="RepoMind API",
        description="Agentic Code Intelligence Platform — Backend API. "
        "Supports Ollama, Gemini, and OpenAI providers with PostgreSQL, "
        "background jobs, JWT authentication, streaming, and observability.",
        version="0.2.0",
        lifespan=lifespan,
    )

    # ── Observability middleware ──────────────────────────────
    app.add_middleware(ObservabilityMiddleware)

    # ── CORS ──────────────────────────────────────────────────
    # Get allowed origins from environment, default to empty list (no CORS) in production
    # For development, you can set CORS_ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8000"
    cors_allowed_origins = settings.cors_allowed_origins
    if cors_allowed_origins:
        # Parse comma-separated origins
        allow_origins = [origin.strip() for origin in cors_allowed_origins.split(",")]
    else:
        # In production, require explicit CORS configuration
        allow_origins = []

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-Request-ID"],
    )

    # ── Rate Limiting ─────────────────────────────────────────
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_requests}/{settings.rate_limit_window_minutes}minute"],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Register routers ──────────────────────────────────────
    from backend.api.routes.agent import router as agent_router
    from backend.api.routes.auth import router as auth_router
    from backend.api.routes.crag import router as crag_router
    from backend.api.routes.git import router as git_router
    from backend.api.routes.github import router as github_router
    from backend.api.routes.graphrag import router as graphrag_router
    from backend.api.routes.health import router as health_router
    from backend.api.routes.imports import router as import_router
    from backend.api.routes.indexing import router as indexing_router
    from backend.api.routes.jobs import router as jobs_router
    from backend.api.routes.parser import router as parser_router
    from backend.api.routes.relationships import router as relationships_router
    from backend.api.routes.repositories import router as repo_router

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(jobs_router)
    app.include_router(repo_router)
    app.include_router(import_router)
    app.include_router(parser_router)
    app.include_router(relationships_router)
    app.include_router(indexing_router)
    app.include_router(git_router)
    app.include_router(github_router)
    app.include_router(agent_router)
    app.include_router(graphrag_router)
    app.include_router(crag_router)

    return app


app = create_app()