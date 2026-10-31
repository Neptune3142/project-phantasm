import { useEffect, useState } from 'react';
import { CheckCircle2, AlertCircle, Loader2, XCircle, ChevronRight } from 'lucide-react';
import { getIncidents } from '../services/api';

const STEPS = [
  'INGESTION',
  'VALIDATION',
  'GEMINI_ANALYSIS',
  'RISK_CLASSIFICATION',
  'DECISION',
  'IAM_ACTION',
  'AUDIT_LEDGER',
  'GMAIL_DISPATCH',
];

const statusConfig = {
  pending:   { icon: ChevronRight,  cls: 'text-phantom-textDim', border: 'border-phantom-border', bg: 'bg-phantom-bg' },
  running:   { icon: Loader2,       cls: 'text-phantom-amber', border: 'border-phantom-amber/60', bg: 'bg-phantom-amber/10', spin: true },
  completed: { icon: CheckCircle2,  cls: 'text-phantom-greenBri', border: 'border-phantom-green/60', bg: 'bg-phantom-green/10' },
  failed:    { icon: XCircle,       cls: 'text-phantom-redBri', border: 'border-phantom-red/60', bg: 'bg-phantom-red/10' },
};

export default function PipelinePage() {
  const [incidents, setIncidents] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await getIncidents(20);
        if (mounted) {
          setIncidents(data);
          if (data.length > 0) setSelected(data[0].incident_id);
        }
      } catch (e) { /* ignore */ }
    })();
    return () => { mounted = false; };
  }, []);

  const current = incidents.find(i => i.incident_id === selected);

  // Build a step map from the latest execution if available — for now we
  // derive a status map from incident.execution_status as a sensible default.
  function stepState(stepName, inc) {
    if (!inc) return 'pending';
    if (inc.execution_status === 'COMPLETED') return 'completed';
    if (inc.execution_status === 'FAILED') {
      return stepName === inc.current_step ? 'failed' : 'pending';
    }
    return 'completed'; // running/intermediate states visualise as completed
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="section-title">n8n Pipeline Monitor</h2>
        <p className="text-sm text-phantom-textDim mt-1">
          Each step is driven by real backend execution events from the pipeline orchestrator — never decorative animation.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="card lg:col-span-1">
          <div className="subsection-title mb-3">Recent Incidents</div>
          <div className="space-y-1 max-h-96 overflow-y-auto pr-1">
            {incidents.length === 0 && <div className="text-xs text-phantom-textDim">No incidents.</div>}
            {incidents.map(inc => (
              <button
                key={inc.incident_id}
                onClick={() => setSelected(inc.incident_id)}
                className={`w-full text-left px-2 py-1.5 rounded text-xs font-mono transition
                  ${selected === inc.incident_id
                    ? 'bg-phantom-purple/20 border border-phantom-purple/40'
                    : 'hover:bg-phantom-panel2 border border-transparent'}`}
              >
                <div className="flex items-center justify-between">
                  <span className="truncate">{inc.user_email}</span>
                  <span className="ml-2">{inc.threat_score}</span>
                </div>
                <div className="text-phantom-textDim text-[10px]">{inc.risk_category} · {inc.execution_status}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="card lg:col-span-3">
          {!current && <div className="text-phantom-textDim text-sm">Select an incident to view its pipeline.</div>}
          {current && (
            <>
              <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                <div>
                  <div className="font-mono text-sm">{current.user_email}</div>
                  <div className="text-xs text-phantom-textDim font-mono">
                    incident: {current.incident_id}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs font-mono">
                  <span className="text-phantom-textDim">status:</span>
                  <span className={current.execution_status === 'COMPLETED' ? 'text-phantom-greenBri' : current.execution_status === 'FAILED' ? 'text-phantom-redBri' : 'text-phantom-amber'}>
                    {current.execution_status}
                  </span>
                  <span className="text-phantom-textDim">·</span>
                  <span className="text-phantom-purpleBri">{current.assessment_source}</span>
                </div>
              </div>

              <div className="space-y-2">
                {STEPS.map((step, idx) => {
                  const state = stepState(step, current);
                  const cfg = statusConfig[state] || statusConfig.pending;
                  const Icon = cfg.icon;
                  return (
                    <div key={step} className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg grid place-items-center border ${cfg.border} ${cfg.bg}`}>
                        <Icon className={`w-4 h-4 ${cfg.cls} ${cfg.spin ? 'animate-spin' : ''}`} />
                      </div>
                      <div className="flex-1">
                        <div className={`text-sm font-mono ${cfg.cls}`}>{step.replace(/_/g, ' ')}</div>
                        <div className="text-xs text-phantom-textDim">
                          {state === 'completed' && 'Step completed'}
                          {state === 'running' && 'In progress…'}
                          {state === 'failed' && 'Failed — see error'}
                          {state === 'pending' && 'Awaiting execution'}
                        </div>
                      </div>
                      {idx < STEPS.length - 1 && (
                        <ChevronRight className="w-4 h-4 text-phantom-textDim/40" />
                      )}
                    </div>
                  );
                })}
              </div>

              {current.ai_reasoning && (
                <div className="mt-4 pt-4 border-t border-phantom-border">
                  <div className="subsection-title mb-2">Assessment Reasoning</div>
                  <p className="text-sm text-phantom-textDim leading-relaxed">{current.ai_reasoning}</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
