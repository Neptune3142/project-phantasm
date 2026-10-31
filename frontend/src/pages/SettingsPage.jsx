import { useEffect, useState } from 'react';
import { Plug, Save, Zap, Check, X, Loader2, ExternalLink, KeyRound } from 'lucide-react';
import { getIntegrationStatus, updateCredential, testIntegration } from '../services/api';

const CREDENTIAL_FIELDS = [
  { key: 'GEMINI_API_KEY',   label: 'Gemini API Key',      group: 'gemini', help: 'https://aistudio.google.com/app/apikey', type: 'password' },
  { key: 'GEMINI_MODEL',     label: 'Gemini Model',        group: 'gemini', help: 'https://ai.google.dev/gemini-api/docs/models', type: 'text' },
  { key: 'N8N_WEBHOOK_URL',  label: 'n8n Webhook URL',     group: 'n8n',    help: 'http://localhost:5679/webhook/phantasm-exorcism', type: 'text' },
  { key: 'N8N_BASE_URL',     label: 'n8n Base URL',         group: 'n8n',    help: 'http://localhost:5679', type: 'text' },
  { key: 'N8N_API_KEY',      label: 'n8n API Key (optional)', group: 'n8n', help: 'Settings → n8n API', type: 'password' },
  { key: 'GOOGLE_CLIENT_ID',     label: 'Google Client ID',     group: 'google', help: 'console.cloud.google.com/apis/credentials', type: 'text' },
  { key: 'GOOGLE_CLIENT_SECRET', label: 'Google Client Secret', group: 'google', help: 'console.cloud.google.com/apis/credentials', type: 'password' },
  { key: 'GOOGLE_REFRESH_TOKEN', label: 'Google Refresh Token', group: 'google', help: 'OAuth playground flow', type: 'password' },
  { key: 'GOOGLE_SHEET_ID',      label: 'Google Sheet ID',      group: 'google', help: 'The long ID in your Sheet URL', type: 'text' },
  { key: 'GMAIL_SENDER',     label: 'Gmail Sender',    group: 'gmail', help: 'e.g. phantasm@your-domain.com', type: 'text' },
  { key: 'GMAIL_RECIPIENT',  label: 'Gmail Recipient', group: 'gmail', help: 'e.g. security-team@your-domain.com', type: 'text' },
  { key: 'SIMULATION_MODE', label: 'Simulation Mode (true/false)', group: 'app', help: 'true | false', type: 'text' },
];

const GROUP_LABEL = {
  gemini: 'Google Gemini',
  n8n:    'n8n Automation',
  google: 'Google Sheets / Gmail',
  gmail:  'Gmail',
  app:    'Application',
};

