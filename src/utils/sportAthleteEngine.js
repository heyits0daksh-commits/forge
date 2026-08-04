// src/utils/sportAthleteEngine.js
// Complete sport-agnostic athlete tracking engine for all 13 sports

// ============================================================
// SPORT DEFINITIONS - Define metrics, goals, tests per sport
// ============================================================
const SPORT_DEFINITIONS = {
  'Judo': {
    id: 'judo',
    name: 'Judo',
    region: 'Japan',
    mono: '柔',
    accent: '#B33A2E',
    categories: ['grip_strength', 'leg_drive', 'explosive_power', 'rotational_core', 'relative_strength'],
    baseline_tests: [
      { name: 'Grip Strength', unit: 'kg', sides: ['left', 'right'] },
      { name: 'Back Squat 1RM', unit: 'kg' },
      { name: 'Vertical Jump', unit: 'cm' },
      { name: 'Body Weight', unit: 'kg' }
    ],
    key_lifts: ['Back Squat', 'Deadlift', 'Farmer Carry', 'Trap Bar Deadlift'],
    weakness_indicators: ['grip_endurance_low', 'leg_drive_weak', 'explosive_power_low'],
    phase_recommendations: {
      'strength': 'Focus on 1RM gains in squat and deadlift',
      'power': 'Olympic lifts, jump training, explosive carries',
      'endurance': 'Grip endurance circuits, long holds'
    }
  },
  'Wrestling': {
    id: 'wrestling',
    name: 'Wrestling',
    region: 'Ancient Greece',
    mono: 'Π',
    accent: '#9C7A3C',
    categories: ['leg_drive', 'explosive_power', 'neck_strength', 'relative_strength'],
    baseline_tests: [
      { name: 'Front Squat 1RM', unit: 'kg' },
      { name: 'Leg Press Max', unit: 'kg' },
      { name: 'Vertical Jump', unit: 'cm' },
      { name: 'Body Weight', unit: 'kg' },
      { name: 'Neck Strength', unit: 'kg' }
    ],
    key_lifts: ['Front Squat', 'Leg Press', 'Trap Bar Deadlift', 'Weighted Shrugs'],
    weakness_indicators: ['leg_drive_weak', 'explosive_power_low', 'neck_weak'],
    phase_recommendations: {
      'strength': 'Heavy front squat, leg press work',
      'power': 'Jump squats, explosive leg work',
      'endurance': 'High-rep leg circuits, sled work'
    }
  },
  'Boxing': {
    id: 'boxing',
    name: 'Boxing',
    region: 'The Sweet Science',
    mono: 'B',
    accent: '#A6332B',
    categories: ['explosive_power', 'rotational_core', 'shoulder_stability', 'rfd'],
    baseline_tests: [
      { name: 'Medicine Ball Throw', unit: 'm' },
      { name: 'Vertical Jump', unit: 'cm' },
      { name: 'Rotational Power', unit: 'watts' },
      { name: 'Shoulder Mobility', unit: 'degrees' }
    ],
    key_lifts: ['Hang Clean', 'Pallof Press', 'Landmine Rotations', 'Push Press'],
    weakness_indicators: ['explosive_power_low', 'core_weak', 'shoulder_unstable'],
    phase_recommendations: {
      'strength': 'Heavy compound lifts with explosive intent',
      'power': 'Olympic lifting, medicine ball work, plyometrics',
      'endurance': 'High-rep combinations, circuit training'
    }
  },
  'Muay Thai': {
    id: 'muay_thai',
    name: 'Muay Thai',
    region: 'Thailand',
    mono: 'ม',
    accent: '#C9A227',
    categories: ['explosive_power', 'leg_drive', 'rotational_core', 'balance', 'relative_strength'],
    baseline_tests: [
      { name: 'Kick Power', unit: 'watts' },
      { name: 'Balance Test', unit: 'seconds' },
      { name: 'Vertical Jump', unit: 'cm' },
      { name: 'Hip Mobility', unit: 'degrees' }
    ],
    key_lifts: ['Back Squat', 'Landmine Rotations', 'Single-Leg RDL', 'Pallof Press'],
    weakness_indicators: ['leg_drive_weak', 'balance_poor', 'hip_mobility_limited'],
    phase_recommendations: {
      'strength': 'Bilateral and unilateral leg work, rotational strength',
      'power': 'Jump training, explosive rotations, dynamic balance',
      'endurance': 'High-rep rotational circuits, single-leg endurance'
    }
  },
  'Kickboxing': {
    id: 'kickboxing',
    name: 'Kickboxing',
    region: 'Japan',
    mono: '蹴',
    accent: '#8E4A8E',
    categories: ['explosive_power', 'leg_drive', 'rotational_core', 'balance'],
    baseline_tests: [
      { name: 'Kick Height', unit: 'cm' },
      { name: 'Kick Power', unit: 'watts' },
      { name: 'Horizontal Power', unit: 'm' },
      { name: 'Vertical Jump', unit: 'cm' }
    ],
    key_lifts: ['Back Squat', 'Jump Squats', 'Landmine Rotations', 'Single-Leg Work'],
    weakness_indicators: ['kick_height_low', 'explosive_power_low', 'balance_poor'],
    phase_recommendations: {
      'strength': 'Heavy bilateral and unilateral leg work',
      'power': 'Jump training, kick-specific power, plyometrics',
      'endurance': 'High-rep leg circuits, balance training'
    }
  },
  'Sambo': {
    id: 'sambo',
    name: 'Sambo',
    region: 'Russia',
    mono: 'С',
    accent: '#7C3F3F',
    categories: ['explosive_power', 'leg_drive', 'rotational_core', 'grip_strength', 'relative_strength'],
    baseline_tests: [
      { name: 'Back Squat 1RM', unit: 'kg' },
      { name: 'Grip Strength', unit: 'kg', sides: ['left', 'right'] },
      { name: 'Vertical Jump', unit: 'cm' },
      { name: 'Body Weight', unit: 'kg' }
    ],
    key_lifts: ['Back Squat', 'Trap Bar Deadlift', 'Farmer Carry', 'Landmine Rotations'],
    weakness_indicators: ['leg_drive_weak', 'grip_weak', 'explosive_power_low'],
    phase_recommendations: {
      'strength': 'Heavy squat, deadlift, grip work',
      'power': 'Explosive leg work, farmer carries, rotational power',
      'endurance': 'High-rep circuits, long carries'
    }
  },
  'BJJ': {
    id: 'bjj',
    name: 'BJJ',
    region: 'Brazil',
    mono: 'J',
    accent: '#2E7D46',
    categories: ['grip_strength_endurance', 'pulling_power', 'dynamic_stability', 'isometric_strength'],
    baseline_tests: [
      { name: 'Grip Endurance Hold', unit: 'seconds' },
      { name: 'Deadlift 1RM', unit: 'kg' },
      { name: 'Max Pullups', unit: 'reps' },
      { name: 'Pulling Power', unit: 'watts' }
    ],
    key_lifts: ['Heavy Rows', 'Farmer Holds', 'Pullups', 'Trap Bar Deadlift'],
    weakness_indicators: ['grip_endurance_low', 'pulling_power_weak', 'stability_poor'],
    phase_recommendations: {
      'strength': 'Heavy rows, deadlifts, grip work',
      'power': 'Explosive pulling, dynamic stability drills',
      'endurance': 'Long-duration holds, high-rep pulling circuits'
    }
  },
  'Sanda': {
    id: 'sanda',
    name: 'Sanda',
    region: 'China',
    mono: '散',
    accent: '#C77B3E',
    categories: ['explosive_power', 'leg_drive', 'rotational_core', 'balance'],
    baseline_tests: [
      { name: 'Leg Drive Power', unit: 'watts' },
      { name: 'Vertical Jump', unit: 'cm' },
      { name: 'Rotational Power', unit: 'watts' },
      { name: 'Balance', unit: 'seconds' }
    ],
    key_lifts: ['Back Squat', 'Landmine Rotations', 'Jump Squats', 'Single-Leg Work'],
    weakness_indicators: ['leg_drive_weak', 'explosive_power_low', 'balance_poor'],
    phase_recommendations: {
      'strength': 'Bilateral and unilateral leg work, rotational strength',
      'power': 'Jump training, explosive rotations, dynamic balance',
      'endurance': 'High-rep leg circuits, balance endurance'
    }
  },
  'Rugby': {
    id: 'rugby',
    name: 'Rugby',
    region: 'Union Football',
    mono: 'R',
    accent: '#5C2A2A',
    categories: ['explosive_power', 'relative_strength', 'leg_drive', 'collision_resistance'],
    baseline_tests: [
      { name: 'Back Squat 1RM', unit: 'kg' },
      { name: 'Vertical Jump', unit: 'cm' },
      { name: 'Power Output', unit: 'watts' },
      { name: 'Body Weight', unit: 'kg' }
    ],
    key_lifts: ['Back Squat', 'Deadlift', 'Push Press', 'Farmer Carry'],
    weakness_indicators: ['leg_drive_weak', 'explosive_power_low', 'relative_strength_low'],
    phase_recommendations: {
      'strength': 'Heavy compound lifts, low reps',
      'power': 'Olympic lifts, jump training, explosive carries',
      'endurance': 'High-rep circuits, sled work, loaded carries'
    }
  },
  'Rock Climbing': {
    id: 'rock_climbing',
    name: 'Rock Climbing',
    region: 'Rock & Alpine',
    mono: '▲',
    accent: '#5B6B73',
    categories: ['grip_strength', 'pulling_power', 'relative_strength', 'core_stability'],
    baseline_tests: [
      { name: 'Max Hang Time', unit: 'seconds' },
      { name: 'Max Pullups', unit: 'reps' },
      { name: 'Grip Strength', unit: 'kg' },
      { name: 'Body Weight', unit: 'kg' }
    ],
    key_lifts: ['Pullups', 'Hang Holds', 'Farmer Carries', 'Rows'],
    weakness_indicators: ['grip_strength_low', 'pulling_power_weak', 'core_weak'],
    phase_recommendations: {
      'strength': 'Heavy pulling, hang training, antagonist work',
      'power': 'Explosive pullups, dynamic holds',
      'endurance': 'High-rep circuits, long hangs, high-volume pulling'
    }
  },
  'HYROX': {
    id: 'hyrox',
    name: 'HYROX',
    region: 'Hybrid Race',
    mono: 'H',
    accent: '#3D6FE0',
    categories: ['work_capacity', 'relative_strength', 'explosive_power', 'endurance'],
    baseline_tests: [
      { name: 'Loaded Carry Distance', unit: 'm' },
      { name: 'Sled Push Power', unit: 'watts' },
      { name: 'Grip Endurance', unit: 'seconds' },
      { name: 'Body Weight', unit: 'kg' }
    ],
    key_lifts: ['Sled Push/Pull', 'Trap Bar Deadlift', 'Farmer Carry', 'Jump Squats'],
    weakness_indicators: ['work_capacity_low', 'explosive_power_low', 'endurance_weak'],
    phase_recommendations: {
      'strength': 'Heavy carries, sled work, compound lifts',
      'power': 'Explosive power development, jump training',
      'endurance': 'High-volume circuits, long carries, metabolic conditioning'
    }
  },
  'Special Forces': {
    id: 'special_forces',
    name: 'Special Forces',
    region: 'Tactical Conditioning',
    mono: '★',
    accent: '#55603F',
    categories: ['functional_strength', 'explosive_power', 'endurance_strength', 'loaded_carry', 'work_capacity'],
    baseline_tests: [
      { name: 'Loaded Carry', unit: 'kg' },
      { name: 'Grip Strength', unit: 'kg' },
      { name: 'Trap Bar Deadlift 1RM', unit: 'kg' },
      { name: 'Work Capacity', unit: 'reps' }
    ],
    key_lifts: ['Farmer Carry', 'Sled Push/Pull', 'Trap Bar Deadlift', 'Sandbag Complex'],
    weakness_indicators: ['work_capacity_low', 'grip_endurance_low', 'explosive_power_low'],
    phase_recommendations: {
      'strength': 'Heavy carries, deadlifts, grip work',
      'power': 'Explosive work, plyometrics, sprint training',
      'endurance': 'High-volume circuits, loaded carries, long-duration holds'
    }
  },
  'MMA': {
    id: 'mma',
    name: 'MMA',
    region: 'Mixed Martial Arts',
    mono: 'M',
    accent: '#1F2937',
    categories: ['relative_strength', 'explosive_power', 'grip_strength', 'leg_drive', 'rotational_core', 'rfd'],
    baseline_tests: [
      { name: 'Grip Strength', unit: 'kg', sides: ['left', 'right'] },
      { name: 'Back Squat 1RM', unit: 'kg' },
      { name: 'Vertical Jump', unit: 'cm' },
      { name: 'Power Output', unit: 'watts' },
      { name: 'Body Weight', unit: 'kg' }
    ],
    key_lifts: ['Deadlift', 'Back Squat', 'Farmer Carry', 'Trap Bar Work', 'Landmine Rotations'],
    weakness_indicators: ['relative_strength_low', 'explosive_power_low', 'grip_weak', 'rfd_low'],
    phase_recommendations: {
      'strength': 'Heavy compound lifts, all modalities',
      'power': 'Olympic lifting, explosive carries, jump training, rotational power',
      'endurance': 'High-rep circuits, grip endurance, rotational endurance'
    }
  }
};

