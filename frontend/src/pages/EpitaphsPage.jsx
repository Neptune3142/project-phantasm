import { useEffect, useState } from 'react';
import { Skull, X } from 'lucide-react';
import { getIncidents } from '../services/api';
import { riskChip, statusChip, scoreBadge } from '../components/Badges';

export default function EpitaphsPage() {
  const [incidents, setIncidents] = useState([]);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await getIncidents(200);
        if (mounted) setIncidents(data);
      } catch (e) { /* ignore */ }
    })();
    return () => { mounted = false; };
  }, []);

  const revoked = incidents.filter(i => i.action_taken === 'REVOKED' || i.epitaph_summary);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="section-title flex items-center gap-2">
          <Skull className="w-5 h-5 text-phantom-purpleBri" />
          Epitaph Vault
        </h2>
        <p className="text-sm text-phantom-textDim mt-1">
          Historical incident reports with the generated epitaph for each exorcised credential.
        </p>
      </div>

      {revoked.length === 0 && (
        <div className="card text-phantom-textDim">
          No epitaphs recorded yet. Run scenarios with critical or high risk to populate the vault.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {revoked.map(inc => (
          <button
            key={inc.incident_id}
            onClick={() => setOpen(inc)}
            className="card card-hover text-left flex flex-col gap-3 hover:shadow-glow-purple"
          >
            <div className="flex items-center justify-between">
              <div className="text-2xl">{inc.risk_category === 'CRITICAL' ? '💀' : '👻'}</div>
              {scoreBadge(inc.threat_score, inc.risk_category)}
            </div>
            <div>
              <div className="font-mono text-sm truncate">{inc.user_email}</div>
              <div className="text-xs text-phantom-textDim font-mono">
                {new Date(inc.timestamp).toLocaleString()}
              </div>
            </div>
            <div className="text-xs italic text-phantom-purpleBri/80 line-clamp-2">
              “{inc.epitaph_summary || 'No epitaph generated.'}”
            </div>
            <div className="flex items-center gap-2">
              {riskChip(inc.risk_category)}
              {statusChip(inc.execution_status)}
            </div>
          </button>
        ))}
      </div>

      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm grid place-items-center p-4"
          onClick={() => setOpen(null)}
        >
          <div
            className="bg-phantom-panel border border-phantom-border rounded-xl max-w-2xl w-full p-6 shadow-glow-purple"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="text-3xl mb-1">{open.risk_category === 'CRITICAL' ? '💀' : '👻'}</div>
                <div className="font-mono text-sm">{open.user_email}</div>
                <div className="text-xs text-phantom-textDim font-mono">
                  incident: {open.incident_id}
                </div>
              </div>
              <button onClick={() => setOpen(null)} className="btn-ghost p-1.5">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-4 flex items-center gap-3 flex-wrap">
              {scoreBadge(open.threat_score, open.risk_category)}
              {riskChip(open.risk_category)}
              {statusChip(open.execution_status)}
              <span className="text-xs font-mono text-phantom-textDim">src: {open.assessment_source}</span>
            </div>

            <div className="mt-4">
              <div className="subsection-title mb-1">Reasoning</div>
              <p className="text-sm text-phantom-textDim leading-relaxed">{open.ai_reasoning || '—'}</p>
            </div>

            <div className="mt-3">
              <div className="subsection-title mb-1">Risk Factors</div>
              <div className="flex flex-wrap gap-1.5">
                {(open.risk_factors || []).map((f, i) => (
                  <span key={i} className="text-xs bg-phantom-bg border border-phantom-border rounded px-2 py-0.5 font-mono">
                    {f}
                  </span>
                ))}
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="subsection-title">Recommended</div>
                <div className="font-mono text-phantom-purpleBri">{open.recommended_action}</div>
              </div>
              <div>
                <div className="subsection-title">Action Taken</div>
                <div className="font-mono text-phantom-text">{open.action_taken || '—'}</div>
              </div>
            </div>

            <div className="mt-5 p-4 rounded-lg bg-phantom-bg border-l-2 border-phantom-purple/60">
              <div className="subsection-title mb-2">Epitaph</div>
              <p className="italic text-phantom-purpleBri/90 leading-relaxed">
                {open.epitaph_summary || '—'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
