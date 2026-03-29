import React from 'react';

export default function Panel({ title, children, className = '' }) {
  return (
    <div className={`hud-panel ${className}`}>
      <div className="corner-bl"></div>
      <div className="corner-br"></div>
      {title && <div className="hud-panel-title">{title}</div>}
      {children}
    </div>
  );
}
