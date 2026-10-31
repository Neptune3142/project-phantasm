"""Tests for the IAM service — mock revocation + live-revocation safety."""
import asyncio
import pytest

from app.database import AsyncSessionLocal
from app.models import UserAccount
from app.services.iam_service import IAMService, IAMRevocationError
from app.schemas import UserTelemetryIn
from sqlalchemy import select


async def _make_user(session, email="victim@example.com"):
    u = UserAccount(
        email=email,
        role="Engineer",
        account_type="employee",
        last_active_days=10,
        accessed_resources=[],
        failed_login_attempts=0,
        location_anomaly=False,
        privilege_level="standard",
        account_status="ACTIVE",
    )
    session.add(u)
    await session.flush()
    return u


def test_simulation_revocation_sets_status():
    async def _run():
        async with AsyncSessionLocal() as s:
            u = await _make_user(s)
            svc = IAMService(simulation_mode=True)
            await svc.revoke(
                s, u.user_id,
                incident_id="inc-1",
                reason="test revocation",
                approved=True,
                approver="test-approver",
            )
            await s.commit()
            result = await s.execute(select(UserAccount).where(UserAccount.user_id == u.user_id))
            return result.scalar_one()
    out = asyncio.get_event_loop().run_until_complete(_run())
    assert out.account_status == "REVOKED"


def test_live_revocation_without_provider_rejected():
    """Live mode with no configured provider must NEVER revoke."""
    async def _run():
        async with AsyncSessionLocal() as s:
            u = await _make_user(s)
            svc = IAMService(simulation_mode=False, live_provider=None)
            with pytest.raises(IAMRevocationError):
                await svc.revoke(
                    s, u.user_id,
                    incident_id="inc-1",
                    reason="attempting live revoke",
                    approved=True,
                )
            await s.rollback()
    asyncio.get_event_loop().run_until_complete(_run())


def test_live_revocation_without_approval_rejected():
    """Even if a provider is configured, AI alone may not revoke."""
    async def _run():
        async with AsyncSessionLocal() as s:
            u = await _make_user(s)
            svc = IAMService(simulation_mode=False, live_provider="aws-iam-stub")
            with pytest.raises(IAMRevocationError):
                await svc.revoke(
                    s, u.user_id,
                    incident_id="inc-1",
                    reason="attempting unapproved revoke",
                    approved=False,
                )
            await s.rollback()
    asyncio.get_event_loop().run_until_complete(_run())


def test_unknown_user_revocation_rejected():
    async def _run():
        async with AsyncSessionLocal() as s:
            svc = IAMService(simulation_mode=True)
            with pytest.raises(IAMRevocationError):
                await svc.revoke(
                    s, "does-not-exist",
                    incident_id="inc-1",
                    reason="missing user",
                    approved=True,
                )
    asyncio.get_event_loop().run_until_complete(_run())


def test_flag_then_monitor_state_transitions():
    async def _run():
        async with AsyncSessionLocal() as s:
            u = await _make_user(s)
            svc = IAMService(simulation_mode=True)
            await svc.flag(s, u.user_id, "flagging")
            await s.flush()
            assert u.account_status == "FLAGGED"
            await svc.monitor(s, u.user_id, "monitoring")
            await s.flush()
            assert u.account_status == "MONITORED"
            await s.rollback()
    asyncio.get_event_loop().run_until_complete(_run())
