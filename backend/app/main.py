"""Project Phantasm — FastAPI application factory."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routes import ROUTERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("phantasm.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting Project Phantasm — simulation_mode=%s", settings.simulation_mode)
    await init_db()
    logger.info("Database initialised at %s", settings.database_url)
    yield
    logger.info("Project Phantasm shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Project Phantasm — Zombie Credential Exorcist",
        description=(
            "Automated cybersecurity threat-intelligence pipeline that identifies, "
            "assesses and neutralises zombie credentials. Powered by FastAPI, "
            "Google Gemini, and n8n automation."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in ROUTERS:
        app.include_router(router)
    return app


app = create_app()
