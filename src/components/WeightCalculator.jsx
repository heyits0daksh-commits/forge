import React, { useState } from 'react';
import { estimate1RM, brzyckiEstimate, workingWeightFrom1RM, warmupSets } from '../utils/workoutGenerator';

export default function WeightCalculator({ unitStep = 1 }) {
  const [weight, setWeight] = useState('');
  const [reps, setReps] = useState('');
  const [oneRM, setOneRM] = useState(null);
  const [goal, setGoal] = useState('hypertrophy');

  function calc() {
    const w = parseFloat(weight);
    const r = parseInt(reps, 10);
    if (!w || !r) {
      alert('Enter weight and reps');
      return;
    }
    const est1 = estimate1RM(w, r) || brzyckiEstimate(w, r);
    setOneRM(est1);
  }

  const working = oneRM ? workingWeightFrom1RM(oneRM, goal, unitStep) : null;
  const warmups = oneRM ? warmupSets(oneRM) : [];

  return (
    <div>
      <h4>Weight Recommendation</h4>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input placeholder="Weight used (kg/lb)" value={weight} onChange={e => setWeight(e.target.value)} />
        <input placeholder="Reps" value={reps} onChange={e => setReps(e.target.value)} />
        <select value={goal} onChange={e => setGoal(e.target.value)}>
          <option value="strength">Strength</option>
          <option value="power">Power</option>
          <option value="hypertrophy">Hypertrophy</option>
          <option value="endurance">Endurance</option>
        </select>
        <button onClick={calc}>Estimate 1RM</button>
      </div>

      {oneRM && (
        <div style={{ marginTop: 8 }}>
          <div><strong>Estimated 1RM:</strong> {oneRM}</div>
          <div><strong>Working weight ({goal}):</strong> {working}</div>
          <div style={{ marginTop: 6 }}>
            <strong>Warm-up:</strong>
            <ul>
              {warmups.map((s, i) => <li key={i}>{s.target} × {s.reps}</li>)}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
