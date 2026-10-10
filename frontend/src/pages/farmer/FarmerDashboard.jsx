import React, { useEffect, useState } from 'react';
import { monitoringService } from '../../services/monitoringService';
import { weatherService } from '../../services/weatherService';
import { marketService } from '../../services/marketService';
import {
  Thermometer,
  Droplets,
  AlertTriangle,
  CheckCircle,
  CloudSun,
  TrendingUp,
  Sprout,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  MessageSquare,
  Clock,
} from 'lucide-react';

export default function FarmerDashboard({ activeBatch, onNavigate }) {
  const [summary, setSummary] = useState(null);
  const [weather, setWeather] = useState(null);
  const [market, setMarket] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchDashboardData = async () => {
    if (!activeBatch) return;
    setLoading(true);
    try {
      const [sumData, wData, mData] = await Promise.all([
        monitoringService.getMonitoringSummary(activeBatch.batch_id).catch(() => null),
        weatherService.getBatchWeather(activeBatch.batch_id).catch(() => null),
        marketService.getBatchMarketPrices(activeBatch.batch_id).catch(() => null),
      ]);
      setSummary(sumData);
      setWeather(wData);
      setMarket(mData);
    } catch (err) {
      console.error('Error loading dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [activeBatch]);

  if (!activeBatch) {
    return (
      <div className="glass-panel" style={{ padding: '60px 40px', textAlign: 'center', maxWidth: '650px', margin: '40px auto' }}>
        <div style={{
          width: '70px',
          height: '70px',
          borderRadius: '50%',
          background: 'rgba(16, 185, 129, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px'
        }}>
          <Sprout size={36} color="#10b981" />
        </div>
        <h2 style={{ fontSize: '1.75rem', marginBottom: '12px' }}>Welcome to FarmShield</h2>
        <p style={{ color: '#94a3b8', marginBottom: '28px', lineHeight: 1.6 }}>
          You have no active crop storage batches configured. Begin by selecting your harvested crop to load source-backed scientific storage limits and activate real-time monitoring.
        </p>
        <button
          className="btn-primary"
          onClick={() => onNavigate('onboarding')}
          style={{ padding: '12px 28px', fontSize: '1rem', margin: '0 auto' }}
        >
          Start Crop Onboarding Wizard <ArrowRight size={18} />
        </button>
      </div>
    );
  }

  const crop = activeBatch.crop_profile || {};
  const currentTemp = summary?.current_temperature_c;
  const currentRH = summary?.current_humidity_percent;

  const isTempSafe = currentTemp != null && currentTemp >= crop.recommended_temperature_min_c && currentTemp <= crop.recommended_temperature_max_c;
  const isRHSafe = currentRH != null && currentRH >= crop.recommended_relative_humidity_min_percent && currentRH <= crop.recommended_relative_humidity_max_percent;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Banner Header */}
      <div className="glass-panel glow-border" style={{ padding: '24px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span className="badge badge-verified">
              <ShieldCheck size={12} /> ICAR Verified Profile
            </span>
            <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
              Batch ID: {activeBatch.batch_id}
            </span>
          </div>
          <h1 style={{ fontSize: '1.9rem', marginTop: '6px', color: '#f8fafc' }}>
            {activeBatch.custom_batch_name}
          </h1>
          <p style={{ color: '#94a3b8', fontSize: '0.95rem' }}>
            Crop: <strong style={{ color: '#34d399' }}>{crop.crop_name}</strong> • Structure: {activeBatch.storage_structure_type} • Quantity: {activeBatch.quantity_kg?.toLocaleString()} kg
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            className="btn-secondary"
            onClick={fetchDashboardData}
            title="Refresh Readings"
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
          </button>
          <button
            className="btn-primary"
            onClick={() => onNavigate('monitoring')}
          >
            Log Measurement <ArrowRight size={16} />
          </button>
        </div>
      </div>

      {/* Active Alerts Banner if any */}
      {summary?.active_alerts && summary.active_alerts.length > 0 && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid rgba(239, 68, 68, 0.35)',
          borderRadius: '16px',
          padding: '18px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#ef4444', fontWeight: '700' }}>
              <AlertTriangle size={22} />
              <span>Active Storage Violations Detected ({summary.active_alerts.length})</span>
            </div>
            <span style={{ fontSize: '0.82rem', color: '#cbd5e1' }}>
              Notifications dispatched automatically to registered farmer profile
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

            return (
              <div
                key={al.alert_id || idx}
                style={{
                  background: 'rgba(15, 23, 42, 0.75)',
                  borderLeft: isCrit ? '4px solid #ef4444' : '4px solid #f59e0b',
                  padding: '14px 18px',
                  borderRadius: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
                      <span className={`badge ${isCrit ? 'badge-critical' : 'badge-warning'}`}>
                        {al.condition_type.replace('_', ' ').toUpperCase()}
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
                    <div style={{ color: '#f8fafc', fontWeight: '600', fontSize: '0.96rem' }}>
                      {al.message}
                    </div>
                    <div style={{ fontSize: '0.84rem', color: '#94a3b8', marginTop: '4px' }}>
                      Actual: <strong style={{ color: isCrit ? '#f87171' : '#fbbf24' }}>{al.measured_value}{al.unit || '°C'}</strong>
                      {al.target_range_min != null && al.target_range_max != null && (
                        <span> • Safe Limit: <strong style={{ color: '#34d399' }}>{al.target_range_min}{al.unit}–{al.target_range_max}{al.unit}</strong></span>
                      )}
                    </div>
                  </div>

                  <button
                    className="btn-secondary"
                    style={{ fontSize: '0.82rem', padding: '6px 14px', alignSelf: 'center' }}
                    onClick={() => onNavigate('alerts')}
                  >
                    View Action Plan <ArrowRight size={14} />
                  </button>
                </div>

                {al.whatsapp_delivery_error && (
                  <div style={{
                    fontSize: '0.8rem',
                    color: '#fca5a5',
                    background: 'rgba(239, 68, 68, 0.1)',
                    padding: '6px 10px',
                    borderRadius: '6px',
                    borderLeft: '3px solid #ef4444'
                  }}>
                    ⚠️ <strong>Delivery Notice:</strong> {al.whatsapp_delivery_error}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Core Monitoring Metrics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        {/* Temperature Card */}
        <div className="glass-panel" style={{ padding: '24px', position: 'relative' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ background: 'rgba(239, 68, 68, 0.15)', padding: '10px', borderRadius: '12px' }}>
                <Thermometer size={24} color="#f87171" />
              </div>
              <div>
                <span style={{ color: '#94a3b8', fontSize: '0.88rem', fontWeight: '600' }}>Storage Temperature</span>
                <div style={{ fontSize: '2.2rem', fontWeight: '800', color: currentTemp != null ? (isTempSafe ? '#10b981' : '#f87171') : '#64748b' }}>
                  {currentTemp != null ? `${currentTemp}°C` : '--'}
                </div>
              </div>
            </div>
            <span className={`badge ${isTempSafe ? 'badge-verified' : (currentTemp == null ? 'badge-info' : 'badge-critical')}`}>
              {currentTemp != null ? (isTempSafe ? 'SAFE' : 'VIOLATION') : 'NO DATA'}
            </span>
          </div>

          <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '6px' }}>
              <span style={{ color: '#94a3b8' }}>Verified Target Range:</span>
              <strong style={{ color: '#f8fafc' }}>{crop.recommended_temperature_min_c}°C – {crop.recommended_temperature_max_c}°C</strong>
            </div>
            <div style={{ height: '8px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '999px', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: currentTemp != null ? `${Math.min(Math.max((currentTemp / 45) * 100, 5), 100)}%` : '0%',
                background: isTempSafe ? '#10b981' : '#ef4444',
                borderRadius: '999px'
              }} />
            </div>
          </div>
        </div>

        {/* Relative Humidity Card */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ background: 'rgba(59, 130, 246, 0.15)', padding: '10px', borderRadius: '12px' }}>
                <Droplets size={24} color="#60a5fa" />
              </div>
              <div>
                <span style={{ color: '#94a3b8', fontSize: '0.88rem', fontWeight: '600' }}>Relative Humidity</span>
                <div style={{ fontSize: '2.2rem', fontWeight: '800', color: currentRH != null ? (isRHSafe ? '#10b981' : '#f87171') : '#64748b' }}>
                  {currentRH != null ? `${currentRH}%` : '--'}
                </div>
              </div>
            </div>
            <span className={`badge ${isRHSafe ? 'badge-verified' : (currentRH == null ? 'badge-info' : 'badge-critical')}`}>
              {currentRH != null ? (isRHSafe ? 'OPTIMAL' : 'OUT OF BOUNDS') : 'NO DATA'}
            </span>
          </div>

          <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '6px' }}>
              <span style={{ color: '#94a3b8' }}>Target Humidity Range:</span>
              <strong style={{ color: '#f8fafc' }}>{crop.recommended_relative_humidity_min_percent}% – {crop.recommended_relative_humidity_max_percent}%</strong>
            </div>
            <div style={{ height: '8px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '999px', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: currentRH != null ? `${Math.min(Math.max((currentRH / 100) * 100, 5), 100)}%` : '0%',
                background: isRHSafe ? '#10b981' : '#f59e0b',
                borderRadius: '999px'
              }} />
            </div>
          </div>
        </div>

        {/* Moisture & Pest Safety Card */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ background: 'rgba(245, 158, 11, 0.15)', padding: '10px', borderRadius: '12px' }}>
                <CheckCircle size={24} color="#f59e0b" />
              </div>
              <div>
                <span style={{ color: '#94a3b8', fontSize: '0.88rem', fontWeight: '600' }}>Safe Crop Moisture</span>
                <div style={{ fontSize: '2.2rem', fontWeight: '800', color: '#f8fafc' }}>
                  {crop.recommended_crop_moisture_percent}%
                </div>
              </div>
            </div>
            <span className="badge badge-verified">MAX LIMIT</span>
          </div>

          <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <div style={{ fontSize: '0.84rem', color: '#cbd5e1' }}>
              <strong>Basis:</strong> {crop.moisture_basis}
            </div>
            <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '4px' }}>
              Source: {crop.source_name}
            </div>
          </div>
        </div>
      </div>

      {/* Two-Column Auxiliary Widgets: Weather Advisory & Mandi Prices */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        {/* Weather Card */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CloudSun size={20} color="#60a5fa" />
              <h3 style={{ fontSize: '1.15rem' }}>Ambient Weather & Aeration</h3>
            </div>
            <span className="badge badge-info">{weather?.freshness_status || 'LIVE'}</span>
          </div>

          {weather ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '14px' }}>
                <div style={{ fontSize: '1.8rem', fontWeight: '700' }}>
                  {weather.current_temperature_c}°C
                </div>
                <div style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                  {weather.weather_condition} • RH: {weather.current_humidity_percent}%
                </div>
              </div>
              <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '12px 14px', borderRadius: '10px', fontSize: '0.88rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                💡 <strong>Aeration Guidance:</strong> {weather.storage_impact_summary}
              </div>
            </div>
          ) : (
            <div style={{ color: '#64748b' }}>Loading weather data...</div>
          )}
        </div>

        {/* Mandi Prices Card */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <TrendingUp size={20} color="#34d399" />
              <h3 style={{ fontSize: '1.15rem' }}>APMC Mandi Market Prices</h3>
            </div>
            <span className="badge badge-verified">{market?.price_trend?.toUpperCase() || 'STABLE'}</span>
          </div>

          {market ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '12px' }}>
                <span style={{ fontSize: '1.8rem', fontWeight: '800', color: '#34d399' }}>
                  ₹{market.average_modal_price?.toLocaleString()}
                </span>
                <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>/ Quintal (Average Modal)</span>
              </div>
              <div style={{ fontSize: '0.86rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                {market.recommendation}
              </div>
            </div>
          ) : (
            <div style={{ color: '#64748b' }}>Loading market prices...</div>
          )}
        </div>
      </div>
    </div>
  );
}
