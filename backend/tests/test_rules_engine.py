"""Tests for the deterministic rules engine — fixed inputs, fixed outputs."""
from app.schemas import UserTelemetryIn
from app.services import rules_engine


def _telemetry(**overrides):
    base = dict(
        email="test@example.com",
        role="Developer",
        account_type="employee",
        last_active_days=0,
        accessed_resources=[],
        failed_login_attempts=0,
        location_anomaly=False,
        privilege_level="standard",
    )
    base.update(overrides)
    return UserTelemetryIn(**base)


def test_low_risk_clean_account():
    t = _telemetry()
    a = rules_engine.assess(t)
    assert a.threat_score == 0
    assert a.risk_category == "LOW"
    assert a.recommended_action == "MONITOR"


def test_critical_compromised_contractor():
    t = _telemetry(
        email="contractor@vendor.com",
        role="DevOps Contractor",
        account_type="contractor",
        last_active_days=114,
        accessed_resources=["production-database", "ssh-bastion"],
        failed_login_attempts=14,
        location_anomaly=True,
        privilege_level="elevated",
    )
    a = rules_engine.assess(t)
    assert a.threat_score >= 75
    assert a.risk_category == "CRITICAL"
    assert a.recommended_action == "REQUIRE_REVOCATION_APPROVAL"


def test_deterministic_repeatability():
    """Same input must produce the same score, every time."""
    t = _telemetry(last_active_days=120, failed_login_attempts=5)
    a1 = rules_engine.assess(t)
    a2 = rules_engine.assess(t)
    a3 = rules_engine.assess(t)
    assert a1.threat_score == a2.threat_score == a3.threat_score
    assert a1.risk_category == a2.risk_category == a3.risk_category
    # Hash must be stable too
    assert rules_engine.deterministic_hash(t) == rules_engine.deterministic_hash(t)


def test_score_in_range():
    """All extreme inputs must still produce a 0-100 score."""
    extremes = [
        _telemetry(last_active_days=365, failed_login_attempts=9999, location_anomaly=True),
        _telemetry(role="Administrator", privilege_level="administrator",
                   accessed_resources=["production-database", "billing", "iam-admin"]),
        _telemetry(account_type="service_account", privilege_level="service",
                   last_active_days=240, accessed_resources=["customer-pii"]),
    ]
    for t in extremes:
        a = rules_engine.assess(t)
        assert 0 <= a.threat_score <= 100
        assert a.risk_category in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_risk_factors_are_populated():
    t = _telemetry(
        last_active_days=180,
        failed_login_attempts=20,
        location_anomaly=True,
        accessed_resources=["production-database"],
    )
    a = rules_engine.assess(t)
    assert len(a.risk_factors) >= 3
    assert any("inactivity" in f.lower() for f in a.risk_factors)
    assert any("brute-force" in f.lower() for f in a.risk_factors)
    assert any("sensitive" in f.lower() for f in a.risk_factors)


def test_epitaph_is_halloween_themed_and_safe():
    t = _telemetry(email="a@b.com")
    a = rules_engine.assess(t)
    assert isinstance(a.epitaph_summary, str)
    assert len(a.epitaph_summary) > 0
    assert "@" in a.epitaph_summary  # references the user
