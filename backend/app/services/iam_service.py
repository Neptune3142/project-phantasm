"""Mock IAM service — manages simulated account states.

In simulation mode this fully owns the account state machine. In live mode
real revocation is *disabled* unless a real provider is explicitly configured
via the integration layer (a stub adapter is provided for future use).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserAccount

logger = logging.getLogger("phantasm.iam")


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FLAGGED = "FLAGGED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    REVOKED = "REVOKED"
    MONITORED = "MONITORED"


class IAMRevocationError(RuntimeError):
    """Raised when an unsafe revocation is attempted."""


class IAMService:
    """In-memory mock IAM with a small adapter hook for live providers."""

    def __init__(self, simulation_mode: bool = True, live_provider: Optional[str] = None) -> None:
        self.simulation_mode = simulation_mode
        self.live_provider = live_provider  # e.g. "aws-iam", "okta" — future use

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------
    async def flag(self, session: AsyncSession, user_id: str, reason: str) -> UserAccount:
        account = await self._get_user(session, user_id)
        account.account_status = AccountStatus.FLAGGED.value
        account.deactivation_reason = reason
        account.updated_at = datetime.now(timezone.utc)
        await session.flush()
        logger.info("Flagged user %s (%s).", user_id, reason)
        return account

    async def monitor(self, session: AsyncSession, user_id: str, reason: str) -> UserAccount:
        account = await self._get_user(session, user_id)
        account.account_status = AccountStatus.MONITORED.value
        account.deactivation_reason = reason
        account.updated_at = datetime.now(timezone.utc)
        await session.flush()
        logger.info("Monitoring user %s (%s).", user_id, reason)
        return account

    async def request_approval(self, session: AsyncSession, user_id: str, reason: str) -> UserAccount:
        account = await self._get_user(session, user_id)
        account.account_status = AccountStatus.PENDING_APPROVAL.value
        account.deactivation_reason = reason
        account.updated_at = datetime.now(timezone.utc)
        await session.flush()
        logger.info("Approval requested for user %s (%s).", user_id, reason)
        return account

    async def revoke(
        self,
        session: AsyncSession,
        user_id: str,
        *,
        incident_id: str,
        reason: str,
        approved: bool = False,
        approver: Optional[str] = None,
    ) -> UserAccount:
        """Revoke credentials. Live revocation requires approval + provider config."""
        account = await self._get_user(session, user_id)

        if not self.simulation_mode and not self.live_provider:
            # Live mode without a configured provider is a hard safety stop.
            raise IAMRevocationError(
                "Live IAM revocation is disabled. Configure a real IAM provider "
                "in the integration layer before attempting live revocation."
            )

        if not self.simulation_mode and not approved:
            raise IAMRevocationError(
                "AI may not revoke real accounts without explicit human approval. "
                f"incident={incident_id}, user={user_id}"
            )

        previous = account.account_status
        account.account_status = AccountStatus.REVOKED.value
        account.deactivation_reason = reason
        account.updated_at = datetime.now(timezone.utc)
        # Audit trail in metadata
        account.__dict__["_revocation_audit"] = {
            "previous_status": previous,
            "incident_id": incident_id,
            "reason": reason,
            "approver": approver,
            "revoked_at": datetime.now(timezone.utc).isoformat(),
        }
        await session.flush()
        logger.info(
            "Revoked credentials for %s (incident=%s, previous=%s, approver=%s).",
            user_id, incident_id, previous, approver or "simulation",
        )
        return account

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _get_user(self, session: AsyncSession, user_id: str) -> UserAccount:
        result = await session.execute(select(UserAccount).where(UserAccount.user_id == user_id))
        account = result.scalar_one_or_none()
        if account is None:
            raise IAMRevocationError(f"User {user_id} not found in IAM directory.")
        return account


iam_service = IAMService(simulation_mode=True)
