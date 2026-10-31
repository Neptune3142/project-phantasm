"""Approval gate for high-risk live IAM actions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import ApprovalRecord, SecurityIncident
from app.schemas import ApprovalOut, ApprovalRequest
from app.services.iam_service import iam_service, IAMRevocationError

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


@router.post("/{incident_id}", response_model=ApprovalOut)
async def approve_or_reject(
    incident_id: str,
    request: ApprovalRequest,
    session: AsyncSession = Depends(get_session),
) -> ApprovalOut:
    settings = get_settings()
    result = await session.execute(
        select(SecurityIncident).where(SecurityIncident.incident_id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    approval = ApprovalRecord(
        incident_id=incident_id,
        approver=str(request.approver),
        decision=request.decision,
        comments=request.comments,
    )
    session.add(approval)

    final_action: str = incident.action_taken or ""
    final_status: str = incident.execution_status or ""

    if request.decision == "approved":
        try:
            # Live revocation only proceeds when a real provider is configured.
            # In simulation mode, the revocation already happened at pipeline
            # time — so this is a no-op re-confirmation.
            if settings.simulation_mode:
                final_action = incident.action_taken or "REVOKED"
                final_status = "APPROVED"
            else:
                # Live mode — perform the actual revocation now.
                await iam_service.revoke(
                    session,
                    incident.user_id,
                    incident_id=incident_id,
                    reason=incident.ai_reasoning or "approved via UI",
                    approved=True,
                    approver=str(request.approver),
                )
                final_action = "REVOKED"
                final_status = "APPROVED"
                incident.execution_status = "REVOKED"
                incident.action_taken = "REVOKED"
        except IAMRevocationError as exc:
            final_status = "REJECTED"
            raise HTTPException(status_code=403, detail=str(exc))
    else:
        final_action = "REJECTED"
        final_status = "REJECTED"
        incident.execution_status = "REJECTED"
        incident.action_taken = "REJECTED"

    await session.flush()
    await session.commit()
    await session.refresh(approval)
    return ApprovalOut(
        approval_id=approval.approval_id,
        incident_id=approval.incident_id,
        approver=approval.approver,
        decision=approval.decision,
        approval_timestamp=approval.approval_timestamp,
        comments=approval.comments,
        final_action_taken=final_action,
        final_status=final_status,
    )
