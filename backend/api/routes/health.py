from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
async def health_check() -> dict[str, str]:
    """Simple health-check endpoint."""
    return {"status": "ok"}