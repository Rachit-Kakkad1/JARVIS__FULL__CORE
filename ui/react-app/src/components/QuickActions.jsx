import React from 'react';
import Panel from './Panel';

const ACTIONS = [
  { id: 'youtube',  icon: '▶',  label: 'YouTube' },
  { id: 'spotify',  icon: '♫',  label: 'Spotify' },
  { id: 'chrome',   icon: '◎',  label: 'Chrome' },
  { id: 'vscode',   icon: '⟨⟩', label: 'VS Code' },
  { id: 'capture',  icon: '📷', label: 'Capture' },
  { id: 'sysinfo',  icon: '◈',  label: 'Sys Info' },
];

export default function QuickActions({ onAction }) {
  return (
    <Panel title="Quick Actions">
      <div className="quick-grid">
        {ACTIONS.map((a) => (
          <button
            key={a.id}
            className="quick-btn"
            onClick={() => onAction(a.id)}
          >
            <span className="quick-btn-icon">{a.icon}</span>
            <span className="quick-btn-label">{a.label}</span>
          </button>
        ))}
      </div>
    </Panel>
  );
}
