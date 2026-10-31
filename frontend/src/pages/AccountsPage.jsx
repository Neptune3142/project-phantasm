import { useEffect, useMemo, useState } from 'react';
import { Search, Skull, RefreshCw } from 'lucide-react';
import { getAccounts, triggerExorcism } from '../services/api';
import { riskChip, statusChip, scoreBadge } from '../components/Badges';

export default function AccountsPage({ simMode }) {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [exorcising, setExorcising] = useState(null);
  const [result, setResult] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const data = await getAccounts();
      setAccounts(data); setErr(null);
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    return accounts.filter(a => {
      if (statusFilter !== 'ALL' && a.account_status !== statusFilter) return false;
      const s = search.trim().toLowerCase();
      if (!s) return true;
      return (
        a.email.toLowerCase().includes(s) ||
        a.role.toLowerCase().includes(s) ||
        a.user_id.toLowerCase().includes(s)
      );
    });
  }, [accounts, search, statusFilter]);

  async function exorcise(userId) {
    setExorcising(userId); setResult(null);
    try {
      const r = await triggerExorcism(userId, { force_simulation: simMode, use_gemini: !simMode });
      setResult({ user_id: userId, ok: true, ...r });
    } catch (e) {
      setResult({ user_id: userId, ok: false, error: e.message });
    } finally {
      setExorcising(null);
      load();
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h2 className="section-title">Ghost Account Monitor</h2>
          <p className="text-sm text-phantom-textDim mt-1">
            Searchable directory of monitored accounts. Click <span className="font-mono text-phantom-redBri">EXORCISE CREDENTIALS</span> to run the full pipeline against an account.
          </p>
        </div>
        <button onClick={load} className="btn-ghost" disabled={loading}>
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      <div className="card">
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-phantom-textDim" />
            <input
              className="input pl-9"
              placeholder="Search by email, role, or user_id…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <select
            className="input w-auto"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="ALL">All statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="FLAGGED">FLAGGED</option>
            <option value="MONITORED">MONITORED</option>
            <option value="PENDING_APPROVAL">PENDING_APPROVAL</option>
            <option value="REVOKED">REVOKED</option>
          </select>
        </div>

        {err && (
          <div className="text-phantom-redBri text-sm mb-3">Error: {err}</div>
        )}

        <div className="overflow-x-auto -mx-2">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-phantom-textDim uppercase tracking-wider text-xs">
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Inactive</th>
                <th className="px-3 py-2">Fails</th>
                <th className="px-3 py-2">Resources</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="text-center py-8 text-phantom-textDim">
                  No accounts. Run scenarios in the Simulation Lab to populate.
                </td></tr>
              )}
              {filtered.map(a => (
                <tr key={a.user_id} className="border-t border-phantom-border/60 hover:bg-phantom-panel2/50 transition">
                  <td className="px-3 py-2 font-mono text-xs">{a.email}</td>
                  <td className="px-3 py-2">{a.role}</td>
                  <td className="px-3 py-2">{a.last_active_days}d</td>
                  <td className="px-3 py-2">{a.failed_login_attempts}</td>
                  <td className="px-3 py-2 text-xs text-phantom-textDim">
                    {(a.accessed_resources || []).slice(0, 3).join(', ')}
                    {(a.accessed_resources || []).length > 3 && ' …'}
                  </td>
                  <td className="px-3 py-2">{statusChip(a.account_status)}</td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => exorcise(a.user_id)}
                      disabled={exorcising === a.user_id}
                      className={`btn-danger ${exorcising === a.user_id ? 'opacity-60' : ''}`}
                    >
                      <Skull className="w-4 h-4" />
                      {exorcising === a.user_id ? 'Exorcising…' : 'Exorcise Credentials'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {result && (
        <div className={`card ${result.ok ? 'border-phantom-green/40' : 'border-phantom-red/40'}`}>
          <div className="flex items-center justify-between">
            <div>
              <div className="subsection-title">Last Exorcism Result</div>
              {result.ok ? (
                <div className="mt-2 text-sm space-y-1">
                  <div>Incident: <span className="font-mono text-xs">{result.incident_id}</span></div>
                  <div>Execution: <span className="font-mono text-xs">{result.execution_id}</span></div>
                  <div>Score: {scoreBadge(result.threat_score, result.risk_category)} {riskChip(result.risk_category)}</div>
                  <div>Recommended action: <span className="font-mono text-phantom-purpleBri">{result.recommended_action}</span></div>
                  <div>Assessment source: <span className="font-mono">{result.assessment_source}</span></div>
                  <div>Final status: {statusChip(result.execution_status)}</div>
                </div>
              ) : (
                <div className="mt-2 text-sm text-phantom-redBri">Error: {result.error}</div>
              )}
            </div>
          </div>
          {result.pipeline && (
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
              {result.pipeline.map((s, i) => (
                <div key={i} className="text-xs bg-phantom-bg border border-phantom-border rounded px-2 py-1.5">
                  <div className="font-mono uppercase tracking-wider">{s.step}</div>
                  <div className={s.status === 'failed' ? 'text-phantom-redBri' : s.status === 'completed' ? 'text-phantom-greenBri' : 'text-phantom-amber'}>
                    {s.status}
                  </div>
                  {s.detail && <div className="text-phantom-textDim mt-0.5 truncate" title={s.detail}>{s.detail}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
