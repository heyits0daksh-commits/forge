import React, { useState, useEffect } from 'react';
import { SPORT_DEFINITIONS, WorkoutSession, saveWorkoutSession, loadAthleteProfile } from '../utils/sportAthleteEngine';

export default function WorkoutLogger({ athleteId }) {
  const [athlete, setAthlete] = useState(null);
  const [phase, setPhase] = useState('strength');
  const [duration, setDuration] = useState('60');
  const [rpe, setRpe] = useState('7');
  const [exercises, setExercises] = useState([]);
  const [newExerciseName, setNewExerciseName] = useState('');
  const [newExerciseGoal, setNewExerciseGoal] = useState('');
  const [readiness, setReadiness] = useState({
    sleep_hours: '7.5',
    energy_level: '7',
    soreness_level: '3',
    mental_readiness: '8'
  });
  const [notes, setNotes] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const profile = loadAthleteProfile(athleteId);
    setAthlete(profile);
    if (profile) {
      setNewExerciseGoal(SPORT_DEFINITIONS[profile.sport].categories[0] || '');
    }
  }, [athleteId]);

  if (!athlete) return <div>Loading athlete...</div>;

  const sportDef = SPORT_DEFINITIONS[athlete.sport];

  function addExercise() {
    if (!newExerciseName.trim() || !newExerciseGoal) return;

    setExercises(prev => [...prev, {
      id: Date.now(),
      name: newExerciseName,
      sport_goal: newExerciseGoal,
      sets: []
    }]);

    setNewExerciseName('');
    setNewExerciseGoal(sportDef.categories[0] || '');
  }

  function addSet(exerciseId) {
    setExercises(prev => prev.map(ex => {
      if (ex.id === exerciseId) {
        return {
          ...ex,
          sets: [...ex.sets, { reps: '', weight: '', rpe: '', bar_speed: 'controlled' }]
        };
      }
      return ex;
    }));
  }

  function updateSet(exerciseId, setIndex, field, value) {
    setExercises(prev => prev.map(ex => {
      if (ex.id === exerciseId) {
        const newSets = [...ex.sets];
        newSets[setIndex] = { ...newSets[setIndex], [field]: value };
        return { ...ex, sets: newSets };
      }
      return ex;
    }));
  }

  function removeSet(exerciseId, setIndex) {
    setExercises(prev => prev.map(ex => {
      if (ex.id === exerciseId) {
        return {
          ...ex,
          sets: ex.sets.filter((_, i) => i !== setIndex)
        };
      }
      return ex;
    }));
  }

  function removeExercise(exerciseId) {
    setExercises(prev => prev.filter(ex => ex.id !== exerciseId));
  }

  function saveWorkout() {
    const session = new WorkoutSession(athleteId, athlete.sport, phase, parseInt(duration));
    session.rpe = parseInt(rpe);
    session.readiness = {
      sleep_hours: parseFloat(readiness.sleep_hours),
      energy_level: parseInt(readiness.energy_level),
      soreness_level: parseInt(readiness.soreness_level),
      mental_readiness: parseInt(readiness.mental_readiness)
    };
    session.notes = notes;

    exercises.forEach(ex => {
      session.addExercise(ex.name, ex.sport_goal, ex.sets);
    });

    saveWorkoutSession(session);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2>{athlete.name} - {athlete.sport}</h2>
          <div style={{ fontSize: 12, color: '#999' }}>Workout Logger</div>
        </div>
        {saved && <div style={{ color: '#2a9d2a', fontWeight: 600 }}>✓ Workout saved!</div>}
      </div>

      {/* Session Info */}
      <div style={{ background: '#f5f5f5', padding: 16, borderRadius: 8, marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4, color: '#666' }}>Training Phase</label>
            <select
              value={phase}
              onChange={e => setPhase(e.target.value)}
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 14 }}
            >
              <option value="strength">Strength</option>
              <option value="power">Power</option>
              <option value="endurance">Endurance</option>
              <option value="deload">Deload</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4, color: '#666' }}>Duration (min)</label>
            <input
              type="number"
              value={duration}
              onChange={e => setDuration(e.target.value)}
              min="15"
              max="180"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 14 }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4, color: '#666' }}>RPE (1-10)</label>
            <input
              type="number"
              value={rpe}
              onChange={e => setRpe(e.target.value)}
              min="1"
              max="10"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 14 }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4, color: '#666' }}>Today's Notes</label>
            <input
              type="text"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="How did it feel?"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 14 }}
            />
          </div>
        </div>
      </div>

      {/* Readiness Metrics */}
      <div style={{ background: '#fff9f0', padding: 16, borderRadius: 8, marginBottom: 20, border: '1px solid #ffe0c6' }}>
        <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>Recovery & Readiness</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4, color: '#666' }}>Sleep (hours)</label>
            <input
              type="number"
              value={readiness.sleep_hours}
              onChange={e => setReadiness({ ...readiness, sleep_hours: e.target.value })}
              step="0.5"
              min="0"
              max="12"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 14 }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4, color: '#666' }}>Energy (1-10)</label>
            <input
              type="number"
              value={readiness.energy_level}
              onChange={e => setReadiness({ ...readiness, energy_level: e.target.value })}
              min="1"
              max="10"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 14 }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4, color: '#666' }}>Soreness (1-10)</label>
            <input
              type="number"
              value={readiness.soreness_level}
              onChange={e => setReadiness({ ...readiness, soreness_level: e.target.value })}
              min="1"
              max="10"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 14 }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4, color: '#666' }}>Mental Ready (1-10)</label>
            <input
              type="number"
              value={readiness.mental_readiness}
              onChange={e => setReadiness({ ...readiness, mental_readiness: e.target.value })}
              min="1"
              max="10"
              style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 14 }}
            />
          </div>
        </div>
      </div>

      {/* Add Exercise */}
      <div style={{ background: '#f9f9f9', padding: 16, borderRadius: 8, marginBottom: 20, border: '1px solid #eee' }}>
        <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>Add Exercise</div>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto', gap: 10 }}>
          <input
            type="text"
            value={newExerciseName}
            onChange={e => setNewExerciseName(e.target.value)}
            placeholder="Exercise name (e.g., Back Squat)"
            style={{ padding: 10, border: '1px solid #ddd', borderRadius: 4, fontSize: 14 }}
          />
          <select
            value={newExerciseGoal}
            onChange={e => setNewExerciseGoal(e.target.value)}
            style={{ padding: 10, border: '1px solid #ddd', borderRadius: 4, fontSize: 14 }}
          >
            {sportDef.categories.map(cat => (
              <option key={cat} value={cat}>{cat.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <button
            onClick={addExercise}
            style={{
              padding: '10px 16px',
              background: sportDef.accent,
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            + Add
          </button>
        </div>
      </div>

      {/* Exercises */}
      <div>
        {exercises.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            No exercises added yet. Add one above.
          </div>
        ) : (
          exercises.map((ex, exIdx) => (
            <div
              key={ex.id}
              style={{
                background: '#fff',
                border: `2px solid ${sportDef.accent}20`,
                borderRadius: 8,
                padding: 16,
                marginBottom: 16,
                borderLeft: `4px solid ${sportDef.accent}`
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>{ex.name}</div>
                  <div style={{ fontSize: 12, color: '#999' }}>Goal: {ex.sport_goal.replace(/_/g, ' ')}</div>
                </div>
                <button
                  onClick={() => removeExercise(ex.id)}
                  style={{
                    background: '#fee',
                    border: '1px solid #fcc',
                    color: '#c33',
                    padding: '6px 12px',
                    borderRadius: 4,
                    cursor: 'pointer',
                    fontSize: 12,
                    fontWeight: 600
                  }}
                >
                  Remove
                </button>
              </div>

              {/* Sets */}
              <div style={{ marginBottom: 12 }}>
                {ex.sets.map((set, setIdx) => (
                  <div
                    key={setIdx}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'auto 1fr 1fr 1fr 1fr auto',
                      gap: 8,
                      alignItems: 'center',
                      marginBottom: 8,
                      padding: 10,
                      background: '#f9f9f9',
                      borderRadius: 4
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 12, color: '#999' }}>Set {setIdx + 1}</div>
                    <input
                      type="number"
                      placeholder="Reps"
                      value={set.reps}
                      onChange={e => updateSet(ex.id, setIdx, 'reps', e.target.value)}
                      style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 12 }}
                    />
                    <input
                      type="number"
                      placeholder="Weight (kg)"
                      value={set.weight}
                      onChange={e => updateSet(ex.id, setIdx, 'weight', e.target.value)}
                      style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 12 }}
                    />
                    <input
                      type="number"
                      placeholder="RPE (1-10)"
                      value={set.rpe}
                      onChange={e => updateSet(ex.id, setIdx, 'rpe', e.target.value)}
                      min="1"
                      max="10"
                      style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 12 }}
                    />
                    <select
                      value={set.bar_speed || 'controlled'}
                      onChange={e => updateSet(ex.id, setIdx, 'bar_speed', e.target.value)}
                      style={{ padding: 8, border: '1px solid #ddd', borderRadius: 4, fontSize: 12 }}
                    >
                      <option value="explosive">Explosive</option>
                      <option value="controlled">Controlled</option>
                      <option value="grind">Grind</option>
                    </select>
                    <button
                      onClick={() => removeSet(ex.id, setIdx)}
                      style={{
                        background: '#fee',
                        border: 'none',
                        color: '#c33',
                        padding: '6px 10px',
                        borderRadius: 4,
                        cursor: 'pointer',
                        fontSize: 12,
                        fontWeight: 600
                      }}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>

              <button
                onClick={() => addSet(ex.id)}
                style={{
                  padding: '8px 16px',
                  background: sportDef.accent + '20',
                  border: `1px solid ${sportDef.accent}`,
                  color: sportDef.accent,
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: 12
                }}
              >
                + Add Set
              </button>
            </div>
          ))
        )}
      </div>

      {/* Save Button */}
      <div style={{ marginTop: 30, display: 'flex', gap: 10 }}>
        <button
          onClick={saveWorkout}
          disabled={exercises.length === 0}
          style={{
            flex: 1,
            padding: 14,
            background: exercises.length === 0 ? '#ccc' : sportDef.accent,
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: exercises.length === 0 ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: 16
          }}
        >
          💾 Save Workout
        </button>
      </div>
    </div>
  );
}
