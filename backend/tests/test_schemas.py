"""Tests for the GeminiAssessment Pydantic schema — validation logic."""
import pytest
from pydantic import ValidationError

from app.schemas import GeminiAssessment


VALID = {
    "threat_score": 92,
    "risk_category": "CRITICAL",
    "reasoning": "This account has been inactive for 114 days and shows repeated failed authentication attempts.",
    "risk_factors": ["Extended inactivity", "Repeated failed authentication", "Sensitive resources"],
    "recommended_action": "REQUIRE_REVOCATION_APPROVAL",
    "epitaph_summary": "The ghost has overstayed its welcome…",
}


def test_valid_assessment_parses():
    a = GeminiAssessment.model_validate(VALID)
    assert a.threat_score == 92
    assert a.risk_category == "CRITICAL"
    assert len(a.risk_factors) == 3


def test_out_of_range_score_rejected():
    bad = {**VALID, "threat_score": 150}
    with pytest.raises(ValidationError):
        GeminiAssessment.model_validate(bad)
    bad2 = {**VALID, "threat_score": -5}
    with pytest.raises(ValidationError):
        GeminiAssessment.model_validate(bad2)


def test_invalid_risk_category_rejected():
    bad = {**VALID, "risk_category": "EXTREME"}
    with pytest.raises(ValidationError):
        GeminiAssessment.model_validate(bad)


def test_invalid_action_rejected():
    bad = {**VALID, "recommended_action": "DELETE_IMMEDIATELY"}
    with pytest.raises(ValidationError):
        GeminiAssessment.model_validate(bad)


def test_missing_required_field_rejected():
    # Only fields without defaults will raise — risk_factors has default_factory.
    for k in ("threat_score", "risk_category", "reasoning", "recommended_action", "epitaph_summary"):
        bad = {k2: v for k2, v in VALID.items() if k2 != k}
        with pytest.raises(ValidationError):
            GeminiAssessment.model_validate(bad)


def test_short_reasoning_rejected():
    bad = {**VALID, "reasoning": "too short"}
    with pytest.raises(ValidationError):
        GeminiAssessment.model_validate(bad)


def test_risk_factors_deduplicated():
    bad = {**VALID, "risk_factors": ["A", "A", "B", "B"]}
    a = GeminiAssessment.model_validate(bad)
    assert a.risk_factors == ["A", "B"]
