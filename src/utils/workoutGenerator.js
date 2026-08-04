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
  if (!Array.isArray(exercises) || exercises.length === 0) return [];
  if (!injuries || injuries.length === 0) return exercises;
  const inj = new Set(injuries.map(i => String(i).toLowerCase().trim()));
  return exercises.filter(ex => {
    const mg = (ex.muscleGroups || []).map(m => String(m).toLowerCase().trim());
    // remove exercise if any muscle group matches an injury
    return !mg.some(m => inj.has(m));
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

  if (!Array.isArray(exercisesDB) || exercisesDB.length === 0) {
    // Return empty exercise lists for each day — UI should handle empty days gracefully
    return split.map(day => ({ dayName: day.name, exercises: [] }));
  }

  const safeExercises = filterExercisesForInjuries(exercisesDB, injuries);

  // Helper to score exercises so we can pick main lifts first, then compounds, then accessories, then finishers
  function scoreExerciseForDay(ex, daySet) {
    const mg = (ex.muscleGroups || []).map(m => String(m).toLowerCase().trim());
    const groupMatch = mg.filter(m => daySet.has(m)).length;
    let score = groupMatch * 10; // match muscle groups strongly
    if (ex.isPrimary) score += 50; // main lifts (squat, deadlift, bench, OHP, row, pull-up)
    if (ex.isCompound) score += 20; // compounds preferred
    if (ex.isFinisher) score -= 5; // finishers lower priority in main picks
    // small tiebreakers by difficulty
    const diff = Number(ex.difficulty) || 3;
    score += (5 - diff);
    return score;
  }

  const plan = split.map(day => {
    const dayGroups = day.groups || [];
    const daySet = new Set(dayGroups.map(g => String(g).toLowerCase().trim()));

    // include all candidates (finishers will be reserved later)
    const candidates = safeExercises.filter(ex => {
      const mg = (ex.muscleGroups || []).map(m => String(m).toLowerCase().trim());
      return mg.some(m => daySet.has(m)) || ex.isFinisher;
    });

    // If no candidates, return empty day
    if (!candidates || candidates.length === 0) {
      return { dayName: day.name, exercises: [] };
    }

    // Sort candidates by score descending with deterministic tie-breaker
    const scored = candidates
      .map(ex => ({ ex, score: scoreExerciseForDay(ex, daySet) }))
      .sort((a, b) => {
        if (b.score !== a.score) return b.score - a.score;
        // prefer primary
        if ((b.ex.isPrimary ? 1 : 0) !== (a.ex.isPrimary ? 1 : 0)) return (b.ex.isPrimary ? 1 : 0) - (a.ex.isPrimary ? 1 : 0);
        // prefer compound
        if ((b.ex.isCompound ? 1 : 0) !== (a.ex.isCompound ? 1 : 0)) return (b.ex.isCompound ? 1 : 0) - (a.ex.isCompound ? 1 : 0);
        return a.ex.name.localeCompare(b.ex.name);
      });

    const sorted = scored.map(s => s.ex);

    // Reserve 1 slot for finisher if any finishers exist for this day
    const finishers = sorted.filter(e => (e.isFinisher || (e.muscleGroups || []).map(m => String(m).toLowerCase().trim()).some(m => ['core', 'traps', 'grip'].includes(m))));
    const reserveFinisher = finishers.length > 0 ? 1 : 0;
    const targetMainSlots = Math.max(1, exercisesPerDay - reserveFinisher);

    // Selection strategy:
    // 1) Pick up to 2 primary/main lifts (isPrimary)
    // 2) Then pick compounds until targetMainSlots
    // 3) Then accessories until targetMainSlots
    // 4) Append 1 finisher if reserved

    const chosen = [];
    const chosenIds = new Set();

    function tryPush(item) {
      if (!item || !item.id) return false;
      if (chosenIds.has(item.id)) return false;
      chosen.push(item);
      chosenIds.add(item.id);
      return true;
    }

    const primaries = sorted.filter(e => e.isPrimary);
    for (const p of primaries) {
      if (chosen.length >= Math.min(2, targetMainSlots)) break;
      tryPush(p);
    }

    const compounds = sorted.filter(e => e.isCompound && !chosenIds.has(e.id));
    for (const c of compounds) {
      if (chosen.length >= targetMainSlots) break;
      tryPush(c);
    }

    const accessories = sorted.filter(e => !e.isCompound && !e.isFinisher && !chosenIds.has(e.id));
    for (const a of accessories) {
      if (chosen.length >= targetMainSlots) break;
      tryPush(a);
    }

    // If we still have room, fill from sorted candidates (non-finishers first)
    if (chosen.length < targetMainSlots) {
      for (const c of sorted) {
        if (chosen.length >= targetMainSlots) break;
        if (c.isFinisher) continue;
        tryPush(c);
      }
    }

    // Append one finisher at the end if reserved and available
    if (reserveFinisher === 1) {
      const fin = finishers.find(f => !chosenIds.has(f.id));
      if (fin) tryPush(fin);
    }

    // Final trim to exercisesPerDay and map to plan items
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