// ============================================================
// ATHLETE DATA STRUCTURE & MANAGEMENT
// ============================================================
class AthleteProfile {
  constructor(name, sport, weight_kg, height_cm, experience_years = 1) {
    this.id = `athlete-${Date.now()}`;
    this.name = name;
    this.sport = sport;
    this.weight_kg = weight_kg;
    this.height_cm = height_cm;
    this.experience_years = experience_years;
    this.created_at = new Date().toISOString();
    this.competition_level = 'amateur';
    this.weight_class = this.calculateWeightClass(weight_kg, sport);
    this.sport_def = SPORT_DEFINITIONS[sport];
  }

  calculateWeightClass(weight, sport) {
    const classes = {
      'Judo': [55, 60, 66, 73, 81, 90, 100, '+100'],
      'Wrestling': [57, 61, 65, 70, 79, 92, 125],
      'Boxing': [50.8, 52, 54.9, 57.2, 60, 63.5, 67, 71.6, 81.8, 91],
      'MMA': [57, 61, 66, 70, 77, 84, 93, 120]
    };
    
    const sportClasses = classes[sport] || [50, 60, 70, 80, 90, 100, '+100'];
    for (const wc of sportClasses) {
      if (weight <= wc) return `${wc}kg`;
    }
    return `${sportClasses[sportClasses.length - 1]}kg`;
  }

