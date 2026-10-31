import { useEffect, useState } from 'react';
import { Beaker, FlaskConical, Play, RotateCcw, Trash2, Dices, Check, X } from 'lucide-react';
import { getScenarios, runScenario, runAllScenarios, generateRandomAccount, resetSimulation, clearHistory, getAccounts } from '../services/api';
import { riskChip, scoreBadge } from '../components/Badges';

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState([]);
  const [results, setResults] = useState({});
  const [running, setRunning] = useState(null);
  const [msg, setMsg] = useState(null);
  const [accounts, setAccounts] = useState([]);

  async function loadScenarios() {
    try {
      const s = await getScenarios();
      setScenarios(s);
    } catch (e) { setMsg({ kind: 'error', text: e.message }); }
  }
  async function loadAccounts() {
    try { setAccounts(await getAccounts()); } catch (e) { /* ignore */ }
  }
  useEffect(() => { loadScenarios(); loadAccounts(); }, []);

  async function runOne(id) {
    setRunning(id);
    try {
      const r = await runScenario(id);
      setResults(prev => ({ ...prev, [id]: r }));
      setMsg({ kind: 'success', text: `Scenario '${id}' ran: ${r.risk_category} (score ${r.threat_score})` });
    } catch (e) {
      setMsg({ kind: 'error', text: e.message });
    } finally {
      setRunning(null);
      loadAccounts();
    }
  }

  async function runAll() {
    setRunning('ALL');
    try {
      const results = await runAllScenarios();
      const map = {};
      results.forEach(r => { map[r.scenario_id] = r; });
      setResults(map);
      const passCount = results.filter(r => r.pass_).length;
      setMsg({ kind: 'success', text: `Ran ${results.length} scenarios. ${passCount} passed.` });
    } catch (e) {
      setMsg({ kind: 'error', text: e.message });
    } finally {
      setRunning(null);
      loadAccounts();
    }
  }

  async function genRandom() {
    try {
      await generateRandomAccount();
      setMsg({ kind: 'success', text: 'Generated a random account.' });
      loadAccounts();
    } catch (e) { setMsg({ kind: 'error', text: e.message }); }
  }

  async function reset() {
    try {
      await resetSimulation();
      setMsg({ kind: 'success', text: 'All accounts reset to ACTIVE.' });
      loadAccounts();
    } catch (e) { setMsg({ kind: 'error', text: e.message }); }
  }

  async function clearAll() {
    if (!confirm('Clear ALL historical simulation data (incidents, executions, approvals)?')) return;
    try {
      await clearHistory();
      setResults({});
      setMsg({ kind: 'success', text: 'Historical simulation data cleared.' });
      loadAccounts();
    } catch (e) { setMsg({ kind: 'error', text: e.message }); }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h2 className="section-title flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-phantom-amber" />
            Simulation Lab
          </h2>
          <p className="text-sm text-phantom-textDim mt-1">
            Six predefined zombie-credential scenarios. Runs the same pipeline as live mode but with deterministic rules-engine assessment.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={runAll} disabled={running === 'ALL'} className="btn-primary">
            <Play className={`w-4 h-4 ${running === 'ALL' ? 'animate-spin' : ''}`} /> Run All Scenarios
          </button>
          <button onClick={genRandom} className="btn-ghost">
            <Dices className="w-4 h-4" /> Generate Random
          </button>
          <button onClick={reset} className="btn-ghost">
            <RotateCcw className="w-4 h-4" /> Reset Accounts
          </button>
          <button onClick={clearAll} className="btn-ghost">
            <Trash2 className="w-4 h-4" /> Clear History
          </button>
        </div>
      </div>

      {msg && (
        <div className={`card ${msg.kind === 'success' ? 'border-phantom-green/40 text-phantom-greenBri' : 'border-phantom-red/40 text-phantom-redBri'}`}>
          {msg.text}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {scenarios.map(s => {
          const r = results[s.scenario_id];
          return (
            <div key={s.scenario_id} className="card card-hover flex flex-col gap-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-display text-base font-semibold text-phantom-text">{s.name}</div>
                  <div className="text-xs font-mono text-phantom-textDim mt-1">{s.scenario_id}</div>
                </div>
                <div className="text-xs font-mono text-phantom-textDim px-2 py-0.5 rounded-full bg-phantom-bg border border-phantom-border">
                  expected: {s.expected_risk}
                </div>
              </div>
              <p className="text-xs text-phantom-textDim leading-relaxed">{s.description}</p>
              <div className="text-xs space-y-1 font-mono">
                <div><span className="text-phantom-textDim">email:</span> {s.telemetry.email}</div>
                <div><span className="text-phantom-textDim">role:</span> {s.telemetry.role}</div>
                <div><span className="text-phantom-textDim">type:</span> {s.telemetry.account_type}</div>
                <div><span className="text-phantom-textDim">inactive:</span> {s.telemetry.last_active_days}d</div>
                <div><span className="text-phantom-textDim">failed:</span> {s.telemetry.failed_login_attempts}</div>
                <div><span className="text-phantom-textDim">geo anomaly:</span> {String(s.telemetry.location_anomaly)}</div>
                <div><span className="text-phantom-textDim">resources:</span> {(s.telemetry.accessed_resources || []).join(', ') || 'none'}</div>
              </div>
              <div className="mt-auto flex items-center justify-between">
                <button
                  onClick={() => runOne(s.scenario_id)}
                  disabled={running === s.scenario_id}
                  className={`btn-primary ${running === s.scenario_id ? 'opacity-60' : ''}`}
                >
                  <Beaker className={`w-4 h-4 ${running === s.scenario_id ? 'animate-spin' : ''}`} />
                  {running === s.scenario_id ? 'Running…' : 'Run Scenario'}
                </button>
                {r && (
                  <div className="flex items-center gap-2">
                    {scoreBadge(r.threat_score, r.risk_category)}
                    {riskChip(r.risk_category)}
                    {r.pass_ ? (
                      <span className="text-phantom-greenBri"><Check className="w-4 h-4" /></span>
                    ) : (
                      <span className="text-phantom-redBri"><X className="w-4 h-4" /></span>
                    )}
                  </div>
                )}
              </div>
              {r && (
                <div className="text-xs text-phantom-textDim">
                  Source: <span className="font-mono text-phantom-purpleBri">{r.assessment_source}</span> · Incident: <span className="font-mono">{r.incident_id.slice(0, 8)}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="card">
        <div className="subsection-title mb-3">Active Accounts ({accounts.length})</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-phantom-textDim uppercase text-xs tracking-wider">
                <th className="px-2 py-1">Email</th>
                <th className="px-2 py-1">Role</th>
                <th className="px-2 py-1">Inactive</th>
                <th className="px-2 py-1">Fails</th>
                <th className="px-2 py-1">Status</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map(a => (
                <tr key={a.user_id} className="border-t border-phantom-border/60">
                  <td className="px-2 py-1 font-mono text-xs">{a.email}</td>
                  <td className="px-2 py-1">{a.role}</td>
                  <td className="px-2 py-1">{a.last_active_days}d</td>
                  <td className="px-2 py-1">{a.failed_login_attempts}</td>
                  <td className="px-2 py-1">
                    <span className={`chip ${
                      a.account_status === 'ACTIVE' ? 'bg-phantom-green/15 text-phantom-greenBri' :
                      a.account_status === 'REVOKED' ? 'bg-phantom-red/20 text-phantom-redBri' :
                      'bg-phantom-amber/15 text-phantom-amber'
                    }`}>{a.account_status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
