// src/utils/workoutGenerator.js
// Helper utilities for split generation, injury filtering, and weight calculations.

function estimate1RM(weight, reps) {
  // Epley formula (works well for reps 1-10)
  if (!weight || !reps || reps <= 0) return null;
  const oneRM = weight * (1 + reps / 30);
  return Math.round(oneRM * 10) / 10;
}

function brzyckiEstimate(weight, reps) {
  if (!weight || !reps || reps <= 0) return null;
  const oneRM = weight * (36 / (37 - reps));
  return Math.round(oneRM * 10) / 10;
}

function workingWeightFrom1RM(oneRM, goal = 'hypertrophy', unitStep = 1) {
  // Map goal to percentage (tuneable)
  const map = {
    strength: 0.9,
    power: 0.85,
    hypertrophy: 0.75,
    endurance: 0.6
  };
  const pct = map[goal] ?? map.hypertrophy;
  let w = oneRM * pct;
  // round to nearest unitStep (1kg or 2.5lb)
  return Math.round(w / unitStep) * unitStep;
}

function warmupSets(oneRM, unitStep = 1) {
  // Simple warm-up progression: 40%x8, 60%x5, 80%x3 -> working
  if (!oneRM) return [];
  const sets = [
    { pct: 0.4, reps: 8 },
    { pct: 0.6, reps: 5 },
    { pct: 0.8, reps: 3 }
  ];
  return sets.map(s => ({
    target: Math.round((oneRM * s.pct) / unitStep) * unitStep,
    reps: s.reps
  }));
}

function generateSplit(daysPerWeek = 3) {
  // Returns an array of day templates with muscle groups prioritized.
  if (daysPerWeek <= 2) {
    return [{ name: 'Full Body', groups: ['chest','back','legs','shoulders','arms','core'] }];
  }
  if (daysPerWeek === 3) {
    return [
      { name: 'Push', groups: ['chest','shoulders','triceps'] },
      { name: 'Pull', groups: ['back','biceps','rear delts'] },
      { name: 'Legs', groups: ['quads','hams','glutes','calves'] }
    ];
  }
  if (daysPerWeek === 4) {
    return [
      { name: 'Upper A', groups: ['chest','back','shoulders'] },
      { name: 'Lower A', groups: ['quads','hams','glutes'] },
      { name: 'Upper B', groups: ['chest','back','arms'] },
      { name: 'Lower B', groups: ['quads','hams','glutes','calves'] }
    ];
  }
  // 5 or 6 days
  const base = [
    { name: 'Push', groups: ['chest','shoulders','triceps'] },
    { name: 'Pull', groups: ['back','biceps'] },
    { name: 'Legs', groups: ['quads','hams','glutes'] },
    { name: 'Accessory', groups: ['core','calves','rear delts'] },
    { name: 'Conditioning', groups: ['conditioning'] }
  ];
  return base.slice(0, Math.min(daysPerWeek, base.length));
}

function filterExercisesForInjuries(exercises, injuries = []) {
  // exercises: [{ id, name, muscleGroups: [] }]
  if (!injuries || injuries.length === 0) return exercises;
  const inj = injuries.map(i => i.toLowerCase());
  return exercises.filter(ex => {
    const mg = (ex.muscleGroups || []).map(m => m.toLowerCase());
    // remove exercise if any muscle group matches an injury
    return !mg.some(m => inj.includes(m));
  });
}

function generateWorkoutPlan({
  daysPerWeek = 3,
  exercisesDB = [],
  injuries = [],
  goal = 'hypertrophy',
  setsPerExercise = 3,
  repsRange = '6-12',
  exercisesPerDay = 5
} = {}) {
  // Build split then pick exercises from DB while avoiding injuries and balancing volume.
  const split = generateSplit(daysPerWeek);
  const safeExercises = filterExercisesForInjuries(exercisesDB, injuries);

  // Helper to score exercises so we can pick main lifts first, then compounds, then accessories, then finishers
  function scoreExerciseForDay(ex, dayGroups) {
    const mg = (ex.muscleGroups || []).map(m => m.toLowerCase());
    const groupMatch = mg.filter(m => dayGroups.includes(m)).length;
    let score = groupMatch * 10; // match muscle groups strongly
    if (ex.isPrimary) score += 50; // main lifts (squat, deadlift, bench, OHP, row, pull-up)
    if (ex.isCompound) score += 20; // compounds preferred
    if (ex.isFinisher) score -= 5; // finishers lower priority in main picks
    // small tiebreakers by difficulty or id
    if (ex.difficulty) score += (5 - (ex.difficulty || 3));
    return score;
  }

  const plan = split.map(day => {
    const dayGroups = day.groups;
    const candidates = safeExercises.filter(ex => {
      // match if any group intersects OR if it's a general finisher/core
      return (ex.muscleGroups || []).some(m => dayGroups.includes(m)) || (ex.isFinisher && dayGroups.includes('core'));
    });

    // Sort candidates by score descending
    const sorted = candidates
      .map(ex => ({ ex, score: scoreExerciseForDay(ex, dayGroups) }))
      .sort((a,b) => b.score - a.score)
      .map(s => s.ex);

    // Selection strategy:
    // 1) Pick up to 2 primary/main lifts (isPrimary)
    // 2) Then pick compounds until 2-3 total
    // 3) Then accessories
    // 4) Always append 1 finisher/core/grip/traps if available (isFinisher or muscleGroups includes core/traps/grip)

    const chosen = [];

    const pickUnique = (arr, n) => {
      for (const item of arr) {
        if (chosen.length >= n) break;
        if (!chosen.includes(item)) chosen.push(item);
      }
    };

    const primaries = sorted.filter(e => e.isPrimary);
    pickUnique(primaries, 2);

    const compounds = sorted.filter(e => e.isCompound && !chosen.includes(e));
    pickUnique(compounds, 3);

    const accessories = sorted.filter(e => !e.isCompound && !e.isFinisher && !chosen.includes(e));
    pickUnique(accessories, exercisesPerDay);

    // Finishers: core/traps/grip or marked isFinisher — try to include one at end
    const finishers = sorted.filter(e => (e.isFinisher || (e.muscleGroups||[]).some(m => ['core','traps','grip'].includes(m))) && !chosen.includes(e));
    if (finishers.length > 0 && chosen.length < exercisesPerDay) {
      pickUnique(finishers, exercisesPerDay);
    }

    // Fallback fill
    if (chosen.length < Math.min(exercisesPerDay, 4)) {
      for (const c of sorted) {
        if (chosen.length >= Math.min(exercisesPerDay, 5)) break;
        if (!chosen.includes(c)) chosen.push(c);
      }
    }

    // Map to plan items
    const items = chosen.slice(0, exercisesPerDay).map(ex => ({
      id: ex.id,
      name: ex.name,
      muscleGroups: ex.muscleGroups,
      sets: ex.defaultSets || setsPerExercise,
      reps: ex.defaultReps || repsRange,
      isCompound: !!ex.isCompound,
      isPrimary: !!ex.isPrimary,
      isFinisher: !!ex.isFinisher
    }));

    return { dayName: day.name, exercises: items };
  });

  return plan;
}

export {
  estimate1RM,
  brzyckiEstimate,
  workingWeightFrom1RM,
  warmupSets,
  generateSplit,
  filterExercisesForInjuries,
  generateWorkoutPlan
};
