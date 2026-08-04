import React, { useState, useEffect } from 'react';
import AthleteSetup from './AthleteSetup';
import WorkoutLogger from './WorkoutLogger';
import ProgressDashboard from './ProgressDashboard';
import { getAllAthletes, exportAthleteData } from '../utils/sportAthleteEngine';

export default function AthleteApp() {
  const [screen, setScreen] = useState('home'); // 'home', 'setup', 'logger', 'dashboard', 'athletes'
  const [athletes, setAthletes] = useState([]);
  const [selectedAthlete, setSelectedAthlete] = useState(null);

  useEffect(() => {
    loadAthletes();
  }, []);

  function loadAthletes() {
    const data = getAllAthletes();
    setAthletes(data);
  }

  function handleProfileCreated(athleteId) {
    loadAthletes();
    setSelectedAthlete(athleteId);
    setScreen('logger');
  }

  function handleExportData(athleteId) {
    const data = exportAthleteData(athleteId);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `athlete-${athleteId}-export.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleDeleteAthlete(athleteId) {
    if (confirm('Are you sure? This will delete all workouts for this athlete.')) {
      const updated = athletes.filter(a => a.id !== athleteId);
      localStorage.setItem('forge_athletes', JSON.stringify(updated));
      
      // Also delete workouts
      const sessions = JSON.parse(localStorage.getItem('forge_sessions') || '[]');
      const filteredSessions = sessions.filter(s => s.athlete_id !== athleteId);
      localStorage.setItem('forge_sessions', JSON.stringify(filteredSessions));
      
      loadAthletes();
      setScreen('athletes');
    }
  }

  // HOME SCREEN
  if (screen === 'home') {
    return (
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: 40, textAlign: 'center' }}>
        <div style={{ marginBottom: 40 }}>
          <h1 style={{ fontSize: 48, fontWeight: 800, marginBottom: 10 }}>FORGE</h1>
          <p style={{ fontSize: 18, color: '#666', marginBottom: 30 }}>
            Sport-Specific Strength Training Tracker<br/>
            Track progress. Predict performance. Master your sport.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20, marginBottom: 40 }}>
          <div
            onClick={() => athletes.length > 0 ? setScreen('athletes') : setScreen('setup')}
            style={{
              padding: 30,
              background: '#f0f5ff',
              border: '2px solid #5B9CFF',
              borderRadius: 12,
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
            onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-4px)'}
            onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <div style={{ fontSize: 32, marginBottom: 12 }}>👤</div>
            <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 6 }}>
              {athletes.length > 0 ? 'My Athletes' : 'New Athlete'}
            </div>
            <div style={{ fontSize: 13, color: '#666' }}>
              {athletes.length > 0 ? `${athletes.length} athlete${athletes.length !== 1 ? 's' : ''}` : 'Create your first athlete profile'}
            </div>
          </div>

          <div
            onClick={() => setScreen('setup')}
            style={{
              padding: 30,
              background: '#f5f0ff',
              border: '2px solid #E8A33D',
              borderRadius: 12,
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
            onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-4px)'}
            onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <div style={{ fontSize: 32, marginBottom: 12 }}>⚙️</div>
            <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 6 }}>New Athlete</div>
            <div style={{ fontSize: 13, color: '#666' }}>Setup a new athlete profile</div>
          </div>

          <div
            onClick={() => athletes.length > 0 ? setScreen('athletes') : null}
            style={{
              padding: 30,
              background: athletes.length > 0 ? '#f0fff5' : '#eee',
              border: athletes.length > 0 ? '2px solid #34C77B' : '2px dashed #ccc',
              borderRadius: 12,
              cursor: athletes.length > 0 ? 'pointer' : 'not-allowed',
              opacity: athletes.length > 0 ? 1 : 0.6,
              transition: 'all 0.2s'
            }}
            onMouseEnter={e => athletes.length > 0 && (e.currentTarget.style.transform = 'translateY(-4px)')}
            onMouseLeave={e => athletes.length > 0 && (e.currentTarget.style.transform = 'translateY(0)')}
          >
            <div style={{ fontSize: 32, marginBottom: 12 }}>📊</div>
            <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 6 }}>View Progress</div>
            <div style={{ fontSize: 13, color: '#666' }}>
              {athletes.length > 0 ? 'View your training analytics' : 'Create an athlete first'}
            </div>
          </div>
        </div>

        {athletes.length > 0 && (
          <div style={{ marginTop: 40, padding: 20, background: '#f9f9f9', borderRadius: 8 }}>
            <div style={{ fontWeight: 600, marginBottom: 12 }}>Recent Athletes</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {athletes.slice(-3).map(athlete => (
                <button
                  key={athlete.id}
                  onClick={() => {
                    setSelectedAthlete(athlete.id);
                    setScreen('logger');
                  }}
                  style={{
                    padding: '10px 16px',
                    background: '#fff',
                    border: '1px solid #ddd',
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontWeight: 600,
                    fontSize: 13
                  }}
                >
                  {athlete.name} ({athlete.sport})
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ATHLETES LIST SCREEN
  if (screen === 'athletes') {
    return (
      <div style={{ maxWidth: 1000, margin: '0 auto', padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 30 }}>
          <div>
            <h2>My Athletes</h2>
            <div style={{ fontSize: 12, color: '#999' }}>{athletes.length} athlete{athletes.length !== 1 ? 's' : ''}</div>
          </div>
          <button
            onClick={() => setScreen('home')}
            style={{
              padding: '10px 20px',
              background: '#f0f0f0',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            ← Home
          </button>
        </div>

        {athletes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
            <div style={{ fontSize: 40, marginBottom: 20 }}>📭</div>
            <div style={{ fontSize: 16, marginBottom: 20 }}>No athletes yet</div>
            <button
              onClick={() => setScreen('setup')}
              style={{
                padding: '12px 24px',
                background: '#E8A33D',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              Create First Athlete
            </button>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 20 }}>
            {athletes.map(athlete => (
              <div
                key={athlete.id}
                style={{
                  background: '#fff',
                  border: '1px solid #eee',
                  borderRadius: 8,
                  padding: 20,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
                }}
              >
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{athlete.name}</div>
                  <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>
                    {athlete.sport} • {athlete.weight_class}
                  </div>
                  <div style={{ fontSize: 11, color: '#999' }}>
                    Joined {new Date(athlete.created_at).toLocaleDateString()}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                  <button
                    onClick={() => {
                      setSelectedAthlete(athlete.id);
                      setScreen('logger');
                    }}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      background: '#5B9CFF',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 4,
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: 12
                    }}
                  >
                    Log Workout
                  </button>
                  <button
                    onClick={() => {
                      setSelectedAthlete(athlete.id);
                      setScreen('dashboard');
                    }}
                    style={{
                      flex: 1,
                      padding: '8px 12px',
                      background: '#34C77B',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 4,
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: 12
                    }}
                  >
                    Analytics
                  </button>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    onClick={() => handleExportData(athlete.id)}
                    style={{
                      flex: 1,
                      padding: '6px 10px',
                      background: '#f0f0f0',
                      border: '1px solid #ddd',
                      borderRadius: 4,
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: 11
                    }}
                  >
                    📥 Export
                  </button>
                  <button
                    onClick={() => handleDeleteAthlete(athlete.id)}
                    style={{
                      flex: 1,
                      padding: '6px 10px',
                      background: '#fee',
                      border: '1px solid #fcc',
                      color: '#c33',
                      borderRadius: 4,
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: 11
                    }}
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // SETUP SCREEN
  if (screen === 'setup') {
    return (
      <div>
        <div style={{ padding: 20, background: '#f9f9f9', borderBottom: '1px solid #eee', marginBottom: 20 }}>
          <button
            onClick={() => setScreen(athletes.length > 0 ? 'athletes' : 'home')}
            style={{
              padding: '8px 16px',
              background: '#f0f0f0',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: 13
            }}
          >
            ← Back
          </button>
        </div>
        <AthleteSetup onProfileCreated={handleProfileCreated} />
      </div>
    );
  }

  // LOGGER SCREEN
  if (screen === 'logger' && selectedAthlete) {
    return (
      <div>
        <div style={{ padding: 20, background: '#f9f9f9', borderBottom: '1px solid #eee', marginBottom: 20 }}>
          <button
            onClick={() => setScreen('athletes')}
            style={{
              padding: '8px 16px',
              background: '#f0f0f0',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: 13
            }}
          >
            ← Back to Athletes
          </button>
        </div>
        <WorkoutLogger athleteId={selectedAthlete} />
      </div>
    );
  }

  // DASHBOARD SCREEN
  if (screen === 'dashboard' && selectedAthlete) {
    return (
      <div>
        <div style={{ padding: 20, background: '#f9f9f9', borderBottom: '1px solid #eee', marginBottom: 20 }}>
          <button
            onClick={() => setScreen('athletes')}
            style={{
              padding: '8px 16px',
              background: '#f0f0f0',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: 13
            }}
          >
            ← Back to Athletes
          </button>
        </div>
        <ProgressDashboard athleteId={selectedAthlete} />
      </div>
    );
  }

  return null;
}
