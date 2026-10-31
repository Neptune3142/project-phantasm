import { Ghost, Activity } from 'lucide-react';

export default function Header({ simMode, onToggleSim }) {
  return (
    <header className="relative overflow-hidden spooky-grid">
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-4 px-6 py-4 border-b border-phantom-border/70 bg-phantom-panel/40 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-phantom-purple/20 border border-phantom-purple/50 grid place-items-center shadow-glow-purple">
            <Ghost className="w-6 h-6 text-phantom-purpleBri animate-float" />
          </div>
          <div>
            <h1 className="font-display text-xl font-semibold tracking-tight leading-tight">
              PROJECT PHANTASM
            </h1>
            <p className="text-xs text-phantom-textDim font-mono uppercase tracking-widest">
              Zombie Credential Exorcist
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-full bg-phantom-bg border border-phantom-border">
            <Activity className={`w-3.5 h-3.5 ${simMode ? 'text-phantom-amber' : 'text-phantom-green'}`} />
            <span className="text-phantom-textDim">{simMode ? 'SIMULATION' : 'LIVE'}</span>
            <span className={simMode ? 'text-phantom-amber' : 'text-phantom-green'}>●</span>
          </div>
          <button
            onClick={onToggleSim}
            className={`btn-ghost ${simMode ? '' : 'text-phantom-green'}`}
            aria-label="Toggle simulation mode"
          >
            {simMode ? 'Switch to LIVE' : 'Switch to SIMULATION'}
          </button>
        </div>
      </div>
    </header>
  );
}
