"""Exorcism trigger endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import UserAccount
from app.schemas import ExorcismRequest, ExorcismResponse
from app.services.pipeline_service import run_exorcism

router = APIRouter(prefix="/api/v1", tags=["exorcism"])


@router.post("/trigger-exorcism", response_model=ExorcismResponse)
async def trigger_exorcism(
    request: ExorcismRequest, session: AsyncSession = Depends(get_session)
) -> ExorcismResponse:
    # Verify the account exists first — pipeline_service handles 404 semantics.
    result = await session.execute(select(UserAccount).where(UserAccount.user_id == request.user_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"User {request.user_id} not found")
    response = await run_exorcism(
        session,
        request.user_id,
        scenario_id=request.scenario_id,
        use_gemini=request.use_gemini,
        force_simulation=request.force_simulation,
    )
    await session.commit()
    return response
