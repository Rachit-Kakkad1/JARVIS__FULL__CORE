import React from 'react';
import Panel from './Panel';

function ArcGauge({ value, label, max = 100 }) {
  const r = 34;
  const circumference = 2 * Math.PI * r;
  const pct = Math.min(value, max) / max;
  const dashLen = circumference * pct;
  const dashGap = circumference - dashLen;

  // Color thresholds
  let color = 'var(--cyan)';
  if (value >= 75) color = 'var(--red)';
  else if (value >= 55) color = 'var(--amber)';

  return (
    <div className="gauge-container">
      <svg className="gauge-svg" viewBox="0 0 90 90">
        <circle className="gauge-bg" cx="45" cy="45" r={r} />
        <circle
          className="gauge-fill"
          cx="45" cy="45" r={r}
          stroke={color}
          strokeDasharray={`${dashLen} ${dashGap}`}
        />
        <text className="gauge-text" x="45" y="42">{Math.round(value)}</text>
        <text className="gauge-pct" x="45" y="56">%</text>
      </svg>
      <span className="gauge-label">{label}</span>
    </div>
  );
}

export default function SystemMonitor({ stats }) {
  const cpu = stats?.cpu_percent ?? 0;
  const ram = stats?.ram_percent ?? 0;
  const disk = stats?.disk_percent ?? 0;
  const temp = stats?.cpu_temp ?? '--';
  const procs = stats?.process_count ?? 0;
  const netRecv = stats?.net_recv_mb ?? 0;

  const getColor = (v) => {
    if (v >= 75) return 'var(--red)';
    if (v >= 55) return 'var(--amber)';
    return 'var(--cyan)';
  };

  return (
    <Panel title="System Monitor">
      <div className="gauges-row">
        <ArcGauge value={cpu} label="CPU" />
        <ArcGauge value={ram} label="RAM" />
      </div>
      <div className="mini-stats">
        <div className="mini-stat">
          <div className="mini-stat-value" style={{ color: getColor(disk) }}>
            {Math.round(disk)}%
          </div>
          <div className="mini-stat-label">DISK</div>
        </div>
        <div className="mini-stat">
          <div className="mini-stat-value">
            {temp !== '--' ? `${temp}°` : '--'}
          </div>
          <div className="mini-stat-label">TEMP</div>
        </div>
        <div className="mini-stat">
          <div className="mini-stat-value">{Math.round(netRecv)}</div>
          <div className="mini-stat-label">NET MB</div>
        </div>
        <div className="mini-stat">
          <div className="mini-stat-value">{procs}</div>
          <div className="mini-stat-label">PROCS</div>
        </div>
      </div>
    </Panel>
  );
}
