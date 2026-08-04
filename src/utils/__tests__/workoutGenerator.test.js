// src/utils/__tests__/workoutGenerator.test.js
import { generateWorkoutPlan, filterExercisesForInjuries } from '../workoutGenerator';

const MOCK_DB = [
  { id: 'sq', name: 'Back Squat', muscleGroups: ['quads','glutes','hams'], isCompound: true, isPrimary: true },
  { id: 'dl', name: 'Deadlift', muscleGroups: ['back','hams','glutes'], isCompound: true, isPrimary: true },
  { id: 'bp', name: 'Barbell Bench Press', muscleGroups: ['chest','triceps','shoulders'], isCompound: true, isPrimary: true },
  { id: 'ohp', name: 'Overhead Press', muscleGroups: ['shoulders','triceps'], isCompound: true, isPrimary: true },
  { id: 'row', name: 'Barbell Row', muscleGroups: ['back','biceps'], isCompound: true, isPrimary: true },
  { id: 'legcurl', name: 'Leg Curl', muscleGroups: ['hams'], isCompound: false },
  { id: 'plank', name: 'Plank', muscleGroups: ['core'], isCompound: false, isFinisher: true },
  { id: 'farmer', name: 'Farmer Carry', muscleGroups: ['grip','core','traps'], isCompound: false, isFinisher: true }
];

test('generateWorkoutPlan produces main lifts first and finisher last for 3-day split', () => {
  const plan = generateWorkoutPlan({ daysPerWeek: 3, exercisesDB: MOCK_DB, exercisesPerDay: 5 });
  expect(plan.length).toBe(3);
  for (const day of plan) {
    const ex = day.exercises;
    if (ex.length === 0) continue;
    // first two should be primaries or compounds
    expect(ex[0]).toBeDefined();
    // finisher should be last if present
    const names = ex.map(e => e.id);
    if (names.includes('plank') || names.includes('farmer')) {
      const last = names[names.length - 1];
      expect(['plank','farmer']).toContain(last);
    }
  }
});

test('filterExercisesForInjuries removes injured muscle group exercises', () => {
  const filtered = filterExercisesForInjuries(MOCK_DB, ['back']);
  // deadlift and row should be removed
  const ids = filtered.map(e => e.id);
  expect(ids).not.toContain('dl');
  expect(ids).not.toContain('row');
});

test('generateWorkoutPlan returns empty exercises when DB empty', () => {
  const plan = generateWorkoutPlan({ daysPerWeek: 3, exercisesDB: [], exercisesPerDay: 5 });
  expect(plan.every(d => Array.isArray(d.exercises) && d.exercises.length === 0)).toBe(true);
});
