"""Audit service — every security decision is persisted locally.

Optional Google Sheets audit ledger when configured. Local persistence is
the source of truth: the Google Sheet is a *secondary* mirror.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SecurityIncident
from app.schemas import IncidentOut

logger = logging.getLogger("phantasm.audit")


async def append_incident(session: AsyncSession, incident: SecurityIncident) -> SecurityIncident:
    session.add(incident)
    await session.flush()
    return incident


async def get_incident(session: AsyncSession, incident_id: str) -> Optional[SecurityIncident]:
    result = await session.execute(
        select(SecurityIncident).where(SecurityIncident.incident_id == incident_id)
    )
    return result.scalar_one_or_none()


async def list_incidents(session: AsyncSession, limit: int = 100) -> list[SecurityIncident]:
    result = await session.execute(
        select(SecurityIncident).order_by(SecurityIncident.timestamp.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def to_sheet_row(incident: SecurityIncident) -> list[str]:
    """Convert an incident to a row suitable for the Google Sheets ledger."""
    return [
        incident.incident_id,
        incident.user.email if incident.user else "",
        incident.timestamp.isoformat() if incident.timestamp else "",
        str(incident.threat_score),
        incident.risk_category,
        incident.ai_reasoning or "",
        "|".join(incident.risk_factors or []),
        incident.recommended_action,
        incident.action_taken or "",
        incident.execution_status,
        incident.assessment_source,
        "TRUE" if incident.simulation_mode else "FALSE",
        incident.epitaph_summary or "",
    ]


SHEET_HEADERS = [
    "incident_id", "user_email", "timestamp", "threat_score", "risk_category",
    "ai_reasoning", "risk_factors", "recommended_action", "action_taken",
    "execution_status", "assessment_source", "simulation_mode", "epitaph_summary",
]
