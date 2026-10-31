"""Simulation endpoints — six predefined scenarios + controls."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import SecurityIncident, UserAccount, WorkflowExecution, ApprovalRecord
from app.schemas import (
    GenericMessage,
    ScenarioOut,
    SimulationRunResult,
    UserAccountOut,
    UserTelemetryIn,
)
from app.services.pipeline_service import run_exorcism
from app.services.rules_engine import assess
from app.services.simulation_service import get_scenario, list_scenarios, random_telemetry

router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


@router.get("/scenarios", response_model=list[ScenarioOut])
async def scenarios() -> list[ScenarioOut]:
    return list_scenarios()


async def _ensure_account(session: AsyncSession, telemetry: UserTelemetryIn, scenario_id: str | None) -> UserAccount:
    """Create or refresh a UserAccount row matching the telemetry."""
    existing = await session.execute(
        select(UserAccount).where(UserAccount.email == str(telemetry.email))
    )
    account = existing.scalar_one_or_none()
    if account is None:
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
    else:
        account.role = telemetry.role
        account.account_type = telemetry.account_type
        account.last_active_days = telemetry.last_active_days
        account.accessed_resources = telemetry.accessed_resources
        account.failed_login_attempts = telemetry.failed_login_attempts
        account.location_anomaly = telemetry.location_anomaly
        account.privilege_level = telemetry.privilege_level
        account.account_status = "ACTIVE"
    await session.flush()
    return account


@router.post("/run/{scenario_id}", response_model=SimulationRunResult)
async def run_scenario(
    scenario_id: str, session: AsyncSession = Depends(get_session)
) -> SimulationRunResult:
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")
    account = await _ensure_account(session, scenario.telemetry, scenario_id)
    response = await run_exorcism(
        session,
        account.user_id,
        scenario_id=scenario_id,
        use_gemini=False,  # scenarios run deterministically by default
        force_simulation=True,
    )
    await session.commit()
    expected = scenario.expected_risk.upper()
    actual = response.risk_category.upper()
    pass_ = _pass_check(expected, actual)
    return SimulationRunResult(
        scenario_id=scenario_id,
        incident_id=response.incident_id,
        execution_id=response.execution_id,
        threat_score=response.threat_score,
        risk_category=response.risk_category,
        assessment_source=response.assessment_source,
        expected_risk=scenario.expected_risk,
        **{"pass_": pass_},
        pipeline=response.pipeline,
    )


@router.post("/run-all", response_model=list[SimulationRunResult])
async def run_all_scenarios(session: AsyncSession = Depends(get_session)) -> list[SimulationRunResult]:
    results: list[SimulationRunResult] = []
    for scenario in list_scenarios():
        account = await _ensure_account(session, scenario.telemetry, scenario.scenario_id)
        response = await run_exorcism(
            session,
            account.user_id,
            scenario_id=scenario.scenario_id,
            use_gemini=False,
            force_simulation=True,
        )
        await session.commit()
        results.append(
            SimulationRunResult(
                scenario_id=scenario.scenario_id,
                incident_id=response.incident_id,
                execution_id=response.execution_id,
                threat_score=response.threat_score,
                risk_category=response.risk_category,
                assessment_source=response.assessment_source,
                expected_risk=scenario.expected_risk,
                **{"pass_": _pass_check(scenario.expected_risk.upper(), response.risk_category.upper())},
                pipeline=response.pipeline,
            )
        )
    return results


@router.post("/generate-random", response_model=UserAccountOut)
async def generate_random(session: AsyncSession = Depends(get_session)) -> UserAccountOut:
    telemetry = random_telemetry()
    account = await _ensure_account(session, telemetry, None)
    await session.commit()
    await session.refresh(account)
    return UserAccountOut(**account.to_dict())


@router.post("/reset", response_model=GenericMessage)
async def reset_simulation(session: AsyncSession = Depends(get_session)) -> GenericMessage:
    """Reset account statuses back to ACTIVE for all accounts."""
    result = await session.execute(select(UserAccount))
    for acc in result.scalars().all():
        acc.account_status = "ACTIVE"
    await session.commit()
    return GenericMessage(
        message="Simulation reset — all accounts set back to ACTIVE.",
    )


@router.post("/clear", response_model=GenericMessage)
async def clear_history(session: AsyncSession = Depends(get_session)) -> GenericMessage:
    """Clear all historical simulation data (incidents, executions, approvals)."""
    await session.execute(delete(ApprovalRecord))
    await session.execute(delete(WorkflowExecution))
    await session.execute(delete(SecurityIncident))
    await session.commit()
    return GenericMessage(
        message="Historical simulation data cleared.",
        detail={"cleared": ["incidents", "executions", "approvals"]},
    )


def _pass_check(expected: str, actual: str) -> bool:
    """Loose pass: expected may be a `|`-separated list of acceptable categories."""
    acceptable = [c.strip().upper() for c in expected.split("|")]
    return actual.upper() in acceptable