  to_json() {
    return {
      id: this.id,
      name: this.name,
      sport: this.sport,
      weight_kg: this.weight_kg,
      height_cm: this.height_cm,
      experience_years: this.experience_years,
      created_at: this.created_at,
      competition_level: this.competition_level,
      weight_class: this.weight_class
    };
  }
}

// ============================================================
// WORKOUT SESSION LOGGING
// ============================================================
class WorkoutSession {
  constructor(athleteId, sport, phase = 'strength', duration_min = 60) {
    this.id = `session-${Date.now()}`;
    this.athlete_id = athleteId;
    this.date = new Date().toISOString().split('T')[0];
    this.sport = sport;
    this.phase = phase;
    this.duration_min = duration_min;
    this.rpe = 7;
    this.exercises = [];
    this.notes = '';
    this.readiness = {
      sleep_hours: 7.5,
      energy_level: 7,
      soreness_level: 3,
      mental_readiness: 8
    };
  }

  addExercise(name, sport_goal, sets_data) {
    this.exercises.push({
      name,
      sport_goal,
      sets: sets_data,
      movement_quality: 8,
      notes: ''
    });
  }

  to_json() {
    return {
      id: this.id,
      athlete_id: this.athlete_id,
      date: this.date,
      sport: this.sport,
      phase: this.phase,
      duration_min: this.duration_min,
      rpe: this.rpe,
      exercises: this.exercises,
      notes: this.notes,
      readiness: this.readiness
    };
  }
}

