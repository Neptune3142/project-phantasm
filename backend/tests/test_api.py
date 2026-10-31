"""Tests for the API endpoints — accounts, exorcism, incidents, dashboard."""
from app.schemas import UserTelemetryIn

# A minimal telemetry used to create test accounts.
SAMPLE_TELEMETRY = {
    "email": "test.user@example.com",
    "role": "Backend Developer",
    "account_type": "employee",
    "last_active_days": 60,
    "accessed_resources": ["internal-wiki"],
    "failed_login_attempts": 1,
    "location_anomaly": False,
    "privilege_level": "standard",
}


def test_health_endpoint(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "project-phantasm"


def test_create_account(client):
    r = client.post("/api/v1/accounts", json=SAMPLE_TELEMETRY)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "test.user@example.com"
    assert body["account_status"] == "ACTIVE"
    assert "user_id" in body


def test_list_accounts(client):
    # Create two accounts
    client.post("/api/v1/accounts", json=SAMPLE_TELEMETRY)
    client.post("/api/v1/accounts", json={**SAMPLE_TELEMETRY, "email": "second.user@example.com"})
    r = client.get("/api/v1/accounts")
    assert r.status_code == 200
    accounts = r.json()
    assert isinstance(accounts, list)
    assert len(accounts) >= 2
    assert all("user_id" in a for a in accounts)


def test_get_account_by_id(client):
    r = client.post("/api/v1/accounts", json=SAMPLE_TELEMETRY)
    user_id = r.json()["user_id"]
    r = client.get(f"/api/v1/accounts/{user_id}")
    assert r.status_code == 200
    assert r.json()["user_id"] == user_id


def test_get_account_not_found(client):
    r = client.get("/api/v1/accounts/nonexistent")
    assert r.status_code == 404


def test_invalid_telemetry_rejected(client):
    bad = {**SAMPLE_TELEMETRY, "last_active_days": -10}
    r = client.post("/api/v1/accounts", json=bad)
    assert r.status_code == 422


def test_dashboard_stats_empty(client):
    r = client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total_accounts"] == 0
    assert body["total_incidents"] == 0
    assert body["simulation_mode"] is True


def test_run_all_scenarios_returns_six(client):
    r = client.post("/api/v1/simulation/run-all")
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)
    assert len(results) == 6
    for result in results:
        assert "scenario_id" in result
        assert "threat_score" in result
        assert "risk_category" in result
        assert "pass_" in result
        assert 0 <= result["threat_score"] <= 100


def test_run_single_scenario(client):
    r = client.post("/api/v1/simulation/run/compromised-contractor")
    assert r.status_code == 200
    body = r.json()
    assert body["scenario_id"] == "compromised-contractor"
    assert body["risk_category"] in ("CRITICAL",)
    assert body["pass_"] is True


def test_run_unknown_scenario_404(client):
    r = client.post("/api/v1/simulation/run/nonexistent")
    assert r.status_code == 404


def test_trigger_exorcism_creates_incident(client):
    r = client.post("/api/v1/accounts", json=SAMPLE_TELEMETRY)
    user_id = r.json()["user_id"]
    r = client.post("/api/v1/trigger-exorcism", json={"user_id": user_id, "force_simulation": True, "use_gemini": False})
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == user_id
    assert body["execution_status"] in ("COMPLETED", "FAILED")
    assert "incident_id" in body
    assert "pipeline" in body
    assert len(body["pipeline"]) >= 6  # at least 6 step records


def test_trigger_exorcism_user_not_found(client):
    r = client.post("/api/v1/trigger-exorcism", json={"user_id": "nonexistent"})
    assert r.status_code == 404


def test_incidents_listed_after_run(client):
    client.post("/api/v1/simulation/run/sleeping-ghost")
    r = client.get("/api/v1/incidents")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_get_incident_by_id(client):
    r = client.post("/api/v1/simulation/run/sleeping-ghost")
    incident_id = r.json()["incident_id"]
    r = client.get(f"/api/v1/incidents/{incident_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["incident_id"] == incident_id
    assert body["user_email"] == "alex.morgan@example.com"


def test_get_execution_by_id(client):
    r = client.post("/api/v1/simulation/run/compromised-contractor")
    execution_id = r.json()["execution_id"]
    r = client.get(f"/api/v1/executions/{execution_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["execution_id"] == execution_id
    assert "step_history" in body
    assert len(body["step_history"]) >= 6
    assert body["workflow_status"] in ("COMPLETED", "FAILED")


def test_integration_status(client):
    r = client.get("/api/v1/integrations/status")
    assert r.status_code == 200
    body = r.json()
    for k in ("gemini", "n8n", "google_sheets", "gmail"):
        assert k in body
        assert "configured" in body[k]


def test_simulation_reset_clears_account_status(client):
    # Run a scenario that flags an account, then reset.
    client.post("/api/v1/simulation/run/compromised-contractor")
    r = client.post("/api/v1/simulation/reset")
    assert r.status_code == 200
    # All accounts should be ACTIVE again
    accounts = client.get("/api/v1/accounts").json()
    for a in accounts:
        assert a["account_status"] == "ACTIVE"


def test_clear_history_removes_incidents(client):
    client.post("/api/v1/simulation/run/sleeping-ghost")
    r = client.post("/api/v1/simulation/clear")
    assert r.status_code == 200
    incidents = client.get("/api/v1/incidents").json()
    assert len(incidents) == 0


def test_generate_random_account(client):
    r = client.post("/api/v1/simulation/generate-random")
    assert r.status_code == 200
    body = r.json()
    assert "@" in body["email"]
    assert body["account_status"] == "ACTIVE"
