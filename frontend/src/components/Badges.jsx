export function riskChip(category) {
  const cls = `chip-${(category || 'low').toLowerCase()}`;
  const label = (category || 'UNKNOWN').toUpperCase();
  return <span className={cls}>{label}</span>;
}

export function statusChip(status) {
  const s = (status || '').toUpperCase();
  let cls = 'bg-phantom-bg text-phantom-textDim border border-phantom-border';
  if (['ACTIVE', 'COMPLETED', 'OPERATIONAL'].includes(s)) cls = 'bg-phantom-green/15 text-phantom-greenBri';
  if (['FLAGGED', 'MONITORED', 'PENDING_APPROVAL'].includes(s)) cls = 'bg-phantom-amber/15 text-phantom-amber';
  if (['REVOKED', 'FAILED', 'REJECTED'].includes(s)) cls = 'bg-phantom-red/20 text-phantom-redBri';
  return <span className={`chip ${cls}`}>{s}</span>;
}

export function scoreBadge(score, category) {
  let cls = 'text-phantom-greenBri border-phantom-green/40';
  if (category === 'MEDIUM') cls = 'text-phantom-amber border-phantom-amber/40';
  if (category === 'HIGH') cls = 'text-phantom-redBri border-phantom-red/40';
  if (category === 'CRITICAL') cls = 'text-phantom-redBri border-phantom-red/60 bg-phantom-red/10 animate-pulse-glow';
  return (
    <span className={`font-mono text-sm font-semibold px-2 py-0.5 rounded border ${cls}`}>
      {score}
    </span>
  );
}
