import React from 'react';
import '../styles/workout.css'; // make sure to import the CSS

// injuries: array of { key:'shoulder', label:'Shoulder' }
// selected: Set or array
export default function InjuryBrowser({ injuries = [], selected = [], onToggle }) {
  const selSet = new Set(selected || []);
  return (
    <div>
      <h4>Injury / Avoid List</h4>
      <div className="injury-list" role="list">
        {injuries.map(i => {
          const checked = selSet.has(i.key);
          return (
            <label key={i.key} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 6 }}>
              <input
                type="checkbox"
                checked={checked}
                onChange={() => onToggle(i.key)}
              />
              <div>
                <div style={{ fontWeight: 600 }}>{i.label}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{i.description}</div>
              </div>
            </label>
          );
        })}
      </div>
    </div>
  );
}
