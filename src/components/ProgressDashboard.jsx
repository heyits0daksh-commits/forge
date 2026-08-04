import React, { useState, useEffect } from 'react';
import { SPORT_DEFINITIONS, loadAthleteProfile, getAthleteWorkouts, analyzeProgress, predictNextProgress, detectWeaknesses, extractStrengthMarkers } from '../utils/sportAthleteEngine';

export default function ProgressDashboard({ athleteId }) {
  const [athlete, setAthlete] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [predictions, setPredictions] = useState(null);
  const [weaknesses, setWeaknesses] = useState([]);
  const [strengthMarkers, setStrengthMarkers] = useState({});
  const [selectedCategory, setSelectedCategory] = useState(null);

  useEffect(() => {
    const profile = loadAthleteProfile(athleteId);
    setAthlete(profile);

    if (profile) {
      const workouts = getAthleteWorkouts(athleteId);
      setSessions(workouts);

      if (workouts.length > 0) {
        const analysis = analyzeProgress(workouts, profile);
        setMetrics(analysis);
        setSelectedCategory(profile.sport_def?.categories[0] || null);

        const pred = predictNextProgress(workouts, profile);
        setPredictions(pred);

        const weak = detectWeaknesses(workouts, profile);
        setWeaknesses(weak);

        const markers = extractStrengthMarkers(workouts);
        setStrengthMarkers(markers);
      }
    }
  }, [athleteId]);

  if (!athlete || !metrics) {
    return <div style={{ padding: 20, textAlign: 'center' }}>Loading progress data...</div>;
  }

  const sportDef = SPORT_DEFINITIONS[athlete.sport];

  // Calculate volume trend
  const weeklyVolumes = Object.entries(metrics.weekly_volume).map(([week, vol]) => ({ week, volume: vol }));
  const latestVolume = weeklyVolumes.length > 0 ? weeklyVolumes[weeklyVolumes.length - 1].volume : 0;
  const prevVolume = weeklyVolumes.length > 1 ? weeklyVolumes[weeklyVolumes.length - 2].volume : 0;
  const volumeChange = prevVolume > 0 ? (((latestVolume - prevVolume) / prevVolume) * 100).toFixed(1) : 0;

  // Get category stats
  const categoryData = metrics.by_category[selectedCategory] || {};
  const sessionsTargetingCategory = categoryData.sessions_targeting?.length || 0;

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: 20 }}>
      <div style={{ marginBottom: 30 }}>
        <h2>{athlete.name} - {athlete.sport} Progress</h2>
        <div style={{ fontSize: 12, color: '#999' }}>
          {sessions.length} sessions logged • {metrics.total_sessions} total workouts
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 30 }}>
        <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 11, color: '#999', fontWeight: 600, marginBottom: 8 }}>Total Workouts</div>
          <div style={{ fontSize: 28, fontWeight: 700, color: sportDef.accent }}>{metrics.total_sessions}</div>
        </div>

        <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 11, color: '#999', fontWeight: 600, marginBottom: 8 }}>Avg RPE</div>
          <div style={{ fontSize: 28, fontWeight: 700, color: sportDef.accent }}>{metrics.average_rpe}/10</div>
        </div>

        <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 11, color: '#999', fontWeight: 600, marginBottom: 8 }}>Latest Volume</div>
          <div style={{ fontSize: 28, fontWeight: 700, color: sportDef.accent }}>{latestVolume.toLocaleString()}</div>
          <div style={{ fontSize: 11, color: volumeChange >= 0 ? '#2a9d2a' : '#d44', marginTop: 4 }}>
            {volumeChange >= 0 ? '↑' : '↓'} {Math.abs(volumeChange)}% from last week
          </div>
        </div>

        <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 11, color: '#999', fontWeight: 600, marginBottom: 8 }}>Unique Lifts</div>
          <div style={{ fontSize: 28, fontWeight: 700, color: sportDef.accent }}>{Object.keys(strengthMarkers).length}</div>
        </div>
      </div>

      {/* Sport-Specific Categories */}
      <div style={{ background: '#f9f9f9', border: '1px solid #eee', borderRadius: 8, padding: 16, marginBottom: 30 }}>
        <div style={{ fontWeight: 600, marginBottom: 12 }}>Sport-Specific Categories</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
          {sportDef.categories.map(category => {
            const catData = metrics.by_category[category] || {};
            const sessions = catData.sessions_targeting?.length || 0;
            const isSelected = selectedCategory === category;
            return (
              <div
                key={category}
                onClick={() => setSelectedCategory(category)}
                style={{
                  padding: 12,
                  background: isSelected ? `${sportDef.accent}15` : '#fff',
                  border: isSelected ? `2px solid ${sportDef.accent}` : '1px solid #ddd',
                  borderRadius: 6,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, textTransform: 'capitalize' }}>
                  {category.replace(/_/g, ' ')}
                </div>
                <div style={{ fontSize: 11, color: '#666' }}>
                  {sessions} sessions targeting
                </div>
                {sessions === 0 && (
                  <div style={{ fontSize: 10, color: '#d44', marginTop: 4 }}>⚠ Not trained yet</div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Category Detail */}
      {selectedCategory && (
        <div style={{ background: '#fff', border: `2px solid ${sportDef.accent}30`, borderRadius: 8, padding: 20, marginBottom: 30, borderLeft: `4px solid ${sportDef.accent}` }}>
          <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 16, textTransform: 'capitalize' }}>
            {selectedCategory.replace(/_/g, ' ')} - Training History
          </div>

          {sessionsTargetingCategory === 0 ? (
            <div style={{ color: '#999', fontSize: 14 }}>No sessions logged for this category yet.</div>
          ) : (
            <div>
              {categoryData.sessions_targeting?.map((session, idx) => (
                <div
                  key={idx}
                  style={{
                    background: '#f9f9f9',
                    padding: 12,
                    borderRadius: 6,
                    marginBottom: 10,
                    borderLeft: `3px solid ${sportDef.accent}`
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{session.exercise}</div>
                      <div style={{ fontSize: 11, color: '#999' }}>{session.date}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontWeight: 600, color: sportDef.accent }}>RPE {session.rpe}</div>
                      <div style={{ fontSize: 11, color: '#999' }}>{session.sets?.length || 0} sets</div>
                    </div>
                  </div>
                  {session.sets && session.sets.map((set, setIdx) => (
                    <div key={setIdx} style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                      Set {setIdx + 1}: {set.reps}x{set.weight}kg
                      {set.rpe && ` (RPE ${set.rpe})`}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Strength Markers */}
      <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 8, padding: 20, marginBottom: 30 }}>
        <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 16 }}>Personal Records by Lift</div>

        {Object.keys(strengthMarkers).length === 0 ? (
          <div style={{ color: '#999' }}>No lifts logged yet</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
            {Object.entries(strengthMarkers).map(([liftName, data]) => (
              <div
                key={liftName}
                style={{
                  background: '#f9f9f9',
                  border: '1px solid #eee',
                  borderRadius: 6,
                  padding: 14
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 10 }}>{liftName}</div>
                <div style={{ fontSize: 13, marginBottom: 6 }}>
                  <span style={{ color: '#999' }}>Max Weight:</span>
                  <span style={{ fontWeight: 600, color: sportDef.accent, marginLeft: 8 }}>{data.max_weight} kg</span>
                </div>
                <div style={{ fontSize: 13, marginBottom: 6 }}>
                  <span style={{ color: '#999' }}>Max Reps:</span>
                  <span style={{ fontWeight: 600, color: sportDef.accent, marginLeft: 8 }}>{data.max_reps}</span>
                </div>
                <div style={{ fontSize: 13 }}>
                  <span style={{ color: '#999' }}>Sessions:</span>
                  <span style={{ fontWeight: 600, color: sportDef.accent, marginLeft: 8 }}>{data.sessions_done}</span>
                </div>
                <div style={{ fontSize: 10, color: '#999', marginTop: 10 }}>
                  Last: {data.dates[data.dates.length - 1]}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Predictions */}
      {predictions && predictions.weeks_ahead.length > 0 && (
        <div style={{ background: '#e8f5ff', border: '1px solid #b3d9ff', borderRadius: 8, padding: 20, marginBottom: 30 }}>
          <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 16, color: '#0066cc' }}>
            📈 {predictions.prediction}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {predictions.weeks_ahead.map((pred, idx) => (
              <div key={idx} style={{ background: '#fff', padding: 12, borderRadius: 6 }}>
                <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>{pred.week}</div>
                <div style={{ fontSize: 13, color: '#0066cc', fontWeight: 600 }}>
                  {pred.predicted_volume.toLocaleString()}
                </div>
                <div style={{ fontSize: 10, color: '#666' }}>Projected Volume</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Weaknesses */}
      {weaknesses.length > 0 && (
        <div style={{ background: '#fff3cd', border: '1px solid #ffc107', borderRadius: 8, padding: 20, marginBottom: 30 }}>
          <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 16, color: '#856404' }}>
            ⚠️ Areas to Focus On
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 12 }}>
            {weaknesses.map((weakness, idx) => (
              <div
                key={idx}
                style={{
                  background: '#fff',
                  padding: 12,
                  borderRadius: 6,
                  borderLeft: weakness.priority === 'HIGH' ? '3px solid #dc3545' : '3px solid #ffc107'
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 4, textTransform: 'capitalize' }}>
                  {weakness.category.replace(/_/g, ' ')}
                </div>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
                  {weakness.reason}
                </div>
                <div
                  style={{
                    display: 'inline-block',
                    fontSize: 10,
                    fontWeight: 600,
                    padding: '3px 8px',
                    borderRadius: 3,
                    background: weakness.priority === 'HIGH' ? '#f8d7da' : '#fff3cd',
                    color: weakness.priority === 'HIGH' ? '#721c24' : '#856404'
                  }}
                >
                  {weakness.priority}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Weekly Volume Chart (Simple) */}
      {weeklyVolumes.length > 0 && (
        <div style={{ background: '#fff', border: '1px solid #eee', borderRadius: 8, padding: 20 }}>
          <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 16 }}>Weekly Volume Trend</div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 200, marginTop: 20 }}>
            {weeklyVolumes.slice(-8).map((week, idx) => {
              const maxVol = Math.max(...weeklyVolumes.map(w => w.volume)) || 1;
              const height = (week.volume / maxVol) * 150;
              return (
                <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <div
                    style={{
                      width: '100%',
                      height: height + 'px',
                      background: sportDef.accent,
                      borderRadius: '4px 4px 0 0',
                      marginBottom: 8
                    }}
                  />
                  <div style={{ fontSize: 10, color: '#999', textAlign: 'center' }}>
                    {week.week.split('-')[1]}
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ fontSize: 11, color: '#999', marginTop: 16, textAlign: 'center' }}>
            Volume = Sum of (Sets × Reps × Weight) per week
          </div>
        </div>
      )}
    </div>
  );
}
