from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from backend.config.settings import get_settings
from backend.database.database import Engine
from backend.core.retrieval.vector_store import VectorStore

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


async def check_postgres() -> dict[str, Any]:
    """Check PostgreSQL database connectivity."""
    try:
        async with Engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return {"status": "healthy", "error": None}
    except Exception as e:
        logger.error("PostgreSQL health check failed: %s", e)
        return {"status": "unhealthy", "error": str(e)}


async def check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        settings = get_settings()
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        await redis.close()
        return {"status": "healthy", "error": None}
    except Exception as e:
        logger.error("Redis health check failed: %s", e)
        return {"status": "unhealthy", "error": str(e)}


async def check_qdrant() -> dict[str, Any]:
    """Check Qdrant vector store connectivity."""
    try:
        store = VectorStore()
        client = await store._get_client()
        await client.get_collections()
        return {"status": "healthy", "error": None}
    except Exception as e:
        logger.error("Qdrant health check failed: %s", e)
        return {"status": "unhealthy", "error": str(e)}


@router.get("/")
async def health_check() -> dict[str, str]:
    """Simple health-check endpoint."""
    return {"status": "ok"}


@router.get("/detailed")
async def detailed_health_check() -> JSONResponse:
    """Comprehensive health check with dependency verification.

    Checks the status of all critical dependencies:
    - PostgreSQL database
    - Redis (for background jobs)
    - Qdrant (for vector storage)

    Returns:
        JSON response with detailed health status of each dependency.
    """
    settings = get_settings()

    # Check all dependencies concurrently
    postgres_status = await check_postgres()
    redis_status = await check_redis()
    qdrant_status = await check_qdrant()

    # Determine overall health
    all_healthy = (
        postgres_status["status"] == "healthy"
        and redis_status["status"] == "healthy"
        and qdrant_status["status"] == "healthy"
    )

    response = {
        "status": "healthy" if all_healthy else "degraded",
        "version": settings.version if hasattr(settings, "version") else "0.2.0",
        "dependencies": {
            "postgres": postgres_status,
            "redis": redis_status,
            "qdrant": qdrant_status,
        },
    }

    if not all_healthy:
        return JSONResponse(status_code=503, content=response)

    return JSONResponse(content=response)