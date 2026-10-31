"""Tests for Gemini service — fallback behaviour, validation, test connection."""
import asyncio
import pytest

from app.services.gemini_service import GeminiService
from app.services import rules_engine
from app.schemas import UserTelemetryIn


def _telemetry():
    return UserTelemetryIn(
        email="test@example.com",
        role="Engineer",
        account_type="employee",
        last_active_days=120,
        accessed_resources=["internal-wiki"],
        failed_login_attempts=2,
        location_anomaly=False,
        privilege_level="standard",
    )


def test_no_gemini_key_falls_back_to_rules_engine():
    """When no API key is configured, GeminiService must use the rules engine."""
    from app.config import Settings
    s = Settings(gemini_api_key=None)
    svc = GeminiService(settings=s)
    out = asyncio.get_event_loop().run_until_complete(svc.assess(_telemetry()))
    expected = rules_engine.assess(_telemetry())
    assert out.threat_score == expected.threat_score
    assert out.risk_category == expected.risk_category


def test_connection_test_returns_helpful_message_without_key():
    from app.config import Settings
    svc = GeminiService(settings=Settings(gemini_api_key=None))
    result = asyncio.get_event_loop().run_until_complete(svc.test_connection())
    assert result["connected"] is False
    assert "GEMINI_API_KEY" in result["detail"]


def test_validation_rejects_malformed_response():
    """Validation helper must return None for invalid dicts."""
    bad = {"threat_score": 200, "risk_category": "EXTREME"}
    assert GeminiService._validate(bad) is None


def test_validation_accepts_well_formed_response():
    good = {
        "threat_score": 42,
        "risk_category": "MEDIUM",
        "reasoning": "This account shows moderate risk due to inactivity and limited failed logins.",
        "risk_factors": ["inactivity"],
        "recommended_action": "FLAG",
        "epitaph_summary": "It stirs quietly.",
    }
    a = GeminiService._validate(good)
    assert a is not None
    assert a.threat_score == 42
    assert a.risk_category == "MEDIUM"


def test_extract_text_handles_valid_payload():
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"threat_score": 50, "risk_category": "HIGH", '
                                    '"reasoning": "Test reasoning sufficient length", '
                                    '"risk_factors": ["x"], "recommended_action": "FLAG", '
                                    '"epitaph_summary": "epitaph text"}'
                        }
                    ]
                },
                "finishReason": "STOP",
                "index": 0,
                "safetyRatings": [],
            }
        ]
    }
    parsed = GeminiService._extract_text(payload)
    assert parsed["threat_score"] == 50
    assert parsed["risk_category"] == "HIGH"


def test_extract_text_raises_on_empty_candidates():
    import pytest
    with pytest.raises(RuntimeError):
        GeminiService._extract_text({"candidates": []})