// ============================================================
// SPORT-SPECIFIC PROGRESS CALCULATIONS
// ============================================================
function calculateRelativeStrength(lift_1rm, bodyweight) {
  return parseFloat((lift_1rm / bodyweight).toFixed(2));
}

function calculateRFD(force_newtons, time_seconds) {
  return parseFloat((force_newtons / time_seconds).toFixed(2));
}

function calculatePowerOutput(force_newtons, velocity_ms) {
  return parseFloat((force_newtons * velocity_ms).toFixed(2));
}

function calculateWeeklyVolume(sessions) {
  let total = 0;
  sessions.forEach(session => {
    session.exercises.forEach(ex => {
      ex.sets.forEach(set => {
        const weight = set.weight || 0;
        const reps = set.reps || 0;
        total += weight * reps;
      });
    });
  });
  return total;
}

function analyzeProgress(sessions, athlete_profile) {
  const sport_def = SPORT_DEFINITIONS[athlete_profile.sport];
  const metrics = {};

  sport_def.categories.forEach(category => {
    metrics[category] = {
      sessions_targeting: [],
      trend: [],
      improvement_pct: 0
    };
  });

  sessions.forEach(session => {
    session.exercises.forEach(ex => {
      const goal = ex.sport_goal;
      if (metrics[goal]) {
        metrics[goal].sessions_targeting.push({
          date: session.date,
          exercise: ex.name,
          rpe: session.rpe,
          sets: ex.sets
        });
      }
    });
  });

  const volumeByWeek = {};
  sessions.forEach(session => {
    const week = getWeekKey(session.date);
    if (!volumeByWeek[week]) volumeByWeek[week] = 0;
    volumeByWeek[week] += calculateWeeklyVolume([session]);
  });

  return {
    by_category: metrics,
    weekly_volume: volumeByWeek,
    total_sessions: sessions.length,
    average_rpe: (sessions.reduce((sum, s) => sum + s.rpe, 0) / sessions.length).toFixed(1),
    strength_markers: extractStrengthMarkers(sessions)
  };
}

