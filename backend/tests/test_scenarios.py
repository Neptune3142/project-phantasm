"""Tests for the simulation scenarios — six predefined scenarios produce expected risk levels."""
SCENARIO_EXPECTATIONS = {
    "sleeping-ghost":          {"acceptable": ["LOW", "MEDIUM"]},
    "compromised-contractor":  {"acceptable": ["CRITICAL"]},
    "privileged-phantom":      {"acceptable": ["CRITICAL"]},
    "false-alarm":             {"acceptable": ["LOW"]},
    "brute-force-ghost":       {"acceptable": ["HIGH", "CRITICAL"]},
    "abandoned-service-account": {"acceptable": ["HIGH", "CRITICAL"]},
}


def test_six_scenarios_defined():
    from app.services.simulation_service import list_scenarios
    s = list_scenarios()
    assert len(s) == 6
    expected_ids = set(SCENARIO_EXPECTATIONS.keys())
    actual_ids = {x.scenario_id for x in s}
    assert expected_ids == actual_ids


def test_scenario_lookup():
    from app.services.simulation_service import get_scenario
    s = get_scenario("compromised-contractor")
    assert s is not None
    assert s.name == "THE COMPROMISED CONTRACTOR"
    assert s.telemetry.email == "contractor.devops@vendor-example.com"
    assert s.telemetry.last_active_days == 114


def test_unknown_scenario_returns_none():
    from app.services.simulation_service import get_scenario
    assert get_scenario("does-not-exist") is None


def test_scenarios_pass_when_run(client):
    """Each predefined scenario produces a risk category that matches its expected set."""
    for scenario_id, expected in SCENARIO_EXPECTATIONS.items():
        r = client.post(f"/api/v1/simulation/run/{scenario_id}")
        assert r.status_code == 200, f"{scenario_id}: {r.text}"
        body = r.json()
        assert body["risk_category"] in expected["acceptable"], (
            f"Scenario {scenario_id} produced {body['risk_category']}, "
            f"expected {expected['acceptable']}"
        )
        assert body["pass_"] is True
        assert 0 <= body["threat_score"] <= 100
