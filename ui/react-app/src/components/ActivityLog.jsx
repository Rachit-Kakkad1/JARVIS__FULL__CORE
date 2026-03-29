import React from 'react';
import Panel from './Panel';

export default function ActivityLog({ activities }) {
  const recent = activities.slice(0, 6);

  return (
    <Panel title="Activity Log">
      <div className="activity-list">
        {recent.length === 0 && (
          <div style={{ color: 'var(--text-dim)', fontSize: '11px', fontStyle: 'italic' }}>
            No activity yet...
          </div>
        )}
        {recent.map((act, i) => (
          <div key={i} className="activity-item">
            <div className="activity-time">
              {new Date(act.timestamp).toLocaleTimeString('en-US', { hour12: false })}
            </div>
            <div className="activity-desc">{act.description}</div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