function extractStrengthMarkers(sessions) {
  const lifts = {};
  
  sessions.forEach(session => {
    session.exercises.forEach(ex => {
      if (!lifts[ex.name]) {
        lifts[ex.name] = {
          max_weight: 0,
          max_reps: 0,
          sessions_done: 0,
          dates: []
        };
      }
      
      ex.sets.forEach(set => {
        if (set.weight && set.weight > lifts[ex.name].max_weight) {
          lifts[ex.name].max_weight = set.weight;
        }
        if (set.reps && set.reps > lifts[ex.name].max_reps) {
          lifts[ex.name].max_reps = set.reps;
        }
      });
      
      lifts[ex.name].sessions_done += 1;
      lifts[ex.name].dates.push(session.date);
    });
  });

  return lifts;
}

function getWeekKey(dateString) {
  const date = new Date(dateString);
  const startOfYear = new Date(date.getFullYear(), 0, 1);
  const pastDaysOfYear = (date - startOfYear) / 86400000;
  const weekNumber = Math.ceil((pastDaysOfYear + startOfYear.getDay() + 1) / 7);
  return `${date.getFullYear()}-W${weekNumber}`;
}

function predictNextProgress(sessions, athlete_profile) {
  const metrics = analyzeProgress(sessions, athlete_profile);
  const volumeTrend = Object.values(metrics.weekly_volume);
  
  if (volumeTrend.length < 2) {
    return { prediction: 'Need more data', weeks_ahead: [] };
  }

  const avgWeeklyVolume = volumeTrend[volumeTrend.length - 1];
  const prevAvgWeeklyVolume = volumeTrend[volumeTrend.length - 2];
  const volumeGrowthRate = (avgWeeklyVolume - prevAvgWeeklyVolume) / prevAvgWeeklyVolume;

  const predictions = [];
  for (let i = 1; i <= 4; i++) {
    predictions.push({
      week: `Week +${i}`,
      predicted_volume: parseFloat((avgWeeklyVolume * Math.pow(1 + volumeGrowthRate, i)).toFixed(0)),
      estimated_rpe: 7.5
    });
  }

  return { prediction: 'Projected 4-week progression', weeks_ahead: predictions };
}

