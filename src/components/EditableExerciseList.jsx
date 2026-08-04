import React, { useState, useEffect } from 'react';

// Props:
// initialExercises: [{id,name,sets,reps}]
// onChange(exercises) - optional
export default function EditableExerciseList({ initialExercises = [], storageKey = 'customWorkout', onChange }) {
  const [exercises, setExercises] = useState([]);
  const [newName, setNewName] = useState('');

  useEffect(() => {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      try {
        setExercises(JSON.parse(saved));
        return;
      } catch {}
    }
    setExercises(initialExercises);
  }, [initialExercises, storageKey]);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(exercises));
    if (onChange) onChange(exercises);
  }, [exercises, storageKey, onChange]);

  function addExercise() {
    const name = newName.trim();
    if (!name) return;
    setExercises(prev => [...prev, { id: Date.now(), name, sets: 3, reps: '6-12' }]);
    setNewName('');
  }

  function removeExercise(id) {
    setExercises(prev => prev.filter(e => e.id !== id));
  }

  function moveUp(index) {
    if (index === 0) return;
    setExercises(prev => {
      const arr = [...prev];
      [arr[index-1], arr[index]] = [arr[index], arr[index-1]];
      return arr;
    });
  }

  function moveDown(index) {
    setExercises(prev => {
      if (index === prev.length - 1) return prev;
      const arr = [...prev];
      [arr[index+1], arr[index]] = [arr[index], arr[index+1]];
      return arr;
    });
  }

  function exportJSON() {
    const blob = new Blob([JSON.stringify(exercises, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'custom_workout.json'; a.click();
    URL.revokeObjectURL(url);
  }

  function importJSON(file) {
    const reader = new FileReader();
    reader.onload = e => {
      try {
        const parsed = JSON.parse(e.target.result);
        if (Array.isArray(parsed)) setExercises(parsed);
      } catch (err) {
        alert('Invalid JSON');
      }
    };
    reader.readAsText(file);
  }

  return (
    <div>
      <h3>Exercises</h3>
      <ul>
        {exercises.map((ex, i) => (
          <li key={ex.id} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <div>
              <strong>{ex.name}</strong>
              <div style={{ fontSize: 12, color: '#666' }}>{ex.sets} sets × {ex.reps}</div>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              <button onClick={() => moveUp(i)} aria-label="move up">↑</button>
              <button onClick={() => moveDown(i)} aria-label="move down">↓</button>
              <button onClick={() => removeExercise(ex.id)}>Remove</button>
            </div>
          </li>
        ))}
      </ul>

      <div style={{ marginTop: 8 }}>
        <input
          placeholder="Add exercise (e.g., Barbell Row)"
          value={newName}
          onChange={e => setNewName(e.target.value)}
        />
        <button onClick={addExercise}>Add</button>
      </div>

      <div style={{ marginTop: 8 }}>
        <button onClick={exportJSON}>Export</button>
        <input
          type="file"
          accept="application/json"
          onChange={e => e.target.files && importJSON(e.target.files[0])}
          style={{ marginLeft: 8 }}
        />
      </div>
    </div>
  );
}
