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
  CheckCircle,
  CheckCircle2,
  RefreshCw,
  MessageSquare,
  ArrowRight,
  Send,
  X,
} from 'lucide-react';

export default function MonitoringPage({ activeBatch, onNavigate }) {
  const [summary, setSummary] = useState(null);
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dispatchingId, setDispatchingId] = useState(null);
  const [dispatchFeedback, setDispatchFeedback] = useState(null);
  const [selectedActionAlert, setSelectedActionAlert] = useState(null);

  // Manual reading modal / form state
  const [tempInput, setTempInput] = useState('26.5');
  const [rhInput, setRhInput] = useState('62.0');
  const [provenanceInput, setProvenanceInput] = useState('manual');
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    if (!activeBatch) return;
    setLoading(true);
    try {
      const [sum, list, activeAlertsList] = await Promise.all([
        monitoringService.getMonitoringSummary(activeBatch.batch_id),
        monitoringService.getReadings(activeBatch.batch_id, 30),
        monitoringService.getAlerts(activeBatch.batch_id, 'active').catch(() => []),
      ]);

      const mergedSummary = sum ? { ...sum } : {};
      if (!mergedSummary.active_alerts || mergedSummary.active_alerts.length === 0) {
        mergedSummary.active_alerts = activeAlertsList || [];
      }

      setSummary(mergedSummary);
      setReadings(list || []);
    } catch (err) {
      console.error('Error loading monitoring data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    const handleSync = () => {
      loadData();
    };

    window.addEventListener('farmshield:alert-updated', handleSync);
    window.addEventListener('farmshield:reading-ingested', handleSync);

    return () => {
      window.removeEventListener('farmshield:alert-updated', handleSync);
      window.removeEventListener('farmshield:reading-ingested', handleSync);
    };
  }, [activeBatch?.batch_id]);

  const handleQuickDispatch = async (alertId) => {
    setDispatchingId(alertId);
    setDispatchFeedback(null);
    try {
      const res = await monitoringService.dispatchWhatsAppAlert(alertId);
      const isOk = Boolean(res.success || res.dispatched || ['accepted', 'queued', 'sent', 'delivered'].includes(res.status));
      setDispatchFeedback({
        alertId,
        type: isOk ? 'success' : 'error',
        text: res.message || (isOk ? 'WhatsApp alert dispatched via Twilio.' : 'Dispatch failed.'),
      });
      await loadData();
    } catch (err) {
      setDispatchFeedback({
        alertId,
        type: 'error',
        text: err.message || 'Twilio WhatsApp dispatch failed.',
      });
    } finally {
      setDispatchingId(null);
    }
  };

  const handleResolveAlert = async (alertId) => {
    try {
      await monitoringService.updateAlertStatus(alertId, 'resolved');
      setSelectedActionAlert(null);
      await loadData();
      window.dispatchEvent(new CustomEvent('farmshield:alert-updated', { detail: { alertId } }));
    } catch (err) {
      alert(err.message || 'Could not resolve alert.');
    }
  };

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
      window.dispatchEvent(new CustomEvent('farmshield:reading-ingested', { detail: { batch_id: activeBatch.batch_id } }));
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
        <button className="btn-secondary" onClick={loadData} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> {loading ? 'Refreshing...' : 'Refresh Telemetry'}
        </button>
      </div>

      {/* Active Alerts Banner */}
      {summary?.active_alerts && summary.active_alerts.length > 0 && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid rgba(239, 68, 68, 0.45)',
          borderRadius: '16px',
          padding: '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          boxShadow: '0 8px 24px rgba(239, 68, 68, 0.12)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#ef4444', fontWeight: '800', fontSize: '1.05rem' }}>
              <AlertTriangle size={24} />
              <span>ACTIVE STORAGE VIOLATION DETECTED ({summary.active_alerts.length})</span>
            </div>
            <span style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>
              Automatic alert evaluation against verified scientific limits
            </span>
          </div>

          {summary.active_alerts.map((al, idx) => {
            const isCrit = al.severity === 'critical';
            const delivStatus = (al.whatsapp_delivery_status || 'pending').toLowerCase();
            let delivBadgeClass = 'badge-info';
            let delivBadgeText = 'WhatsApp: PENDING';
            if (delivStatus === 'delivered') {
              delivBadgeClass = 'badge-verified';
              delivBadgeText = 'WhatsApp: DELIVERED';
            } else if (delivStatus === 'accepted' || delivStatus === 'queued' || delivStatus === 'sent') {
              delivBadgeClass = 'badge-verified';
              delivBadgeText = 'WhatsApp: ACCEPTED BY TWILIO';
            } else if (delivStatus === 'sandbox_not_opted_in') {
              delivBadgeClass = 'badge-warning';
              delivBadgeText = 'WhatsApp: SANDBOX OPT-IN REQUIRED';
            } else if (delivStatus.includes('fail') || delivStatus.includes('invalid') || delivStatus.includes('missing')) {
              delivBadgeClass = 'badge-critical';
              delivBadgeText = 'WhatsApp: DELIVERY FAILED';
            }

            const limitDisplay = (al.target_range_min != null && al.target_range_max != null)
              ? `${al.target_range_min}${al.unit || '°C'}–${al.target_range_max}${al.unit || '°C'}`
              : (al.target_threshold != null ? `${al.target_threshold}${al.unit || '°C'}` : 'Limit configured');

            return (
              <div
                key={al.alert_id || idx}
                style={{
                  background: 'rgba(15, 23, 42, 0.85)',
                  borderLeft: isCrit ? '5px solid #ef4444' : '5px solid #f59e0b',
                  padding: '16px 20px',
                  borderRadius: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div style={{ flex: 1, minWidth: '280px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '6px' }}>
                      <span className={`badge ${isCrit ? 'badge-critical' : 'badge-warning'}`} style={{ fontWeight: '700' }}>
                        {al.condition_type ? al.condition_type.replace('_', ' ').toUpperCase() : 'THRESHOLD VIOLATION'}
                      </span>
                      <span className={`badge ${isCrit ? 'badge-critical' : 'badge-warning'}`} style={{ fontSize: '0.75rem' }}>
                        SEVERITY: {al.severity ? al.severity.toUpperCase() : (isCrit ? 'CRITICAL' : 'WARNING')}
                      </span>
                      <span className={`badge ${delivBadgeClass}`} style={{ fontSize: '0.75rem' }}>
                        <MessageSquare size={12} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                        {delivBadgeText}
                      </span>
                      {al.whatsapp_recipient_masked && (
                        <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                          To: <strong style={{ color: '#cbd5e1' }}>{al.whatsapp_recipient_masked}</strong>
                        </span>
                      )}
                      {al.whatsapp_last_attempt_at && (
                        <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                          <Clock size={12} style={{ marginRight: '3px', verticalAlign: 'middle' }} />
                          {new Date(al.whatsapp_last_attempt_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>

                    <div style={{ color: '#f8fafc', fontWeight: '700', fontSize: '1.02rem', marginBottom: '4px' }}>
                      {al.message}
                    </div>

                    <div style={{ fontSize: '0.88rem', color: '#cbd5e1', display: 'flex', gap: '16px', flexWrap: 'wrap', margin: '6px 0' }}>
                      <span>Actual Reading: <strong style={{ color: isCrit ? '#f87171' : '#fbbf24', fontSize: '1rem' }}>{al.measured_value}{al.unit || '°C'}</strong></span>
                      <span>Verified Safe Limit: <strong style={{ color: '#34d399' }}>{limitDisplay}</strong></span>
                    </div>

                    <div style={{
                      background: 'rgba(255, 255, 255, 0.04)',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      borderLeft: '3px solid #38bdf8',
                      fontSize: '0.86rem',
                      color: '#e2e8f0',
                      marginTop: '8px'
                    }}>
                      <strong style={{ color: '#38bdf8' }}>Recommended Action: </strong>
                      {al.recommended_action || 'Inspect storage ventilation immediately and recheck readings.'}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexDirection: 'column', minWidth: '150px' }}>
                    <button
                      className="btn-primary"
                      style={{ fontSize: '0.82rem', padding: '8px 14px', width: '100%', justifyContent: 'center' }}
                      onClick={() => setSelectedActionAlert(al)}
                    >
                      Take Corrective Action <ArrowRight size={14} />
                    </button>
                    <button
                      className="btn-secondary"
                      style={{ fontSize: '0.82rem', padding: '7px 12px', width: '100%', justifyContent: 'center' }}
                      onClick={() => handleQuickDispatch(al.alert_id)}
                      disabled={dispatchingId === al.alert_id}
                    >
                      <MessageSquare size={13} /> {dispatchingId === al.alert_id ? 'Sending...' : 'Dispatch WhatsApp'}
                    </button>
                    {onNavigate && (
                      <button
                        style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '0.78rem', cursor: 'pointer', textAlign: 'center', marginTop: '2px' }}
                        onClick={() => onNavigate('alerts')}
                      >
                        View All Alerts →
                      </button>
                    )}
                  </div>
                </div>

                {dispatchFeedback && dispatchFeedback.alertId === al.alert_id && (
                  <div style={{
                    fontSize: '0.82rem',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    background: dispatchFeedback.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                    color: dispatchFeedback.type === 'success' ? '#34d399' : '#f87171',
                    border: dispatchFeedback.type === 'success' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)'
                  }}>
                    {dispatchFeedback.text}
                  </div>
                )}

                {al.whatsapp_delivery_error && (
                  <div style={{
                    fontSize: '0.8rem',
                    color: '#fca5a5',
                    background: 'rgba(239, 68, 68, 0.1)',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    borderLeft: '3px solid #ef4444'
                  }}>
                    ⚠️ <strong>Twilio Delivery Status:</strong> {al.whatsapp_delivery_error}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

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

      {/* Corrective Action Protocol Modal */}
      {selectedActionAlert && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div className="glass-panel" style={{
            maxWidth: '560px',
            width: '100%',
            padding: '28px',
            position: 'relative',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.15)'
          }}>
            <button
              onClick={() => setSelectedActionAlert(null)}
              style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer'
              }}
            >
              <X size={20} />
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <span className={`badge ${selectedActionAlert.severity === 'critical' ? 'badge-critical' : 'badge-warning'}`}>
                {selectedActionAlert.severity?.toUpperCase()} ALERT
              </span>
              <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                ID: {selectedActionAlert.alert_id}
              </span>
            </div>

            <h2 style={{ fontSize: '1.35rem', color: '#f8fafc', marginBottom: '14px' }}>
              Corrective Action Protocol: {selectedActionAlert.crop_name}
            </h2>

            <div style={{
              background: 'rgba(239, 68, 68, 0.12)',
              borderLeft: '4px solid #ef4444',
              padding: '12px 16px',
              borderRadius: '8px',
              marginBottom: '18px'
            }}>
              <div style={{ fontWeight: '600', color: '#f87171', fontSize: '0.95rem' }}>
                {selectedActionAlert.message}
              </div>
              <div style={{ fontSize: '0.86rem', color: '#cbd5e1', marginTop: '6px' }}>
                Measured Value: <strong>{selectedActionAlert.measured_value}{selectedActionAlert.unit || '°C'}</strong>
                {selectedActionAlert.target_range_max != null && (
                  <span> (Safe Limit: {selectedActionAlert.target_range_min ?? 15}{selectedActionAlert.unit}–{selectedActionAlert.target_range_max}{selectedActionAlert.unit})</span>
                )}
              </div>
            </div>

            <div style={{
              background: 'rgba(255, 255, 255, 0.04)',
              padding: '16px',
              borderRadius: '10px',
              marginBottom: '20px'
            }}>
              <div style={{ fontWeight: '600', color: '#38bdf8', marginBottom: '8px', fontSize: '0.92rem' }}>
                📋 Prescribed Steps:
              </div>
              <div style={{ fontSize: '0.9rem', color: '#e2e8f0', lineHeight: 1.6 }}>
                {selectedActionAlert.recommended_action}
              </div>
            </div>

            {selectedActionAlert.whatsapp_recipient_masked && (
              <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '16px' }}>
                WhatsApp Recipient: <strong style={{ color: '#e2e8f0' }}>{selectedActionAlert.whatsapp_recipient_masked}</strong>
                {selectedActionAlert.whatsapp_delivery_status && (
                  <span> • Status: <strong style={{ color: '#34d399' }}>{selectedActionAlert.whatsapp_delivery_status}</strong></span>
                )}
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button
                className="btn-secondary"
                style={{ flex: 1, justifyContent: 'center' }}
                disabled={dispatchingId === selectedActionAlert.alert_id}
                onClick={() => handleQuickDispatch(selectedActionAlert.alert_id)}
              >
                <Send size={15} /> {dispatchingId === selectedActionAlert.alert_id ? 'Dispatching...' : 'Dispatch WhatsApp Alert'}
              </button>
              <button
                className="btn-primary"
                style={{ flex: 1, justifyContent: 'center' }}
                onClick={() => handleResolveAlert(selectedActionAlert.alert_id)}
              >
                <CheckCircle size={15} /> Mark as Resolved
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
