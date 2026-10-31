"""Incident + execution endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import SecurityIncident, WorkflowExecution
from app.schemas import ExecutionOut, IncidentOut

router = APIRouter(prefix="/api/v1", tags=["incidents"])


@router.get("/incidents", response_model=list[IncidentOut])
async def list_incidents(limit: int = 100, session: AsyncSession = Depends(get_session)) -> list[IncidentOut]:
    result = await session.execute(
        select(SecurityIncident)
        .options(selectinload(SecurityIncident.user))
        .order_by(SecurityIncident.timestamp.desc())
        .limit(limit)
    )
    out = []
    for inc in result.scalars().all():
        d = inc.to_dict()
        d["user_email"] = inc.user.email if inc.user else None
        out.append(IncidentOut(**d))
    return out


@router.get("/incidents/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: str, session: AsyncSession = Depends(get_session)) -> IncidentOut:
    result = await session.execute(
        select(SecurityIncident)
        .options(selectinload(SecurityIncident.user))
        .where(SecurityIncident.incident_id == incident_id)
    )
    inc = result.scalar_one_or_none()
    if inc is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    d = inc.to_dict()
    d["user_email"] = inc.user.email if inc.user else None
    return IncidentOut(**d)


@router.get("/executions/{execution_id}", response_model=ExecutionOut)
async def get_execution(execution_id: str, session: AsyncSession = Depends(get_session)) -> ExecutionOut:
    result = await session.execute(
        select(WorkflowExecution).where(WorkflowExecution.execution_id == execution_id)
    )
    ex = result.scalar_one_or_none()
    if ex is None:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    return ExecutionOut(**ex.to_dict())
