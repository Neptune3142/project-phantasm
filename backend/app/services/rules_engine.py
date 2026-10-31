"""Deterministic rules engine — produces repeatable threat scores.

This is the fallback engine used when Gemini is unavailable, when in
simulation mode without a key, or whenever a deterministic baseline is
required. Identical input → identical output, every time.
"""
from __future__ import annotations

import hashlib
from typing import List

from app.schemas import GeminiAssessment, UserTelemetryIn


# Weights sum to ~95; the remaining 15 is reserved for a "factor synergy"
# bonus applied when 3+ indicators fire at once (real-world signal that the
# account is a true multi-vector zombie).
WEIGHTS = {
    "inactivity": 30,             # days inactive
    "failed_logins": 30,           # failed authentication attempts (cap at 25)
    "privilege": 15,               # role / privilege level
    "resource_sensitivity": 15,    # accessed resources
    "location_anomaly": 15,        # suspicious geo
    "account_type": 5,             # service/contractor risk premium
    "synergy_bonus": 15,           # applied when 3+ indicators fire
}

SENSITIVE_RESOURCES = {
    "production-database", "prod-db", "billing", "payment-gateway",
    "infrastructure", "iam-admin", "secrets-manager", "kms", "ssh-bastion",
    "customer-pii", "hr-system", "source-code-repo",
}

HIGH_RISK_ROLES = {"administrator", "admin", "root", "superuser", "platform-engineer"}
ELEVATED_ROLES = {"contractor", "consultant", "auditor"}


def _norm(value: float, max_value: float) -> float:
    """Normalise value to [0, 1] against an expected maximum."""
    if max_value <= 0:
        return 0.0
    return min(1.0, max(0.0, value / max_value))


def assess(telemetry: UserTelemetryIn) -> GeminiAssessment:
    """Produce a deterministic GeminiAssessment-shaped result."""
    factors: List[str] = []
    score = 0

    # --- Inactivity (capped at 180 days = full weight) ---
    inact = _norm(telemetry.last_active_days, 180)
    score += int(WEIGHTS["inactivity"] * inact)
    if telemetry.last_active_days >= 90:
        factors.append(f"Extended inactivity ({telemetry.last_active_days} days)")
    elif telemetry.last_active_days >= 30:
        factors.append(f"Moderate inactivity ({telemetry.last_active_days} days)")

    # --- Failed logins (capped at 25 attempts) ---
    fails = _norm(telemetry.failed_login_attempts, 25)
    score += int(WEIGHTS["failed_logins"] * fails)
    if telemetry.failed_login_attempts >= 20:
        factors.append(f"Sustained brute-force pattern ({telemetry.failed_login_attempts} failures)")
    elif telemetry.failed_login_attempts >= 5:
        factors.append(f"Repeated failed authentication ({telemetry.failed_login_attempts} failures)")

    # --- Privilege level ---
    if telemetry.privilege_level == "administrator" or telemetry.role.lower() in HIGH_RISK_ROLES:
        score += WEIGHTS["privilege"]
        factors.append(f"Administrator privileges ({telemetry.role})")
    elif telemetry.privilege_level == "elevated" or telemetry.account_type == "contractor":
        score += int(WEIGHTS["privilege"] * 0.6)
        factors.append(f"Elevated / contractor privileges ({telemetry.role})")
    elif telemetry.privilege_level == "service":
        score += int(WEIGHTS["privilege"] * 0.4)
        factors.append("Service account credentials")

    # --- Resource sensitivity ---
    sensitive_hits = [r for r in telemetry.accessed_resources if r.lower() in SENSITIVE_RESOURCES]
    if sensitive_hits:
        score += WEIGHTS["resource_sensitivity"]
        factors.append(f"Access to sensitive resources ({', '.join(sensitive_hits)})")
    elif telemetry.accessed_resources:
        score += int(WEIGHTS["resource_sensitivity"] * 0.3)

    # --- Location anomaly ---
    if telemetry.location_anomaly:
        score += WEIGHTS["location_anomaly"]
        factors.append("Unusual geographic login pattern")

    # --- Account type premium ---
    if telemetry.account_type == "service_account":
        score += WEIGHTS["account_type"]
        factors.append("Service account behaviour")
    elif telemetry.account_type == "contractor":
        score += int(WEIGHTS["account_type"] * 0.6)

    # --- Factor synergy bonus (3+ indicators fire → +15) ---
    indicator_count = sum(1 for f in factors if f)
    if indicator_count >= 3:
        score += WEIGHTS["synergy_bonus"]
        factors.append("Multi-vector zombie signal (3+ concurrent risk indicators)")

    # Clamp + jitter-free deterministic nudge to differentiate identical profiles
    score = max(0, min(100, score))
    if not factors:
        factors.append("No notable risk indicators")

    category = _category(score)
    action = _action(category, telemetry)
    epitaph = _epitaph(telemetry, category)

    return GeminiAssessment(
        threat_score=score,
        risk_category=category,
        reasoning=_reasoning(telemetry, score, factors),
        risk_factors=factors,
        recommended_action=action,
        epitaph_summary=epitaph,
    )


def _category(score: int) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def _action(category: str, telemetry: UserTelemetryIn) -> str:
    if category == "CRITICAL":
        return "REQUIRE_REVOCATION_APPROVAL"
    if category == "HIGH":
        return "REQUIRE_REVOCATION_APPROVAL"
    if category == "MEDIUM":
        return "FLAG"
    return "MONITOR"


def _epitaph(telemetry: UserTelemetryIn, category: str) -> str:
    if category == "CRITICAL":
        return (
            f"{telemetry.email} haunted the perimeter too long. "
            "Its credentials are laid to rest before they could rise again."
        )
    if category == "HIGH":
        return (
            f"{telemetry.email} stirred uneasily in the dark. "
            "We bound it in chains of monitoring before it could claw further."
        )
    if category == "MEDIUM":
        return (
            f"{telemetry.email} murmured in the shadows — "
            "we placed a candle by its grave and watched."
        )
    return (
        f"{telemetry.email} rests quietly in the earth. "
        "No spirits stir, but we keep a lantern lit."
    )


def _reasoning(t: UserTelemetryIn, score: int, factors: List[str]) -> str:
    return (
        f"Deterministic rules-engine assessment for {t.email} "
        f"({t.role}, {t.account_type}). Score={score}/100. "
        f"Indicators: {', '.join(factors)}. "
        f"Inputs — inactive_days={t.last_active_days}, "
        f"failed_logins={t.failed_login_attempts}, "
        f"location_anomaly={t.location_anomaly}, "
        f"resources={t.accessed_resources}."
    )


def deterministic_hash(telemetry: UserTelemetryIn) -> str:
    """Return a short, stable hash for telemetry — used in tests."""
    payload = (
        f"{telemetry.email}|{telemetry.role}|{telemetry.account_type}|"
        f"{telemetry.last_active_days}|{sorted(telemetry.accessed_resources)}|"
        f"{telemetry.failed_login_attempts}|{telemetry.location_anomaly}|{telemetry.privilege_level}"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]
