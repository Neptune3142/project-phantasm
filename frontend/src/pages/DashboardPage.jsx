import { useEffect, useState } from 'react';
import {
  Activity, AlertTriangle, ShieldCheck, ShieldX, Skull, Users, Eye, ListChecks,
} from 'lucide-react';
import {
  BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, LineChart, Line,
} from 'recharts';
import StatCard from '../components/StatCard';
import { getDashboardStats, getIncidents, getAccounts } from '../services/api';

const COLORS = ['#22C55E', '#F59E0B', '#F87171', '#7C3AED'];

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [s, inc, acc] = await Promise.all([
          getDashboardStats(), getIncidents(50), getAccounts(),
        ]);
        if (mounted) {
          setStats(s); setIncidents(inc); setAccounts(acc); setErr(null);
        }
      } catch (e) {
        if (mounted) setErr(e.message);
      }
    })();
    return () => { mounted = false; };
  }, []);

  if (err) {
    return (
      <div className="card text-phantom-redBri">
        <AlertTriangle className="inline w-4 h-4 mr-2" />
        Failed to load dashboard: {err}
      </div>
    );
  }
  if (!stats) return <div className="card">Loading dashboard…</div>;

  // Build chart data
  const dist = (['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']).map(k => ({
    name: k,
    value: incidents.filter(i => i.risk_category === k).length,
  }));
  const statusDist = (['ACTIVE', 'FLAGGED', 'MONITORED', 'PENDING_APPROVAL', 'REVOKED']).map(k => ({
    name: k,
    value: accounts.filter(a => a.account_status === k).length,
  })).filter(d => d.value > 0);

  // Risk score trend over incidents (chronological)
  const trend = [...incidents].reverse().slice(-20).map((i, idx) => ({
    name: `#${idx + 1}`,
    score: i.threat_score,
    source: i.assessment_source,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="section-title">Operational Overview</h2>
        <p className="text-sm text-phantom-textDim mt-1">
          Real-time snapshot of the zombie-credential exorcism pipeline.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<Users className="w-5 h-5" />} label="Monitored Accounts" value={stats.total_accounts} accent="purple" />
        <StatCard icon={<ShieldCheck className="w-5 h-5" />} label="Active" value={stats.active_accounts} accent="green" />
        <StatCard icon={<Eye className="w-5 h-5" />} label="Inactive (30d+)" value={stats.inactive_accounts} accent="amber" />
        <StatCard icon={<AlertTriangle className="w-5 h-5" />} label="Flagged" value={stats.flagged_accounts} accent="amber" />
        <StatCard icon={<Skull className="w-5 h-5" />} label="Critical Threats" value={stats.critical_threats} accent="red" />
        <StatCard icon={<ShieldX className="w-5 h-5" />} label="Credentials Revoked" value={stats.credentials_revoked} accent="red" />
        <StatCard icon={<ListChecks className="w-5 h-5" />} label="Total Incidents" value={stats.total_incidents} accent="purple" />
        <StatCard icon={<Activity className="w-5 h-5" />} label="System Status" value={stats.system_status.split(' ')[0]} accent={stats.simulation_mode ? 'amber' : 'green'} sub={stats.simulation_mode ? 'simulation mode' : 'live mode'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card">
          <div className="subsection-title mb-3">Threat Distribution</div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={dist} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={75} innerRadius={45} paddingAngle={2}>
                {dist.map((d, i) => <Cell key={i} fill={COLORS[i]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#140F1B', border: '1px solid #2A1F3C', borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 12, color: '#9A8DB0' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card lg:col-span-2">
          <div className="subsection-title mb-3">Risk Score Trend (last 20 incidents)</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A1F3C" />
              <XAxis dataKey="name" stroke="#9A8DB0" fontSize={11} />
              <YAxis stroke="#9A8DB0" fontSize={11} domain={[0, 100]} />
              <Tooltip contentStyle={{ background: '#140F1B', border: '1px solid #2A1F3C', borderRadius: 8 }} />
              <Line type="monotone" dataKey="score" stroke="#A855F7" strokeWidth={2} dot={{ fill: '#A855F7', r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card lg:col-span-2">
          <div className="subsection-title mb-3">Incident History</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={dist}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2A1F3C" />
              <XAxis dataKey="name" stroke="#9A8DB0" fontSize={11} />
              <YAxis stroke="#9A8DB0" fontSize={11} />
              <Tooltip contentStyle={{ background: '#140F1B', border: '1px solid #2A1F3C', borderRadius: 8 }} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {dist.map((d, i) => <Cell key={i} fill={COLORS[i]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <div className="subsection-title mb-3">Account Status Distribution</div>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={statusDist} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
                {statusDist.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#140F1B', border: '1px solid #2A1F3C', borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#9A8DB0' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
