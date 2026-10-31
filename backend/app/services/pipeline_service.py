"""Pipeline orchestrator — runs the full exorcism pipeline for one account.

This is the heart of the application. It executes the same pipeline steps in
both simulation and live mode:

  INGESTION → VALIDATION → GEMINI ANALYSIS → RISK CLASSIFICATION →
  DECISION → APPROVAL / SIMULATED REVOCATION → AUDIT LEDGER → GMAIL DISPATCH

Each step is recorded as an ExecutionStep so the frontend pipeline monitor
reflects the genuine backend execution trace, not decorative animation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import SecurityIncident, UserAccount, WorkflowExecution
from app.schemas import (
    ExecutionStep,
    ExorcismResponse,
    GeminiAssessment,
    UserTelemetryIn,
)
from app.services import rules_engine
from app.services.audit_service import append_incident
from app.services.gemini_service import gemini_service
from app.services.google_service import google_service
from app.services.iam_service import IAMRevocationError, iam_service
from app.services.n8n_service import n8n_service

logger = logging.getLogger("phantasm.pipeline")


# Pipeline steps in order — referenced by both the orchestrator and the
# frontend pipeline monitor (via the step_history field).
PIPELINE_STEPS = [
    "INGESTION",
    "VALIDATION",
    "GEMINI_ANALYSIS",
    "RISK_CLASSIFICATION",
    "DECISION",
    "IAM_ACTION",
    "AUDIT_LEDGER",
    "GMAIL_DISPATCH",
]


async def _mark_step(execution: WorkflowExecution, step: str, status: str, detail: Optional[str] = None) -> None:
    execution.current_step = step
    execution.step_history = (execution.step_history or []) + [
        {
            "step": step,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        }
    ]


async def _complete_step(execution: WorkflowExecution, step: str, detail: Optional[str] = None) -> None:
    await _mark_step(execution, step, "completed", detail)


async def _fail_step(execution: WorkflowExecution, step: str, detail: str) -> None:
    await _mark_step(execution, step, "failed", detail)
    execution.workflow_status = "FAILED"
    execution.error_message = detail


async def run_exorcism(
    session: AsyncSession,
    user_id: str,
    *,
    scenario_id: Optional[str] = None,
    use_gemini: bool = True,
    force_simulation: bool = False,
) -> ExorcismResponse:
    """Execute the full pipeline for one user.

    Returns an ExorcismResponse containing the incident, execution and the
    step-by-step pipeline trace for the frontend pipeline monitor.
    """
    settings = get_settings()
    sim_mode = settings.simulation_mode or force_simulation

    # Re-init IAM service with current mode
    iam_service.simulation_mode = sim_mode

    # Create a fresh execution record.
    execution = WorkflowExecution(
        workflow_status="RUNNING",
        current_step="INGESTION",
        step_history=[],
    )
    session.add(execution)
    await _mark_step(execution, "INGESTION", "running")

    # ---- INGESTION ------------------------------------------------------
    result = await session.execute(select(UserAccount).where(UserAccount.user_id == user_id))
    account = result.scalar_one_or_none()
    if account is None:
        await _fail_step(execution, "INGESTION", f"User {user_id} not found.")
        await session.flush()
        return ExorcismResponse(
            incident_id="",
            execution_id=execution.execution_id,
            user_id=user_id,
            threat_score=0,
            risk_category="LOW",
            recommended_action="MONITOR",
            assessment_source="none",
            execution_status="FAILED",
            pipeline=[ExecutionStep(**s) for s in execution.step_history],
        )
    await _complete_step(execution, "INGESTION", f"Loaded account {account.email}")

    # ---- VALIDATION -----------------------------------------------------
    await _mark_step(execution, "VALIDATION", "running")
    try:
        telemetry = UserTelemetryIn(
            email=account.email,
            role=account.role,
            account_type=account.account_type,
            last_active_days=account.last_active_days,
            accessed_resources=account.accessed_resources or [],
            failed_login_attempts=account.failed_login_attempts,
            location_anomaly=account.location_anomaly,
            privilege_level=account.privilege_level,
        )
    except Exception as exc:
        await _fail_step(execution, "VALIDATION", f"Telemetry invalid: {exc}")
        await session.flush()
        return ExorcismResponse(
            incident_id="",
            execution_id=execution.execution_id,
            user_id=user_id,
            threat_score=0,
            risk_category="LOW",
            recommended_action="MONITOR",
            assessment_source="none",
            execution_status="FAILED",
            pipeline=[ExecutionStep(**s) for s in execution.step_history],
        )
    await _complete_step(execution, "VALIDATION", "Telemetry conforms to schema")

    # ---- GEMINI ANALYSIS ------------------------------------------------
    await _mark_step(execution, "GEMINI_ANALYSIS", "running")
    source_label = "rules_engine"
    if use_gemini and settings.has_gemini() and not force_simulation:
        assessment = await gemini_service.assess(telemetry)
        source_label = "gemini" if settings.has_gemini() else "rules_engine"
        detail = f"Assessment via {source_label}"
    else:
        assessment = rules_engine.assess(telemetry)
        detail = "Assessment via deterministic rules engine (no Gemini key configured)"
    await _complete_step(execution, "GEMINI_ANALYSIS", detail)

    # ---- RISK CLASSIFICATION -------------------------------------------
    await _mark_step(execution, "RISK_CLASSIFICATION", "running")
    # The category is already derived from the score inside the assess step.
    await _complete_step(
        execution,
        "RISK_CLASSIFICATION",
        f"score={assessment.threat_score} category={assessment.risk_category}",
    )

    # ---- DECISION -------------------------------------------------------
    await _mark_step(execution, "DECISION", "running")
    action = assessment.recommended_action
    await _complete_step(execution, "DECISION", f"recommended_action={action}")

    # Create the incident record (audit ledger entry).
    incident = SecurityIncident(
        user_id=user_id,
        threat_score=assessment.threat_score,
        risk_category=assessment.risk_category,
        ai_reasoning=assessment.reasoning,
        risk_factors=assessment.risk_factors,
        recommended_action=assessment.recommended_action,
        assessment_source=source_label,
        simulation_mode=sim_mode,
        scenario_id=scenario_id,
        execution_status="RUNNING",
    )
    # Attach the already-loaded account so downstream services can read
    # incident.user.email without triggering a lazy load in async context.
    incident.user = account
    session.add(incident)
    await session.flush()
    execution.incident_id = incident.incident_id

    # ---- IAM ACTION -----------------------------------------------------
    await _mark_step(execution, "IAM_ACTION", "running")
    action_taken: str
    if action in ("REQUIRE_REVOCATION_APPROVAL", "REVOKE_IMMEDIATELY") and sim_mode:
        # Simulation can revoke mock accounts safely.
        try:
            await iam_service.revoke(
                session,
                user_id,
                incident_id=incident.incident_id,
                reason=assessment.reasoning,
                approved=True,
                approver="simulation-engine",
            )
            action_taken = "REVOKED"
            incident.execution_status = "REVOKED"
        except IAMRevocationError as exc:
            action_taken = "REJECTED"
            incident.execution_status = "REJECTED"
            await _fail_step(execution, "IAM_ACTION", str(exc))
    elif action == "REVOKE_IMMEDIATELY":
        # Live mode — request approval gate, do not revoke.
        await iam_service.request_approval(session, user_id, assessment.reasoning)
        action_taken = "PENDING_APPROVAL"
        incident.execution_status = "PENDING_APPROVAL"
    elif action == "FLAG":
        await iam_service.flag(session, user_id, assessment.reasoning)
        action_taken = "FLAGGED"
        incident.execution_status = "FLAGGED"
    else:
        await iam_service.monitor(session, user_id, assessment.reasoning)
        action_taken = "MONITORED"
        incident.execution_status = "MONITORED"
    incident.action_taken = action_taken
    incident.epitaph_summary = assessment.epitaph_summary
    await session.flush()
    if execution.workflow_status != "FAILED":
        await _complete_step(execution, "IAM_ACTION", f"action_taken={action_taken}")

    # ---- FIRE-AND-FORGET n8n SUBMIT -----------------------------------
    # n8n is optional. If configured, the same payload is also dispatched to
    # the workflow. The local pipeline is the source of truth.
    n8n_payload = {
        "incident_id": incident.incident_id,
        "user_id": user_id,
        "telemetry": telemetry.model_dump(mode="json"),
        "assessment": {
            "threat_score": assessment.threat_score,
            "risk_category": assessment.risk_category,
            "reasoning": assessment.reasoning,
            "risk_factors": assessment.risk_factors,
            "recommended_action": assessment.recommended_action,
            "epitaph_summary": assessment.epitaph_summary,
            "assessment_source": source_label,
            "simulation_mode": sim_mode,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    n8n_result = await n8n_service.submit_exorcism(n8n_payload)

    # ---- AUDIT LEDGER ---------------------------------------------------
    await _mark_step(execution, "AUDIT_LEDGER", "running")
    sheet_result = await google_service.append_incident_row(incident)
    await _complete_step(
        execution,
        "AUDIT_LEDGER",
        f"local=ok, sheets={'ok' if sheet_result.get('written') else 'skipped'}",
    )

    # ---- GMAIL DISPATCH -------------------------------------------------
    await _mark_step(execution, "GMAIL_DISPATCH", "running")
    mail_result = await google_service.send_incident_email(incident)
    await _complete_step(
        execution,
        "GMAIL_DISPATCH",
        f"{'sent' if mail_result.get('sent') else 'skipped'}",
    )

    # ---- Finalise execution --------------------------------------------
    if execution.workflow_status != "FAILED":
        execution.workflow_status = "COMPLETED"
    execution.completed_at = datetime.now(timezone.utc)
    if execution.workflow_status == "COMPLETED":
        incident.execution_status = incident.execution_status or "COMPLETED"
    await session.flush()

    return ExorcismResponse(
        incident_id=incident.incident_id,
        execution_id=execution.execution_id,
        user_id=user_id,
        threat_score=assessment.threat_score,
        risk_category=assessment.risk_category,
        recommended_action=assessment.recommended_action,
        assessment_source=source_label,
        execution_status=execution.workflow_status,
        pipeline=[ExecutionStep(**s) for s in execution.step_history],
    )
