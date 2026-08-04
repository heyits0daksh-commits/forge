// App.jsx - example integration
import React, { useState, useMemo } from 'react';
import { generateWorkoutPlan } from './utils/workoutGenerator';
import EditableExerciseList from './components/EditableExerciseList';
import InjuryBrowser from './components/InjuryBrowser';
import WeightCalculator from './components/WeightCalculator';
import './styles/workout.css';

const EXERCISES_DB = [
  { id: 'sq', name: 'Back Squat', muscleGroups: ['quads','glutes','hams'], isCompound: true, isPrimary: true },
  { id: 'dl', name: 'Deadlift', muscleGroups: ['back','hams','glutes'], isCompound: true, isPrimary: true },
  { id: 'bp', name: 'Barbell Bench Press', muscleGroups: ['chest','triceps','shoulders'], isCompound: true, isPrimary: true },
  { id: 'ohp', name: 'Overhead Press', muscleGroups: ['shoulders','triceps'], isCompound: true, isPrimary: true },
  { id: 'row', name: 'Barbell Row', muscleGroups: ['back','biceps'], isCompound: true, isPrimary: true },
  { id: 'pull', name: 'Pull-up', muscleGroups: ['back','biceps'], isCompound: true, isPrimary: true },
  { id: 'legcurl', name: 'Leg Curl', muscleGroups: ['hams'], isCompound: false },
  { id: 'calf', name: 'Calf Raise', muscleGroups: ['calves'], isCompound: false, isFinisher: true },
  { id: 'plank', name: 'Plank', muscleGroups: ['core'], isCompound: false, isFinisher: true },
  { id: 'shrug', name: 'Dumbbell Shrug', muscleGroups: ['traps'], isCompound: false, isFinisher: true },
  { id: 'farmer', name: 'Farmer Carry', muscleGroups: ['grip','core','traps'], isCompound: false, isFinisher: true },
  { id: 'face', name: 'Face Pull', muscleGroups: ['rear delts','traps'], isCompound: false },
  { id: 'dip', name: 'Dip', muscleGroups: ['chest','triceps'], isCompound: true }
];

const POSSIBLE_INJURIES = [
  { key: 'shoulders', label: 'Shoulder', description: 'Avoid pressing/overhead loads' },
  { key: 'knee', label: 'Knee', description: 'Avoid heavy squats or knee-dominant pain' },
  { key: 'back', label: 'Back', description: 'Avoid heavy spinal loading if hurt' },
  { key: 'elbow', label: 'Elbow', description: 'Avoid heavy rows/curls/extensions' }
];

export default function App() {
  const [days, setDays] = useState(3);
  const [injuries, setInjuries] = useState([]);
  const [goal, setGoal] = useState('hypertrophy');
  const [plan, setPlan] = useState(null);

  function toggleInjury(k) {
    setInjuries(prev => prev.includes(k) ? prev.filter(x=>x!==k) : [...prev, k]);
  }

  function onGenerate() {
    const result = generateWorkoutPlan({
      daysPerWeek: days,
      exercisesDB: EXERCISES_DB,
      injuries,
      goal,
      exercisesPerDay: 5
    });
    setPlan(result);
  }

  const initialExercises = useMemo(() => (plan && plan[0] ? plan[0].exercises : []), [plan]);

  return (
    <div style={{ padding: 16, maxWidth: 900, margin: '0 auto' }}>
      <h2>Coach / Athlete Workout Generator</h2>

      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ flex: 1 }}>
          <label>Days per week:
            <input type="number" min="1" max="6" value={days} onChange={e => setDays(parseInt(e.target.value || '3',10))} />
          </label>
          <label style={{ marginLeft: 8 }}>Goal:
            <select value={goal} onChange={e=>setGoal(e.target.value)}>
              <option value="strength">Strength</option>
              <option value="hypertrophy">Hypertrophy</option>
              <option value="endurance">Endurance</option>
            </select>
          </label>

          <InjuryBrowser injuries={POSSIBLE_INJURIES} selected={injuries} onToggle={toggleInjury} />

          <div style={{ marginTop: 8 }}>
            <button onClick={onGenerate}>Generate</button>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <WeightCalculator />
        </div>
      </div>

      <div style={{ marginTop: 20 }}>
        {plan ? (
          <>
            <h3>Generated Plan</h3>
            {plan.map((d, i) => (
              <div key={i} style={{ border: '1px solid #ddd', padding: 8, marginBottom: 8 }}>
                <h4>{d.dayName}</h4>
                <EditableExerciseList initialExercises={d.exercises} storageKey={`plan-${i}`} />
              </div>
            ))}
          </>
        ) : <div>No plan generated yet</div>}
      </div>
    </div>
  );
}
