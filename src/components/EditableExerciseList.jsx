import React, { useState, useEffect } from 'react';
import {
  DndContext,
  closestCenter,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// Sortable item wrapper using dnd-kit
function SortableItem({ item, index, onMoveUp, onMoveDown, onRemove }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    display: 'flex',
    gap: 8,
    alignItems: 'center',
    padding: 8,
    marginBottom: 6,
    background: isDragging ? '#f0f8ff' : 'transparent',
    borderRadius: 4,
  };

  return (
    <li ref={setNodeRef} style={style} {...attributes}>
      <div {...listeners} style={{ cursor: 'grab', paddingRight: 8 }} aria-label="drag-handle">☰</div>
      <div style={{ flex: 1 }}>
        <strong>{item.name}</strong>
        <div style={{ fontSize: 12, color: '#666' }}>{item.sets} sets × {item.reps}</div>
      </div>

      <div style={{ display: 'flex', gap: 6 }}>
        <button onClick={() => onMoveUp(index)} aria-label="move up">↑</button>
        <button onClick={() => onMoveDown(index)} aria-label="move down">↓</button>
        <button onClick={() => onRemove(item.id)}>Remove</button>
      </div>
    </li>
  );
}

// Props:
// initialExercises: [{id,name,sets,reps}]
// onChange(exercises) - optional
export default function EditableExerciseList({ initialExercises = [], storageKey = 'customWorkout', onChange }) {
  const [exercises, setExercises] = useState([]);
  const [newName, setNewName] = useState('');
  const [longPressDrag, setLongPressDrag] = useState(true); // default to long-press on mobile for stability

  useEffect(() => {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      try {
        setExercises(JSON.parse(saved));
        return;
      } catch {}
    }
    // normalize ids to strings
    setExercises(initialExercises.map(p => ({ ...p, id: p.id ? String(p.id) : Date.now().toString() })));
  }, [initialExercises, storageKey]);

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(exercises));
    if (onChange) onChange(exercises);
  }, [exercises, storageKey, onChange]);

  function addExercise() {
    const name = newName.trim();
    if (!name) return;
    setExercises(prev => [...prev, { id: Date.now().toString(), name, sets: 3, reps: '6-12' }]);
    setNewName('');
  }

  function removeExercise(id) {
    setExercises(prev => prev.filter(e => e.id !== id));
  }

  function moveUp(index) {
    if (index === 0) return;
    setExercises(prev => arrayMove(prev, index, index - 1));
  }

  function moveDown(index) {
    setExercises(prev => {
      if (index === prev.length - 1) return prev;
      return arrayMove(prev, index, index + 1);
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
        if (Array.isArray(parsed)) setExercises(parsed.map(p => ({ ...p, id: p.id ? String(p.id) : Date.now().toString() })));
      } catch (err) {
        alert('Invalid JSON');
      }
    };
    reader.readAsText(file);
  }

  // dnd-kit sensors: include PointerSensor for mouse and TouchSensor for touch
  const pointerSensor = useSensor(PointerSensor, { activationConstraint: { distance: 5 } });
  // For touch we allow toggling between long-press activation or immediate drag.
  const touchSensor = useSensor(TouchSensor, longPressDrag ? { activationConstraint: { delay: 250, tolerance: 5 } } : {});
  const sensors = useSensors(pointerSensor, touchSensor);

  function handleDragEnd(event) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = exercises.findIndex(e => e.id === active.id);
    const newIndex = exercises.findIndex(e => e.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;
    setExercises(prev => arrayMove(prev, oldIndex, newIndex));
  }

  return (
    <div>
      <h3>Exercises</h3>

      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 12 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input type="checkbox" checked={longPressDrag} onChange={() => setLongPressDrag(v => !v)} />
          Use long-press to start drag on touch devices
        </label>
        <div style={{ fontSize: 12, color: '#666' }}>Toggle long-press for more reliable touch drags on mobile.</div>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={exercises.map(e => e.id)} strategy={verticalListSortingStrategy}>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {exercises.map((ex, i) => (
              <SortableItem
                key={ex.id}
                item={ex}
                index={i}
                onMoveUp={moveUp}
                onMoveDown={moveDown}
                onRemove={removeExercise}
              />
            ))}
          </ul>
        </SortableContext>
      </DndContext>

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

      <div style={{ marginTop: 10, fontSize: 12, color: '#444' }}>
        Tip: Drag the exercise by the handle (☰) to reorder. Toggle long-press to require holding for 250ms before drag starts on touch devices.
      </div>
    </div>
  );
}
