"""Centralised application configuration for Project Phantasm.

Secrets are loaded from environment variables / a `.env` file. The application
NEVER logs raw secrets and never returns them via API responses. The frontend
may *update* credentials via the integrations endpoints, but only the masked
status is ever returned.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed, validated application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_env: str = Field(default="development")
    simulation_mode: bool = Field(default=True)
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000")

    # --- Database ---
    database_url: str = Field(default="sqlite+aiosqlite:///./phantasm.db")

    @field_validator("database_url", mode="before")
    @classmethod
    def _fix_db_url(cls, v):
        # If the env-var override is not a SQLAlchemy URL (e.g. a bare
        # file:// path leaked from the sandbox), fall back to the default
        # SQLite URL rather than crashing at import time.
        if not v or not isinstance(v, str):
            return "sqlite+aiosqlite:///./phantasm.db"
        if v.startswith("file:"):
            return "sqlite+aiosqlite:///./phantasm.db"
        if v.startswith("sqlite:") and "aiosqlite" not in v:
            return v.replace("sqlite:", "sqlite+aiosqlite:", 1)
        return v

    # --- Gemini ---
    gemini_api_key: Optional[str] = Field(default=None)
    gemini_model: str = Field(default="gemini-3.8-flash")

    # --- n8n ---
    n8n_base_url: Optional[str] = Field(default=None)
    n8n_webhook_url: Optional[str] = Field(default=None)
    n8n_api_key: Optional[str] = Field(default=None)

    # --- Google Sheets ---
    google_client_id: Optional[str] = Field(default=None)
    google_client_secret: Optional[str] = Field(default=None)
    google_refresh_token: Optional[str] = Field(default=None)
    google_sheet_id: Optional[str] = Field(default=None)

    # --- Gmail ---
    gmail_sender: Optional[str] = Field(default=None)
    gmail_recipient: Optional[str] = Field(default=None)

    # --- Risk thresholds (used by deterministic rules engine) ---
    critical_threshold: int = 75
    high_threshold: int = 50
    medium_threshold: int = 25

    @field_validator("simulation_mode", mode="before")
    @classmethod
    def _coerce_bool(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in {"1", "true", "yes", "on"}
        return bool(v)

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    def has_n8n(self) -> bool:
        return bool(self.n8n_webhook_url)

    def has_google_sheets(self) -> bool:
        return all([self.google_client_id, self.google_client_secret, self.google_refresh_token, self.google_sheet_id])

    def has_gmail(self) -> bool:
        return bool(self.gmail_sender and self.gmail_recipient)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


def reload_settings() -> Settings:
    """Force a re-read of `.env` (used after the Settings page saves new values)."""
    get_settings.cache_clear()
    # Also clear any cached secrets inside service singletons.
    return get_settings()


def mask_secret(value: Optional[str]) -> str:
    """Return a masked representation of a secret for display."""
    if not value:
        return "—"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}…{value[-4:]}"


def set_env(key: str, value: Optional[str]) -> None:
    """Persist a runtime override to the process environment.

    This is used by the integrations endpoints so credentials entered via the
    UI take effect immediately. The change is also written back to the `.env`
    file so it survives a process restart.
    """
    if value is None or value == "":
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    _persist_env_to_file(key, value)


def _persist_env_to_file(key: str, value: Optional[str]) -> None:
    """Persist a single key/value pair to the local `.env` file."""
    env_path = os.path.join(os.getcwd(), ".env")
    lines: List[str] = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip().startswith(f"{key}=") or line.strip() == key:
                    if value:
                        lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found and value:
        lines.append(f"{key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
