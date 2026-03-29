import React from 'react';

export default function ArcReactor() {
  const r = 50;
  const cx = 65;
  const cy = 65;

  return (
    <div className="arc-reactor-container">
      <svg className="arc-reactor-svg" viewBox="0 0 130 130">
        {/* Ring 1 — slow clockwise, sparse dashes */}
        <circle
          className="arc-ring arc-ring-1"
          cx={cx} cy={cy} r={r}
          strokeWidth="2"
          strokeDasharray="8 18 4 22"
        />
        {/* Ring 2 — medium counter-clockwise */}
        <circle
          className="arc-ring arc-ring-2"
          cx={cx} cy={cy} r={r - 8}
          strokeWidth="1.5"
          strokeDasharray="12 8 6 14"
        />
        {/* Ring 3 — fast clockwise, dense */}
        <circle
          className="arc-ring arc-ring-3"
          cx={cx} cy={cy} r={r - 16}
          strokeWidth="1"
          strokeDasharray="3 5 8 4 2 6"
        />
        {/* Center pulse */}
        <circle className="arc-center" cx={cx} cy={cy} r="10" />
      </svg>
      <div className="arc-label">J.A.R.V.I.S.</div>
      <div className="arc-sublabel">RK AETHERION SYSTEMS</div>
    </div>
  );
}
