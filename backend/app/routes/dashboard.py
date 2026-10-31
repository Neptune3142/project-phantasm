"""Dashboard statistics endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import SecurityIncident, UserAccount
from app.schemas import DashboardStats

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(session: AsyncSession = Depends(get_session)) -> DashboardStats:
    s = get_settings()
    # Accounts
    total = (await session.execute(select(func.count(UserAccount.user_id)))).scalar_one()
    active = (
        await session.execute(
            select(func.count(UserAccount.user_id)).where(UserAccount.account_status == "ACTIVE")
        )
    ).scalar_one()
    flagged = (
        await session.execute(
            select(func.count(UserAccount.user_id)).where(
                UserAccount.account_status.in_(["FLAGGED", "PENDING_APPROVAL", "MONITORED"])
            )
        )
    ).scalar_one()
    revoked = (
        await session.execute(
            select(func.count(UserAccount.user_id)).where(UserAccount.account_status == "REVOKED")
        )
    ).scalar_one()
    inactive = (
        await session.execute(
            select(func.count(UserAccount.user_id)).where(UserAccount.last_active_days >= 30)
        )
    ).scalar_one()
    # Incidents
    total_inc = (await session.execute(select(func.count(SecurityIncident.incident_id)))).scalar_one()
    critical = (
        await session.execute(
            select(func.count(SecurityIncident.incident_id)).where(
                SecurityIncident.risk_category == "CRITICAL"
            )
        )
    ).scalar_one()

    return DashboardStats(
        total_accounts=int(total),
        active_accounts=int(active),
        inactive_accounts=int(inactive),
        flagged_accounts=int(flagged),
        critical_threats=int(critical),
        credentials_revoked=int(revoked),
        total_incidents=int(total_inc),
        system_status="OPERATIONAL" if not s.simulation_mode else "OPERATIONAL (SIMULATION)",
        simulation_mode=s.simulation_mode,
    )
