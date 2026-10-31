// Frontend API client — proxies to FastAPI at /api/v1 via the Vite dev proxy.
const BASE = '/api/v1';

async function jsonOrThrow(resp, fallbackMsg) {
  if (!resp.ok) {
    let detail = fallbackMsg || `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (body && body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }
  const txt = await resp.text();
  if (!txt) return null;
  return JSON.parse(txt);
}

export async function getHealth() {
  const r = await fetch(`${BASE}/health`);
  return jsonOrThrow(r, 'health check failed');
}

export async function getDashboardStats() {
  const r = await fetch(`${BASE}/dashboard/stats`);
  return jsonOrThrow(r, 'failed to load dashboard stats');
}

export async function getIntegrationStatus() {
  const r = await fetch(`${BASE}/integrations/status`);
  return jsonOrThrow(r, 'failed to load integration status');
}

export async function updateCredential(key, value) {
  const r = await fetch(`${BASE}/integrations/credentials`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, value }),
  });
  return jsonOrThrow(r, 'failed to update credential');
}

export async function testIntegration(name) {
  const r = await fetch(`${BASE}/integrations/test/${name}`, { method: 'POST' });
  return jsonOrThrow(r, `failed to test ${name}`);
}

export async function getAccounts() {
  const r = await fetch(`${BASE}/accounts`);
  return jsonOrThrow(r, 'failed to load accounts');
}

export async function createAccount(telemetry) {
  const r = await fetch(`${BASE}/accounts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(telemetry),
  });
  return jsonOrThrow(r, 'failed to create account');
}

export async function triggerExorcism(user_id, opts = {}) {
  const r = await fetch(`${BASE}/trigger-exorcism`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id,
      scenario_id: opts.scenario_id ?? null,
      use_gemini: opts.use_gemini ?? true,
      force_simulation: opts.force_simulation ?? false,
    }),
  });
  return jsonOrThrow(r, 'failed to trigger exorcism');
}

export async function getIncidents(limit = 100) {
  const r = await fetch(`${BASE}/incidents?limit=${limit}`);
  return jsonOrThrow(r, 'failed to load incidents');
}

export async function getIncident(id) {
  const r = await fetch(`${BASE}/incidents/${id}`);
  return jsonOrThrow(r, 'failed to load incident');
}

export async function getExecution(id) {
  const r = await fetch(`${BASE}/executions/${id}`);
  return jsonOrThrow(r, 'failed to load execution');
}

export async function getScenarios() {
  const r = await fetch(`${BASE}/simulation/scenarios`);
  return jsonOrThrow(r, 'failed to load scenarios');
}

export async function runScenario(id) {
  const r = await fetch(`${BASE}/simulation/run/${id}`, { method: 'POST' });
  return jsonOrThrow(r, `failed to run scenario ${id}`);
}

export async function runAllScenarios() {
  const r = await fetch(`${BASE}/simulation/run-all`, { method: 'POST' });
  return jsonOrThrow(r, 'failed to run all scenarios');
}

export async function generateRandomAccount() {
  const r = await fetch(`${BASE}/simulation/generate-random`, { method: 'POST' });
  return jsonOrThrow(r, 'failed to generate random account');
}

export async function resetSimulation() {
  const r = await fetch(`${BASE}/simulation/reset`, { method: 'POST' });
  return jsonOrThrow(r, 'failed to reset simulation');
}

export async function clearHistory() {
  const r = await fetch(`${BASE}/simulation/clear`, { method: 'POST' });
  return jsonOrThrow(r, 'failed to clear history');
}

export async function submitApproval(incident_id, approver, decision, comments = '') {
  const r = await fetch(`${BASE}/approvals/${incident_id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approver, decision, comments }),
  });
  return jsonOrThrow(r, 'failed to submit approval');
}
