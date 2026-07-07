from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.settings import get_settings
from backend.database.database import Engine
from backend.database.models import Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:  # noqa: ANN401
    """Application lifecycle: create tables on startup, dispose engine on shutdown."""
    settings = get_settings()
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
    app = FastAPI(
        title="RepoMind API",
        description="Agentic Code Intelligence Platform — Backend API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── CORS (allow any origin for now; will be locked down later) ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register routers ──────────────────────────────────────────
    from backend.api.routes.agent import router as agent_router
    from backend.api.routes.crag import router as crag_router
    from backend.api.routes.git import router as git_router
    from backend.api.routes.github import router as github_router
    from backend.api.routes.graphrag import router as graphrag_router
    from backend.api.routes.health import router as health_router
    from backend.api.routes.indexing import router as indexing_router
    from backend.api.routes.parser import router as parser_router
    from backend.api.routes.relationships import router as relationships_router
    from backend.api.routes.repositories import router as repo_router

    app.include_router(health_router)
    app.include_router(repo_router)
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