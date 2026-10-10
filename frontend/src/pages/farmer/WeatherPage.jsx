import React, { useState, useEffect } from 'react';
import { weatherService } from '../../services/monitoringService';
import { CloudSun, Wind, Droplets, Compass, ShieldCheck } from 'lucide-react';

export default function WeatherPage({ activeBatch }) {
  const [weather, setWeather] = useState(null);
  const [locationInput, setLocationInput] = useState('New Delhi, IN');
  const [loading, setLoading] = useState(false);

  const fetchWeather = async (loc = null) => {
    setLoading(true);
    try {
      const data = loc ? await weatherService.getWeather(loc) : (activeBatch ? await weatherService.getBatchWeather(activeBatch.batch_id) : await weatherService.getWeather('New Delhi, IN'));
      setWeather(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWeather();
  }, [activeBatch]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <span className="badge badge-info">Workflow 9: Weather Forecast & Storage Aeration Impact</span>
          <h1 style={{ fontSize: '1.8rem', marginTop: '4px' }}>Weather & Ambient Storage Advisory</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
            External atmospheric forecasts correlated with storage ventilation and condensation risk.
          </p>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); fetchWeather(locationInput); }} style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            className="input-field"
            value={locationInput}
            onChange={(e) => setLocationInput(e.target.value)}
            style={{ width: '220px' }}
          />
          <button type="submit" className="btn-primary">Search</button>
        </form>
      </div>

      {weather && (
        <>
          {/* Main Weather Card */}
          <div className="glass-panel glow-border" style={{ padding: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
            <div>
              <span className="badge badge-verified">{weather.location} • {weather.provider}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginTop: '12px' }}>
                <CloudSun size={64} color="#60a5fa" />
                <div>
                  <div style={{ fontSize: '3.2rem', fontWeight: '800', lineHeight: 1 }}>{weather.current_temperature_c}°C</div>
                  <div style={{ fontSize: '1.1rem', color: '#94a3b8', marginTop: '4px' }}>{weather.weather_condition}</div>
                </div>
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '20px 24px', borderRadius: '14px', maxWidth: '480px' }}>
              <div style={{ fontWeight: '700', color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <ShieldCheck size={18} /> Storage Impact Summary
              </div>
              <p style={{ fontSize: '0.92rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                {weather.storage_impact_summary}
              </p>
            </div>
          </div>

          {/* Forecast Cards */}
          <h3 style={{ fontSize: '1.3rem' }}>Next 24-48 Hours Forecast</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            {weather.forecast.map((fc, i) => (
              <div key={i} className="glass-panel" style={{ padding: '18px', textAlign: 'center' }}>
                <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '8px' }}>{fc.timestamp}</div>
                <CloudSun size={32} color="#60a5fa" style={{ margin: '0 auto 8px' }} />
                <div style={{ fontSize: '1.4rem', fontWeight: '700' }}>{fc.temperature_c}°C</div>
                <div style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '4px' }}>{fc.weather_condition}</div>
                <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '8px' }}>
                  💧 RH: {fc.humidity_percent}% • 💨 {fc.wind_speed_kmh} km/h
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
