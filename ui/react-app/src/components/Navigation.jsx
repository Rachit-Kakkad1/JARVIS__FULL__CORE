import React from 'react';
import Panel from './Panel';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'controls',  label: 'Controls' },
  { id: 'memory',    label: 'Memory' },
  { id: 'settings',  label: 'Settings' },
];

export default function Navigation({ activeNav, onNavChange }) {
  return (
    <Panel title="Navigation">
      <ul className="nav-list">
        {NAV_ITEMS.map((item) => (
          <li
            key={item.id}
            className={`nav-item ${activeNav === item.id ? 'active' : ''}`}
            onClick={() => onNavChange(item.id)}
          >
            <span>{item.label}</span>
            <span className="nav-chevron">›</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
