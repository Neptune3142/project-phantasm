"""Pytest fixtures for Project Phantasm.

Uses FastAPI's TestClient with an in-memory SQLite database for isolation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the app package is importable regardless of cwd.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Force a clean test environment before importing the app.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_phantasm.db")
os.environ.setdefault("SIMULATION_MODE", "true")
os.environ.setdefault("APP_ENV", "test")
os.environ.pop("GEMINI_API_KEY", None)

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    """Synchronous TestClient — uses httpx under the hood and runs the
    lifespan startup so the database is created automatically."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_db():
    """Each test starts with a clean slate — delete all rows from each table."""
    import asyncio
    from app.database import AsyncSessionLocal, engine
    from app.models import ApprovalRecord, SecurityIncident, UserAccount, WorkflowExecution
    from sqlalchemy import delete

    async def _wipe():
        async with AsyncSessionLocal() as s:
            await s.execute(delete(ApprovalRecord))
            await s.execute(delete(WorkflowExecution))
            await s.execute(delete(SecurityIncident))
            await s.execute(delete(UserAccount))
            await s.commit()

    asyncio.get_event_loop().run_until_complete(_wipe())
    yield