export default function SettingsPage() {
  const [status, setStatus] = useState(null);
  const [vals, setVals] = useState({});
  const [testing, setTesting] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [msg, setMsg] = useState(null);

  async function loadStatus() {
    try {
      const s = await getIntegrationStatus();
      setStatus(s);
    } catch (e) { setMsg({ kind: 'error', text: e.message }); }
  }
  useEffect(() => { loadStatus(); }, []);

  async function save(key) {
    const value = vals[key];
    if (value === undefined) return;
    try {
      await updateCredential(key, value);
      setMsg({ kind: 'success', text: `Updated ${key}. Masked value will be visible on next status refresh.` });
      setVals(v => ({ ...v, [key]: '' }));
      loadStatus();
    } catch (e) { setMsg({ kind: 'error', text: e.message }); }
  }

  async function test(name) {
    setTesting(name);
    try {
      const r = await testIntegration(name);
      setTestResults(prev => ({ ...prev, [name]: r }));
    } catch (e) {
      setTestResults(prev => ({ ...prev, [name]: { connected: false, detail: e.message } }));
    } finally {
      setTesting(null);
      loadStatus();
    }
  }

  function renderIntegrationCard(name, label, data) {
    return (
      <div className="card">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Plug className={`w-4 h-4 ${data?.configured ? 'text-phantom-greenBri' : 'text-phantom-textDim'}`} />
            <span className="font-semibold">{label}</span>
          </div>
          {data?.configured
            ? <span className="chip bg-phantom-green/15 text-phantom-greenBri"><Check className="w-3 h-3" /> configured</span>
            : <span className="chip bg-phantom-bg text-phantom-textDim border border-phantom-border"><X className="w-3 h-3" /> disconnected</span>}
        </div>
        <div className="text-xs text-phantom-textDim font-mono mb-2">
          {data?.masked_value || '—'} {data?.hint ? `· ${data.hint}` : ''}
        </div>
        <button
          onClick={() => test(name)}
          disabled={testing === name}
          className="btn-ghost text-xs"
        >
          {testing === name ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
          Test {name} connection
        </button>
        {testResults[name] && (
          <div className={`mt-2 text-xs ${testResults[name].connected ? 'text-phantom-greenBri' : 'text-phantom-redBri'}`}>
            {testResults[name].connected ? '✓' : '✕'} {testResults[name].detail}
            {testResults[name].suggestion && (
              <div className="mt-1 text-phantom-textDim">{testResults[name].suggestion}</div>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="section-title">Integrations & Credentials</h2>
        <p className="text-sm text-phantom-textDim mt-1">
          Configure your real API keys here. Credentials are stored in the backend <span className="font-mono">.env</span> file and never returned in full to the frontend.
        </p>
      </div>

      {msg && (
        <div className={`card ${msg.kind === 'success' ? 'border-phantom-green/40 text-phantom-greenBri' : 'border-phantom-red/40 text-phantom-redBri'}`}>
          {msg.text}
        </div>
      )}

      {status && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {renderIntegrationCard('gemini', 'Gemini AI', status.gemini)}
          {renderIntegrationCard('n8n',    'n8n Automation', status.n8n)}
          {renderIntegrationCard('google','Google Sheets', status.google_sheets)}
          {renderIntegrationCard('gmail', 'Gmail', status.gmail)}
        </div>
      )}

      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <KeyRound className="w-4 h-4 text-phantom-purpleBri" />
          <h3 className="subsection-title">Credential Configuration</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {CREDENTIAL_FIELDS.map(field => (
            <div key={field.key} className="space-y-1.5">
              <label className="label">
                {field.label}
                <a
                  href={field.help.startsWith('http') ? field.help : '#'}
                  target="_blank"
                  rel="noreferrer"
                  className="ml-2 text-phantom-textDim/70 hover:text-phantom-purpleBri inline-flex items-center"
                >
                  <ExternalLink className="w-3 h-3" />
                </a>
              </label>
              <div className="flex gap-2">
                <input
                  type={field.type === 'password' ? 'password' : 'text'}
                  className="input"
                  placeholder={field.help}
                  value={vals[field.key] ?? ''}
                  onChange={e => setVals(v => ({ ...v, [field.key]: e.target.value }))}
                />
                <button
                  onClick={() => save(field.key)}
                  disabled={!vals[field.key]}
                  className={`btn-primary ${!vals[field.key] ? 'opacity-60' : ''}`}
                >
                  <Save className="w-3.5 h-3.5" /> Save
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card text-xs text-phantom-textDim leading-relaxed">
        <div className="font-semibold text-phantom-text mb-1">How credentials are stored</div>
        <p>
          Credentials entered here are written to <span className="font-mono text-phantom-purpleBri">backend/.env</span> and re-loaded
          by the FastAPI process immediately. They are <strong>never</strong> returned to the frontend in clear text — only a masked
          preview like <span className="font-mono">ABCD…WXYZ</span> is shown in the integration status panel. The <span className="font-mono">.env</span> file
          is excluded from Git via <span className="font-mono">.gitignore</span>.
        </p>
      </div>
    </div>
  );
}