function detectWeaknesses(sessions, athlete_profile) {
  const sport_def = SPORT_DEFINITIONS[athlete_profile.sport];
  const metrics = analyzeProgress(sessions, athlete_profile);
  const weaknesses = [];

  sport_def.categories.forEach(category => {
    const data = metrics.by_category[category];
    if (data.sessions_targeting.length === 0) {
      weaknesses.push({
        category,
        reason: 'No sessions targeting this metric',
        priority: 'HIGH'
      });
    } else if (data.sessions_targeting.length < 2) {
      weaknesses.push({
        category,
        reason: 'Insufficient training volume for this metric',
        priority: 'MEDIUM'
      });
    }
  });

  return weaknesses;
}

// ============================================================
// LOCAL STORAGE MANAGEMENT
// ============================================================
function saveAthleteProfile(profile) {
  const athletes = JSON.parse(localStorage.getItem('forge_athletes') || '[]');
  const existingIndex = athletes.findIndex(a => a.id === profile.id);
  
  if (existingIndex >= 0) {
    athletes[existingIndex] = profile.to_json();
  } else {
    athletes.push(profile.to_json());
  }
  
  localStorage.setItem('forge_athletes', JSON.stringify(athletes));
  return profile.id;
}

function loadAthleteProfile(athleteId) {
  const athletes = JSON.parse(localStorage.getItem('forge_athletes') || '[]');
  return athletes.find(a => a.id === athleteId) || null;
}

function getAllAthletes() {
  return JSON.parse(localStorage.getItem('forge_athletes') || '[]');
}

function saveWorkoutSession(session) {
  const sessions = JSON.parse(localStorage.getItem('forge_sessions') || '[]');
  sessions.push(session.to_json());
  localStorage.setItem('forge_sessions', JSON.stringify(sessions));
  return session.id;
}

function getAthleteWorkouts(athleteId) {
  const sessions = JSON.parse(localStorage.getItem('forge_sessions') || '[]');
  return sessions.filter(s => s.athlete_id === athleteId);
}

function getAllWorkoutSessions() {
  return JSON.parse(localStorage.getItem('forge_sessions') || '[]');
}

function exportAthleteData(athleteId) {
  const profile = loadAthleteProfile(athleteId);
  const sessions = getAthleteWorkouts(athleteId);
  const metrics = analyzeProgress(sessions, profile);
  const predictions = predictNextProgress(sessions, profile);
  const weaknesses = detectWeaknesses(sessions, profile);

  return {
    athlete: profile,
    sessions: sessions,
    metrics: metrics,
    predictions: predictions,
    weaknesses: weaknesses,
    exported_at: new Date().toISOString()
  };
}

export {
  SPORT_DEFINITIONS,
  AthleteProfile,
  WorkoutSession,
  calculateRelativeStrength,
  calculateRFD,
  calculatePowerOutput,
  calculateWeeklyVolume,
  analyzeProgress,
  extractStrengthMarkers,
  predictNextProgress,
  detectWeaknesses,
  saveAthleteProfile,
  loadAthleteProfile,
  getAllAthletes,
  saveWorkoutSession,
  getAthleteWorkouts,
  getAllWorkoutSessions,
  exportAthleteData
};
