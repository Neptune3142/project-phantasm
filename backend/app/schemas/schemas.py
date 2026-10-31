"""Pydantic schemas for request/response validation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# User telemetry
# ---------------------------------------------------------------------------
class UserTelemetryIn(BaseModel):
    """Incoming security telemetry for a monitored account."""

    email: EmailStr
    role: str = Field(..., min_length=1, max_length=128)
    account_type: Literal["employee", "contractor", "service_account", "admin"] = "employee"
    last_active_days: int = Field(..., ge=0, le=10000)
    accessed_resources: List[str] = Field(default_factory=list)
    failed_login_attempts: int = Field(default=0, ge=0, le=100000)
    location_anomaly: bool = False
    privilege_level: Literal["standard", "elevated", "administrator", "service"] = "standard"

    @field_validator("accessed_resources")
    @classmethod
    def _strip_resources(cls, v):
        return [r for r in v if r and r.strip()]


class UserAccountOut(BaseModel):
    user_id: str
    email: EmailStr
    role: str
    account_type: str
    last_active_days: int
    accessed_resources: List[str]
    failed_login_attempts: int
    location_anomaly: bool
    privilege_level: str
    account_status: str
    created_at: Optional[datetime] = None


class AccountCreateOut(BaseModel):
    user_id: str
    email: EmailStr
    account_status: str


# ---------------------------------------------------------------------------
# AI / threat assessment
# ---------------------------------------------------------------------------
RiskCategory = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
RecommendedAction = Literal["MONITOR", "FLAG", "REQUIRE_REVOCATION_APPROVAL", "REVOKE_IMMEDIATELY"]


class GeminiAssessment(BaseModel):
    """Schema enforced on Gemini structured responses."""

    threat_score: int = Field(..., ge=0, le=100)
    risk_category: RiskCategory
    reasoning: str = Field(..., min_length=10)
    risk_factors: List[str] = Field(default_factory=list)
    recommended_action: RecommendedAction
    epitaph_summary: str = Field(..., min_length=1)

    @field_validator("risk_factors")
    @classmethod
    def _dedupe_factors(cls, v):
        return [f for f in dict.fromkeys(v) if f]


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------
class IncidentOut(BaseModel):
    incident_id: str
    user_id: str
    user_email: Optional[str] = None
    timestamp: datetime
    threat_score: int
    risk_category: RiskCategory
    ai_reasoning: Optional[str]
    risk_factors: List[str]
    recommended_action: RecommendedAction
    action_taken: Optional[str]
    execution_status: str
    epitaph_summary: Optional[str]
    assessment_source: str
    simulation_mode: bool
    scenario_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Workflow execution
# ---------------------------------------------------------------------------
class ExecutionStep(BaseModel):
    step: str
    status: Literal["pending", "running", "completed", "failed"]
    timestamp: Optional[datetime] = None
    detail: Optional[str] = None


class ExecutionOut(BaseModel):
    execution_id: str
    incident_id: Optional[str] = None
    workflow_status: str
    current_step: str
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    step_history: List[dict]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DashboardStats(BaseModel):
    total_accounts: int
    active_accounts: int
    inactive_accounts: int
    flagged_accounts: int
    critical_threats: int
    credentials_revoked: int
    total_incidents: int
    system_status: str
    simulation_mode: bool


# ---------------------------------------------------------------------------
# Pipeline execution request
# ---------------------------------------------------------------------------
class ExorcismRequest(BaseModel):
    user_id: str
    scenario_id: Optional[str] = None
    use_gemini: bool = True
    force_simulation: bool = False


class ExorcismResponse(BaseModel):
    incident_id: str
    execution_id: str
    user_id: str
    threat_score: int
    risk_category: RiskCategory
    recommended_action: RecommendedAction
    assessment_source: str
    execution_status: str
    pipeline: List[ExecutionStep]


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------
class ApprovalRequest(BaseModel):
    approver: EmailStr
    decision: Literal["approved", "rejected"]
    comments: Optional[str] = None


class ApprovalOut(BaseModel):
    approval_id: str
    incident_id: str
    approver: str
    decision: str
    approval_timestamp: datetime
    comments: Optional[str]
    final_action_taken: Optional[str] = None
    final_status: Optional[str] = None


# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------
class IntegrationStatus(BaseModel):
    gemini: dict
    n8n: dict
    google_sheets: dict
    gmail: dict
    simulation_mode: bool
    database_url: str


class CredentialUpdate(BaseModel):
    """A single credential update sent from the Settings page."""

    key: Literal[
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "N8N_BASE_URL",
        "N8N_WEBHOOK_URL",
        "N8N_API_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
        "GOOGLE_SHEET_ID",
        "GMAIL_SENDER",
        "GMAIL_RECIPIENT",
        "SIMULATION_MODE",
    ]
    value: str


class ConnectionTestResult(BaseModel):
    connected: bool
    detail: str
    suggestion: Optional[str] = None


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
class ScenarioOut(BaseModel):
    scenario_id: str
    name: str
    description: str
    telemetry: UserTelemetryIn
    expected_risk: str


class SimulationRunResult(BaseModel):
    scenario_id: str
    incident_id: str
    execution_id: str
    threat_score: int
    risk_category: str
    assessment_source: str
    expected_risk: str
    pass_: bool
    pipeline: List[ExecutionStep]


class GenericMessage(BaseModel):
    message: str
    detail: Optional[Any] = None
