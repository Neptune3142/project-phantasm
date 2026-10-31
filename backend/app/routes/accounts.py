"""Account management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import UserAccount
from app.schemas import AccountCreateOut, UserAccountOut, UserTelemetryIn

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


@router.get("", response_model=list[UserAccountOut])
async def list_accounts(session: AsyncSession = Depends(get_session)) -> list[UserAccountOut]:
    result = await session.execute(select(UserAccount).order_by(UserAccount.created_at.desc()))
    accounts = result.scalars().all()
    return [UserAccountOut(**a.to_dict()) for a in accounts]


@router.get("/{user_id}", response_model=UserAccountOut)
async def get_account(user_id: str, session: AsyncSession = Depends(get_session)) -> UserAccountOut:
    result = await session.execute(select(UserAccount).where(UserAccount.user_id == user_id))
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return UserAccountOut(**account.to_dict())


@router.post("", response_model=AccountCreateOut, status_code=201)
async def create_account(
    telemetry: UserTelemetryIn, session: AsyncSession = Depends(get_session)
) -> AccountCreateOut:
    account = UserAccount(
        email=str(telemetry.email),
        role=telemetry.role,
        account_type=telemetry.account_type,
        last_active_days=telemetry.last_active_days,
        accessed_resources=telemetry.accessed_resources,
        failed_login_attempts=telemetry.failed_login_attempts,
        location_anomaly=telemetry.location_anomaly,
        privilege_level=telemetry.privilege_level,
        account_status="ACTIVE",
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return AccountCreateOut(
        user_id=account.user_id,
        email=account.email,
        account_status=account.account_status,
    )
