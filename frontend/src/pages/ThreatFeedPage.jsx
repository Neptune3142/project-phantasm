import { useEffect, useState } from 'react';
import { Radio } from 'lucide-react';
import { getIncidents } from '../services/api';
import { riskChip, statusChip, scoreBadge } from '../components/Badges';

export default function ThreatFeedPage() {
  const [incidents, setIncidents] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await getIncidents(50);
        if (mounted) { setIncidents(data); setErr(null); }
      } catch (e) { if (mounted) setErr(e.message); }
    })();
    const id = setInterval(async () => {
      try {
        const data = await getIncidents(50);
        if (mounted) { setIncidents(data); setErr(null); }
      } catch (e) { /* ignore poll errors */ }
    }, 8000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="section-title flex items-center gap-2">
          <Radio className="w-4 h-4 text-phantom-greenBri animate-pulse" />
          Threat Intelligence Feed
        </h2>
        <p className="text-sm text-phantom-textDim mt-1">
          Live stream of incident assessments — Gemini reasoning or deterministic rules-engine output, with recommended security actions.
        </p>
      </div>

      {err && <div className="card text-phantom-redBri">Error: {err}</div>}

      <div className="space-y-3">
        {incidents.length === 0 && (
          <div className="card text-phantom-textDim">No incidents yet. Run a scenario to populate the feed.</div>
        )}
        {incidents.map(inc => (
          <div key={inc.incident_id} className="card card-hover">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-3">
                <div className="text-2xl">{inc.risk_category === 'CRITICAL' ? '💀' : inc.risk_category === 'HIGH' ? '👻' : inc.risk_category === 'MEDIUM' ? '🕯️' : '🍃'}</div>
                <div>
                  <div className="font-mono text-sm">{inc.user_email}</div>
                  <div className="text-xs text-phantom-textDim font-mono">
                    {new Date(inc.timestamp).toLocaleString()} · src={inc.assessment_source} · sim={String(inc.simulation_mode)}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {scoreBadge(inc.threat_score, inc.risk_category)}
                {riskChip(inc.risk_category)}
                {statusChip(inc.execution_status)}
              </div>
            </div>
            <div className="mt-3 text-sm text-phantom-textDim leading-relaxed">
              <span className="text-phantom-text font-medium">Reasoning:</span> {inc.ai_reasoning || '—'}
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {(inc.risk_factors || []).map((f, i) => (
                <span key={i} className="text-xs bg-phantom-bg border border-phantom-border rounded px-2 py-0.5 font-mono text-phantom-textDim">
                  {f}
                </span>
              ))}
            </div>
            <div className="mt-3 flex items-center gap-4 text-xs">
              <div>
                <span className="text-phantom-textDim">Recommended: </span>
                <span className="font-mono text-phantom-purpleBri">{inc.recommended_action}</span>
              </div>
              <div>
                <span className="text-phantom-textDim">Action taken: </span>
                <span className="font-mono text-phantom-text">{inc.action_taken || '—'}</span>
              </div>
            </div>
            {inc.epitaph_summary && (
              <div className="mt-3 text-xs italic text-phantom-purpleBri/80 border-l-2 border-phantom-purple/40 pl-3">
                “{inc.epitaph_summary}”
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
