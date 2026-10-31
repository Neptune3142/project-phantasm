"""Health check."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "service": "project-phantasm",
        "simulation_mode": s.simulation_mode,
        "version": "1.0.0",
    }
