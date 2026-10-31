export default function StatCard({ icon, label, value, sub, accent = 'purple' }) {
  const accentClasses = {
    purple: 'text-phantom-purpleBri',
    green: 'text-phantom-greenBri',
    amber: 'text-phantom-amber',
    red: 'text-phantom-redBri',
    dim: 'text-phantom-textDim',
  };
  return (
    <div className="card card-hover">
      <div className="flex items-start justify-between mb-3">
        <div className="text-xs font-mono uppercase tracking-wider text-phantom-textDim">
          {label}
        </div>
        <div className={`text-xl ${accentClasses[accent]}`}>{icon}</div>
      </div>
      <div className={`stat-num ${accentClasses[accent]}`}>{value}</div>
      {sub && (
        <div className="mt-1 text-xs text-phantom-textDim">{sub}</div>
      )}
    </div>
  );
}
