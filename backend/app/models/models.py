"""SQLAlchemy ORM models for Project Phantasm."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import JSON, String, Text, ForeignKey, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class UserAccount(Base):
    """A monitored user/contractor/service account."""

    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    account_type: Mapped[str] = mapped_column(String(64), default="employee")
    last_active_days: Mapped[int] = mapped_column(Integer, default=0)
    accessed_resources: Mapped[List[str]] = mapped_column(JSON, default=list)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    location_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    privilege_level: Mapped[str] = mapped_column(String(64), default="standard")
    account_status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    deactivation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    incidents: Mapped[List["SecurityIncident"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role,
            "account_type": self.account_type,
            "last_active_days": self.last_active_days,
            "accessed_resources": self.accessed_resources or [],
            "failed_login_attempts": self.failed_login_attempts,
            "location_anomaly": self.location_anomaly,
            "privilege_level": self.privilege_level,
            "account_status": self.account_status,
            "deactivation_reason": self.deactivation_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SecurityIncident(Base):
    """A single exorcism event — one account, one assessment, one action."""

    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    threat_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_category: Mapped[str] = mapped_column(String(32), default="LOW")
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_factors: Mapped[List[str]] = mapped_column(JSON, default=list)
    recommended_action: Mapped[str] = mapped_column(String(64), default="MONITOR")
    action_taken: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    execution_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    epitaph_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assessment_source: Mapped[str] = mapped_column(String(32), default="rules_engine")
    simulation_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    scenario_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user: Mapped["UserAccount"] = relationship(back_populates="incidents")
    executions: Mapped[List["WorkflowExecution"]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    approvals: Mapped[List["ApprovalRecord"]] = relationship(back_populates="incident", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "user_id": self.user_id,
            "user_email": self.user.email if self.user else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "threat_score": self.threat_score,
            "risk_category": self.risk_category,
            "ai_reasoning": self.ai_reasoning,
            "risk_factors": self.risk_factors or [],
            "recommended_action": self.recommended_action,
            "action_taken": self.action_taken,
            "execution_status": self.execution_status,
            "epitaph_summary": self.epitaph_summary,
            "assessment_source": self.assessment_source,
            "simulation_mode": self.simulation_mode,
            "scenario_id": self.scenario_id,
        }


class WorkflowExecution(Base):
    """Pipeline execution trace for a single incident."""

    __tablename__ = "executions"

    execution_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    incident_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("incidents.incident_id"), nullable=True, index=True)
    workflow_status: Mapped[str] = mapped_column(String(32), default="RUNNING")
    current_step: Mapped[str] = mapped_column(String(64), default="INGESTION")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    step_history: Mapped[List[dict]] = mapped_column(JSON, default=list)

    incident: Mapped["SecurityIncident"] = relationship(back_populates="executions")

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "incident_id": self.incident_id,
            "workflow_status": self.workflow_status,
            "current_step": self.current_step,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "step_history": self.step_history or [],
        }


class ApprovalRecord(Base):
    """Human approval for a high-risk IAM action."""

    __tablename__ = "approvals"

    approval_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    approver: Mapped[str] = mapped_column(String(255), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    approval_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    incident: Mapped["SecurityIncident"] = relationship(back_populates="approvals")

    def to_dict(self) -> dict:
        return {
            "approval_id": self.approval_id,
            "incident_id": self.incident_id,
            "approver": self.approver,
            "decision": self.decision,
            "approval_timestamp": self.approval_timestamp.isoformat() if self.approval_timestamp else None,
            "comments": self.comments,
        }


__all__ = ["UserAccount", "SecurityIncident", "WorkflowExecution", "ApprovalRecord", "Base"]
