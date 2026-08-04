import React, { useState } from 'react';
import { SPORT_DEFINITIONS, AthleteProfile, saveAthleteProfile } from '../utils/sportAthleteEngine';

export default function AthleteSetup({ onProfileCreated }) {
  const [step, setStep] = useState(1); // 1: sport, 2: bio, 3: baseline tests
  const [selectedSport, setSelectedSport] = useState('');
  const [name, setName] = useState('');
  const [weight, setWeight] = useState('75');
  const [height, setHeight] = useState('180');
  const [experience, setExperience] = useState('1');
  const [baselineTests, setBaselineTests] = useState({});
  const [errors, setErrors] = useState([]);

  const sports = Object.keys(SPORT_DEFINITIONS);
  const currentSportDef = SPORT_DEFINITIONS[selectedSport];

  function handleSportSelect(sport) {
    setSelectedSport(sport);
    setBaselineTests({});
  }

  function handleNext() {
    const newErrors = [];

    if (step === 1 && !selectedSport) {
      newErrors.push('Please select a sport');
    }
    if (step === 2) {
      if (!name.trim()) newErrors.push('Name is required');
      if (!weight || parseFloat(weight) <= 0) newErrors.push('Valid weight required');
      if (!height || parseFloat(height) <= 0) newErrors.push('Valid height required');
    }
    if (step === 3 && currentSportDef) {
      currentSportDef.baseline_tests.forEach(test => {
        if (!baselineTests[test.name] || (Array.isArray(baselineTests[test.name]) && baselineTests[test.name].some(v => !v))) {
          newErrors.push(`${test.name} is required`);
        }
      });
    }

    if (newErrors.length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors([]);

    if (step === 3) {
      // Create athlete profile
      const profile = new AthleteProfile(name, selectedSport, parseFloat(weight), parseFloat(height), parseFloat(experience));
      profile.baseline_tests = baselineTests;
      const athleteId = saveAthleteProfile(profile);
      onProfileCreated(athleteId);
    } else {
      setStep(step + 1);
    }
  }

  function handleBaselineChange(testName, value, side = null) {
    if (side) {
      if (!baselineTests[testName]) baselineTests[testName] = {};
      baselineTests[testName][side] = value;
    } else {
      baselineTests[testName] = value;
    }
    setBaselineTests({ ...baselineTests });
  }

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: 20 }}>
      <h2>Athlete Setup</h2>
      <div style={{ marginBottom: 20, fontSize: 12, color: '#999' }}>
        Step {step} of 3
      </div>

      {errors.length > 0 && (
        <div style={{ background: '#fee', border: '1px solid #fcc', padding: 12, borderRadius: 8, marginBottom: 16 }}>
          {errors.map((e, i) => <div key={i} style={{ color: '#c33' }}>{e}</div>)}
        </div>
      )}

      {/* STEP 1: Sport Selection */}
      {step === 1 && (
        <div>
          <h3>Choose Your Sport</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
            {sports.map(sport => {
              const def = SPORT_DEFINITIONS[sport];
              return (
                <div
                  key={sport}
                  onClick={() => handleSportSelect(sport)}
                  style={{
                    padding: 16,
                    border: selectedSport === sport ? `2px solid ${def.accent}` : '1px solid #ddd',
                    borderRadius: 8,
                    cursor: 'pointer',
                    background: selectedSport === sport ? `${def.accent}10` : '#f9f9f9',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ fontSize: 24, marginBottom: 8 }}>{def.mono}</div>
                  <div style={{ fontWeight: 600 }}>{def.name}</div>
                  <div style={{ fontSize: 11, color: '#999' }}>{def.region}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* STEP 2: Biometrics */}
      {step === 2 && (
        <div>
          <h3>Athlete Information</h3>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Your name"
              style={{ width: '100%', padding: 10, border: '1px solid #ddd', borderRadius: 6, fontSize: 14 }}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>Weight (kg)</label>
              <input
                type="number"
                value={weight}
                onChange={e => setWeight(e.target.value)}
                style={{ width: '100%', padding: 10, border: '1px solid #ddd', borderRadius: 6, fontSize: 14 }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>Height (cm)</label>
              <input
                type="number"
                value={height}
                onChange={e => setHeight(e.target.value)}
                style={{ width: '100%', padding: 10, border: '1px solid #ddd', borderRadius: 6, fontSize: 14 }}
              />
            </div>
          </div>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>Experience (years)</label>
            <input
              type="number"
              value={experience}
              onChange={e => setExperience(e.target.value)}
              min="1"
              style={{ width: '100%', padding: 10, border: '1px solid #ddd', borderRadius: 6, fontSize: 14 }}
            />
          </div>
        </div>
      )}

      {/* STEP 3: Baseline Tests */}
      {step === 3 && currentSportDef && (
        <div>
          <h3>Baseline Tests ({selectedSport})</h3>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 16 }}>
            Record your current max or benchmark for each metric
          </div>
          {currentSportDef.baseline_tests.map((test, idx) => (
            <div key={idx} style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>
                {test.name} ({test.unit})
              </label>
              {test.sides ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  {test.sides.map(side => (
                    <div key={side}>
                      <input
                        type="number"
                        placeholder={`${side.charAt(0).toUpperCase() + side.slice(1)}`}
                        value={baselineTests[test.name]?.[side] || ''}
                        onChange={e => handleBaselineChange(test.name, e.target.value, side)}
                        style={{ width: '100%', padding: 10, border: '1px solid #ddd', borderRadius: 6, fontSize: 14 }}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <input
                  type="number"
                  placeholder={`Enter ${test.name}`}
                  value={baselineTests[test.name] || ''}
                  onChange={e => handleBaselineChange(test.name, e.target.value)}
                  style={{ width: '100%', padding: 10, border: '1px solid #ddd', borderRadius: 6, fontSize: 14 }}
                />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Navigation */}
      <div style={{ display: 'flex', gap: 10, marginTop: 30 }}>
        {step > 1 && (
          <button
            onClick={() => setStep(step - 1)}
            style={{
              flex: 1,
              padding: 12,
              border: '1px solid #ddd',
              borderRadius: 6,
              background: '#f9f9f9',
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            ← Back
          </button>
        )}
        <button
          onClick={handleNext}
          style={{
            flex: 1,
            padding: 12,
            border: 'none',
            borderRadius: 6,
            background: selectedSport ? SPORT_DEFINITIONS[selectedSport].accent : '#ccc',
            color: '#fff',
            cursor: 'pointer',
            fontWeight: 600
          }}
        >
          {step === 3 ? 'Create Athlete' : 'Next →'}
        </button>
      </div>
    </div>
  );
}
