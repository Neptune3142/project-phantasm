export default function Sidebar({ active, onSelect }) {
  const nav = [
    { id: 'dashboard',    label: 'Dashboard',          icon: '📊' },
    { id: 'accounts',     label: 'Ghost Monitor',      icon: '👻' },
    { id: 'threat',       label: 'Threat Feed',        icon: '🛰️' },
    { id: 'pipeline',     label: 'n8n Pipeline',       icon: '⚙️' },
    { id: 'epitaphs',     label: 'Epitaph Vault',      icon: '⚰️' },
    { id: 'scenarios',    label: 'Simulation Lab',     icon: '🧪' },
    { id: 'settings',     label: 'Integrations',       icon: '🔌' },
  ];
  return (
    <nav className="w-56 shrink-0 border-r border-phantom-border bg-phantom-panel/30 backdrop-blur-sm">
      <div className="py-4 px-3 flex flex-col gap-1">
        {nav.map(item => (
          <button
            key={item.id}
            onClick={() => onSelect(item.id)}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition
              ${active === item.id
                ? 'bg-phantom-purple/20 text-phantom-text border border-phantom-purple/40'
                : 'text-phantom-textDim hover:bg-phantom-panel2 hover:text-phantom-text border border-transparent'}`}
          >
            <span className="text-base">{item.icon}</span>
            <span className="font-medium">{item.label}</span>
          </button>
        ))}
      </div>
      <div className="px-4 pt-2 pb-4 text-[10px] text-phantom-textDim/60 font-mono uppercase tracking-widest">
        v1.0.0 · phantasm.core
      </div>
    </nav>
  );
}
