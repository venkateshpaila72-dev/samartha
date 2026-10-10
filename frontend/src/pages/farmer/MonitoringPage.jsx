import React, { useState, useEffect } from 'react';
import { monitoringService } from '../../services/monitoringService';
import {
  Activity,
  Thermometer,
  Droplets,
  PlusCircle,
  AlertTriangle,
  Clock,
  Radio,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';

export default function MonitoringPage({ activeBatch }) {
  const [summary, setSummary] = useState(null);
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(false);

  // Manual reading modal / form state
  const [tempInput, setTempInput] = useState('26.5');
  const [rhInput, setRhInput] = useState('62.0');
  const [provenanceInput, setProvenanceInput] = useState('manual');
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    if (!activeBatch) return;
    setLoading(true);
    try {
      const [sum, list] = await Promise.all([
        monitoringService.getMonitoringSummary(activeBatch.batch_id),
        monitoringService.getReadings(activeBatch.batch_id, 30),
      ]);
      setSummary(sum);
      setReadings(list);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeBatch]);

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!activeBatch) return;
    setSubmitting(true);
    try {
      await monitoringService.ingestReading(activeBatch.batch_id, {
        batch_id: activeBatch.batch_id,
        temperature_c: Number(tempInput),
        relative_humidity_percent: Number(rhInput),
        sensor_id: provenanceInput === 'hardware_sensor' ? 'iot_dht22_node1' : 'manual_sensor_log',
        provenance: provenanceInput,
      });
      await loadData();
      alert('Measurement logged and evaluated against storage thresholds!');
    } catch (err) {
      alert(err.message || 'Error ingesting reading');
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuickSimulation = (scenario) => {
    const crop = activeBatch?.crop_profile || {};
    if (scenario === 'normal') {
      const midT = ((crop.recommended_temperature_min_c || 18) + (crop.recommended_temperature_max_c || 24)) / 2;
      const midRH = ((crop.recommended_relative_humidity_min_percent || 55) + (crop.recommended_relative_humidity_max_percent || 65)) / 2;
      setTempInput(midT.toFixed(1));
      setRhInput(midRH.toFixed(1));
      setProvenanceInput('simulated');
    } else if (scenario === 'hot') {
      setTempInput(((crop.recommended_temperature_max_c || 25) + 5.5).toFixed(1));
      setProvenanceInput('simulated');
    } else if (scenario === 'humid') {
      setRhInput(((crop.recommended_relative_humidity_max_percent || 65) + 12.0).toFixed(1));
      setProvenanceInput('simulated');
    }
  };

  if (!activeBatch) {
    return <div className="glass-panel" style={{ padding: '40px', textAlign: 'center' }}>Please select a batch from the top navigation.</div>;
  }

  const crop = activeBatch.crop_profile || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <span className="badge badge-verified">Workflow 4: Sensor & Environmental Monitoring</span>
          <h1 style={{ fontSize: '1.8rem', marginTop: '4px' }}>Sensor Ingestion & History Logs</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
            Batch: <strong>{activeBatch.custom_batch_name}</strong> ({crop.crop_name})
          </p>
        </div>
        <button className="btn-secondary" onClick={loadData}>
          <RefreshCw size={16} /> Refresh Telemetry
        </button>
      </div>

      {/* Latest telemetry from hardware or the HarvestStore simulator */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 style={{ marginTop: 0 }}>Latest Storage Environment Readings</h3>
        <p style={{ color: '#94a3b8', fontSize: '.85rem' }}>Values below are loaded from the saved backend monitoring summary.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))', gap: '12px' }}>
          {[
            ['Temperature', summary?.current_temperature_c, '°C'],
            ['Humidity', summary?.current_humidity_percent, '% RH'],
            ['CO₂', summary?.current_co2_ppm, 'ppm'],
            ['Air velocity', summary?.current_air_velocity_m_s, 'm/s'],
            ['Pressure', summary?.current_pressure_kpa, 'kPa'],
            ['Light intensity', summary?.current_light_lux, 'lux'],
          ].map(([label, value, unit]) => (
            <div key={label} style={{ padding: '14px', borderRadius: '12px', background: 'rgba(148,163,184,.08)', border: '1px solid rgba(148,163,184,.18)' }}>
              <div style={{ color: '#94a3b8', fontSize: '.8rem' }}>{label}</div>
              <div style={{ fontSize: '1.35rem', fontWeight: 700, marginTop: '7px' }}>{value == null ? 'No data' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })} <small style={{ fontSize: '.75rem', color: '#94a3b8' }}>{value == null ? '' : unit}</small></div>
            </div>
          ))}
        </div>
        {summary?.reading_provenance && <p style={{ color: '#94a3b8', fontSize: '.78rem', marginBottom: 0 }}>Source: {summary.reading_provenance} · Last reading: {summary.last_reading_time || 'unknown'}</p>}
      </div>

      {/* Verified crop-profile threshold limits */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 style={{ marginTop: 0 }}>Configured Threshold Limits</h3>
        <p style={{ color: '#94a3b8', fontSize: '.85rem', marginTop: 0 }}>
          Limits come from the selected crop's saved profile. A reading outside these ranges creates a storage alert; automatic WhatsApp delivery depends on Twilio configuration and opt-in.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
          <div style={{ padding: '14px', borderRadius: '12px', background: 'rgba(148,163,184,.08)', border: '1px solid rgba(148,163,184,.18)' }}>
            <strong>Temperature</strong>
            <div style={{ marginTop: '8px', color: '#34d399' }}>
              {summary?.target_temperature_min_c ?? crop.recommended_temperature_min_c ?? 15}°C – {summary?.target_temperature_max_c ?? crop.recommended_temperature_max_c ?? 25}°C
            </div>
            <small style={{ color: '#94a3b8' }}>Below minimum or above maximum triggers an alert.</small>
          </div>
          <div style={{ padding: '14px', borderRadius: '12px', background: 'rgba(148,163,184,.08)', border: '1px solid rgba(148,163,184,.18)' }}>
            <strong>Relative humidity</strong>
            <div style={{ marginTop: '8px', color: '#34d399' }}>
              {summary?.target_humidity_min_percent ?? crop.recommended_relative_humidity_min_percent ?? 50}% – {summary?.target_humidity_max_percent ?? crop.recommended_relative_humidity_max_percent ?? 70}%
            </div>
            <small style={{ color: '#94a3b8' }}>Below minimum or above maximum triggers an alert.</small>
          </div>
        </div>
      </div>

      {/* Ingestion & Simulation Tool */}
      <div className="glass-panel glow-border" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <h3 style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <PlusCircle size={20} color="#10b981" /> Log Environmental Measurement
          </h3>
          <div style={{ display: 'flex', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8', alignSelf: 'center' }}>Test Scenarios:</span>
            <button className="btn-secondary" style={{ fontSize: '0.78rem', padding: '4px 10px' }} onClick={() => handleQuickSimulation('normal')}>
              🟢 Safe Normal
            </button>
            <button className="btn-secondary" style={{ fontSize: '0.78rem', padding: '4px 10px', color: '#f87171' }} onClick={() => handleQuickSimulation('hot')}>
              🔴 Temperature Spike
            </button>
            <button className="btn-secondary" style={{ fontSize: '0.78rem', padding: '4px 10px', color: '#fbbf24' }} onClick={() => handleQuickSimulation('humid')}>
              🟡 High Moisture Spurt
            </button>
          </div>
        </div>

        <form onSubmit={handleIngest} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', alignItems: 'flex-end' }}>
          <div>
            <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Temperature (°C)</label>
            <input
              type="number"
              step="0.1"
              required
              className="input-field"
              value={tempInput}
              onChange={(e) => setTempInput(e.target.value)}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Relative Humidity (%)</label>
            <input
              type="number"
              step="0.1"
              required
              className="input-field"
              value={rhInput}
              onChange={(e) => setRhInput(e.target.value)}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Source Provenance</label>
            <select
              className="input-field"
              value={provenanceInput}
              onChange={(e) => setProvenanceInput(e.target.value)}
            >
              <option value="manual">Manual Farmer Entry</option>
              <option value="hardware_sensor">Hardware IoT Sensor</option>
              <option value="simulated">Test Simulation</option>
            </select>
          </div>
          <div>
            <button type="submit" disabled={submitting} className="btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
              {submitting ? 'Evaluating...' : 'Submit Reading'}
            </button>
          </div>
        </form>
      </div>

      {/* Historical Telemetry Table */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.2rem', marginBottom: '16px' }}>Measurement History Log ({readings.length})</h3>

        {readings.length === 0 ? (
          <div style={{ color: '#64748b', textAlign: 'center', padding: '30px' }}>
            No measurements recorded yet for this batch. Use the form above to log readings.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
                  <th style={{ padding: '12px 14px' }}>Timestamp</th>
                  <th style={{ padding: '12px 14px' }}>Temperature</th>
                  <th style={{ padding: '12px 14px' }}>Rel. Humidity</th>
                  <th style={{ padding: '12px 14px' }}>Provenance</th>
                  <th style={{ padding: '12px 14px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {readings.map((r, i) => {
                  const tSafe = r.is_temperature_in_range;
                  const rhSafe = r.is_humidity_in_range;
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                      <td style={{ padding: '12px 14px', color: '#cbd5e1' }}>
                        {new Date(r.timestamp).toLocaleString()}
                      </td>
                      <td style={{ padding: '12px 14px', fontWeight: '700', color: tSafe ? '#10b981' : '#f87171' }}>
                        {r.temperature_c}°C
                      </td>
                      <td style={{ padding: '12px 14px', fontWeight: '700', color: rhSafe ? '#10b981' : '#fbbf24' }}>
                        {r.relative_humidity_percent}%
                      </td>
                      <td style={{ padding: '12px 14px' }}>
                        <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>
                          {r.provenance}
                        </span>
                      </td>
                      <td style={{ padding: '12px 14px' }}>
                        {tSafe && rhSafe ? (
                          <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <CheckCircle2 size={16} /> Safe
                          </span>
                        ) : (
                          <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <AlertTriangle size={16} /> Violation
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
