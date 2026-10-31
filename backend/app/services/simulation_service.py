"""Simulation engine — six predefined zombie-credential scenarios.

The same core pipeline (telemetry → assessment → classification → decision →
IAM action → audit) runs in both simulation and live mode. The only
difference is the source of the assessment (rules engine vs Gemini) and the
target of the IAM action (mock state vs real provider).
"""
from __future__ import annotations

import logging
from typing import List

from app.schemas import ScenarioOut, UserTelemetryIn

logger = logging.getLogger("phantasm.simulation")


# ---------------------------------------------------------------------------
# Six predefined scenarios
# ---------------------------------------------------------------------------
SCENARIOS: List[ScenarioOut] = [
    ScenarioOut(
        scenario_id="sleeping-ghost",
        name="THE SLEEPING GHOST",
        description=(
            "A long-dormant employee account with only a couple of failed logins "
            "and access to low-risk resources. Expected: LOW or MEDIUM."
        ),
        telemetry=UserTelemetryIn(
            email="alex.morgan@example.com",
            role="Junior Developer",
            account_type="employee",
            last_active_days=120,
            accessed_resources=["internal-wiki", "company-chat"],
            failed_login_attempts=2,
            location_anomaly=False,
            privilege_level="standard",
        ),
        expected_risk="LOW|MEDIUM",
    ),
    ScenarioOut(
        scenario_id="compromised-contractor",
        name="THE COMPROMISED CONTRACTOR",
        description=(
            "A contractor with 114 days of inactivity, 14 failed logins, "
            "production database access, and an unusual geographic login. "
            "Expected: CRITICAL."
        ),
        telemetry=UserTelemetryIn(
            email="contractor.devops@vendor-example.com",
            role="DevOps Contractor",
            account_type="contractor",
            last_active_days=114,
            accessed_resources=["production-database", "ssh-bastion", "ci-pipeline"],
            failed_login_attempts=14,
            location_anomaly=True,
            privilege_level="elevated",
        ),
        expected_risk="CRITICAL",
    ),
    ScenarioOut(
        scenario_id="privileged-phantom",
        name="THE PRIVILEGED PHANTOM",
        description=(
            "An administrator account inactive for 180 days with access to "
            "billing and infrastructure systems. Expected: CRITICAL."
        ),
        telemetry=UserTelemetryIn(
            email="infra.admin@example.com",
            role="Platform Administrator",
            account_type="admin",
            last_active_days=180,
            accessed_resources=["billing", "infrastructure", "iam-admin", "secrets-manager"],
            failed_login_attempts=1,
            location_anomaly=False,
            privilege_level="administrator",
        ),
        expected_risk="CRITICAL",
    ),
    ScenarioOut(
        scenario_id="false-alarm",
        name="THE FALSE ALARM",
        description=(
            "A user only 45 days inactive, no suspicious activity, only "
            "legitimate business resources. Expected: LOW."
        ),
        telemetry=UserTelemetryIn(
            email="sarah.chen@example.com",
            role="Marketing Lead",
            account_type="employee",
            last_active_days=45,
            accessed_resources=["marketing-portal", "analytics-readonly"],
            failed_login_attempts=0,
            location_anomaly=False,
            privilege_level="standard",
        ),
        expected_risk="LOW",
    ),
    ScenarioOut(
        scenario_id="brute-force-ghost",
        name="THE BRUTE FORCE GHOST",
        description=(
            "An account only 20 days inactive but with 50 failed logins from "
            "multiple suspicious IPs. Expected: HIGH or CRITICAL."
        ),
        telemetry=UserTelemetryIn(
            email="legacy.svc@example.com",
            role="Legacy Service Operator",
            account_type="employee",
            last_active_days=20,
            accessed_resources=["internal-api", "ldap"],
            failed_login_attempts=50,
            location_anomaly=True,
            privilege_level="standard",
        ),
        expected_risk="HIGH|CRITICAL",
    ),
    ScenarioOut(
        scenario_id="abandoned-service-account",
        name="THE ABANDONED SERVICE ACCOUNT",
        description=(
            "A service account 240 days inactive with elevated permissions "
            "and access to sensitive resources. Expected: HIGH or CRITICAL."
        ),
        telemetry=UserTelemetryIn(
            email="svc-data-pipeline@example.com",
            role="Data Pipeline Service",
            account_type="service_account",
            last_active_days=240,
            accessed_resources=["customer-pii", "production-database", "kms"],
            failed_login_attempts=3,
            location_anomaly=False,
            privilege_level="service",
        ),
        expected_risk="HIGH|CRITICAL",
    ),
]


def list_scenarios() -> List[ScenarioOut]:
    return SCENARIOS


def get_scenario(scenario_id: str) -> ScenarioOut | None:
    for s in SCENARIOS:
        if s.scenario_id == scenario_id:
            return s
    return None


def random_telemetry() -> UserTelemetryIn:
    """Generate a single random telemetry for the 'Generate random user' button."""
    import random

    names = ["zombie", "phantom", "wraith", "ghoul", "spectre", "ghost", "banshee", "lich"]
    domains = ["example.com", "corp.example.com", "vendor-example.com"]
    roles = [
        ("Sales Engineer", "employee", "standard"),
        ("IT Support", "employee", "elevated"),
        ("Cloud Administrator", "admin", "administrator"),
        ("DevOps Contractor", "contractor", "elevated"),
        ("API Service", "service_account", "service"),
    ]
    role, atype, priv = random.choice(roles)
    resources = random.sample(
        [
            "internal-wiki", "company-chat", "marketing-portal", "analytics-readonly",
            "production-database", "billing", "infrastructure", "iam-admin",
            "secrets-manager", "ssh-bastion", "customer-pii", "kms",
        ],
        k=random.randint(0, 4),
    )
    return UserTelemetryIn(
        email=f"{random.choice(names)}.{random.randint(100, 9999)}@{random.choice(domains)}",
        role=role,
        account_type=atype,
        last_active_days=random.randint(1, 260),
        accessed_resources=resources,
        failed_login_attempts=random.choice([0, 0, 1, 2, 5, 8, 15, 30, 60]),
        location_anomaly=random.random() < 0.35,
        privilege_level=priv,
    )
