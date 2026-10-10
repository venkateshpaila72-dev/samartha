import React, { useState, useEffect } from 'react';
import { monitoringService } from '../../services/monitoringService';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Send,
  RefreshCw,
  MessageSquare,
} from 'lucide-react';

export default function AlertsPage({ activeBatch }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [dispatchingId, setDispatchingId] = useState(null);
  const [dispatchMessage, setDispatchMessage] = useState(null);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const statusParam = filterStatus === 'all' ? null : filterStatus;
      const data = await monitoringService.getAlerts(activeBatch?.batch_id, statusParam);
      setAlerts(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [activeBatch, filterStatus]);

  const handleResolve = async (alertId) => {
    try {
      await monitoringService.updateAlertStatus(alertId, 'resolved');
      await loadAlerts();
    } catch (err) {
      alert(err.message || 'Error updating alert');
    }
  };

  const handleDispatchWhatsApp = async (alertId) => {
    setDispatchingId(alertId);
    setDispatchMessage(null);
    try {
      const res = await monitoringService.dispatchWhatsAppAlert(alertId);
      setDispatchMessage({
        type: res.success ? 'success' : 'error',
        text: res.message || (res.success ? 'WhatsApp alert dispatched.' : 'WhatsApp alert failed.'),
      });
      await loadAlerts();
    } catch (err) {
      setDispatchMessage({ type: 'error', text: err.message || 'WhatsApp dispatch request failed.' });
      await loadAlerts();
    } finally {
      setDispatchingId(null);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <span className="badge badge-warning">Workflow 11: Threshold Alerts & WhatsApp Notification Engine</span>
          <h1 style={{ fontSize: '1.8rem', marginTop: '4px' }}>Storage Alerts & WhatsApp Dispatch</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
            Active thresholds evaluated against verified crop limits with automatic debounce, farmer WhatsApp delivery tracking, and auto-resolution.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <select
            className="input-field"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            style={{ width: 'auto' }}
          >
            <option value="all">All Alerts</option>
            <option value="active">Active Only</option>
            <option value="resolved">Resolved Only</option>
          </select>
          <button className="btn-secondary" onClick={loadAlerts} title="Refresh Alerts">
            <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {dispatchMessage && (
        <div style={{
          padding: '12px 18px',
          borderRadius: '10px',
          background: dispatchMessage.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
          border: dispatchMessage.type === 'success' ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(239, 68, 68, 0.4)',
          color: dispatchMessage.type === 'success' ? '#34d399' : '#f87171',
          fontSize: '0.9rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{dispatchMessage.text}</span>
          <button
            onClick={() => setDispatchMessage(null)}
            style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', fontWeight: 'bold' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Alerts Stream */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {alerts.length === 0 ? (
          <div className="glass-panel" style={{ padding: '60px', textAlign: 'center' }}>
            <CheckCircle size={48} color="#10b981" style={{ margin: '0 auto 16px' }} />
            <h3 style={{ fontSize: '1.3rem' }}>No Environmental Alerts Found</h3>
            <p style={{ color: '#94a3b8', marginTop: '6px' }}>
              All storage parameters are currently within safe verified scientific boundaries.
            </p>
          </div>
        ) : (
          alerts.map((al) => {
            const isCrit = al.severity === 'critical';
            const isActive = al.status === 'active';
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
                key={al.alert_id}
                className="glass-panel"
                style={{
                  padding: '20px 24px',
                  borderLeft: isCrit ? '4px solid #ef4444' : (isActive ? '4px solid #f59e0b' : '4px solid #10b981'),
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  flexWrap: 'wrap',
                  gap: '16px'
                }}
              >
                <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start', flex: 1, minWidth: '280px' }}>
                  <div style={{
                    background: isCrit ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                    padding: '12px',
                    borderRadius: '12px'
                  }}>
                    <AlertTriangle size={24} color={isCrit ? '#ef4444' : '#f59e0b'} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                      <span className={`badge ${isCrit ? 'badge-critical' : 'badge-warning'}`}>
                        {al.condition_type?.replace('_', ' ').toUpperCase()}
                      </span>
                      <span className={`badge ${delivBadgeClass}`}>
                        <MessageSquare size={12} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                        {delivBadgeText}
                      </span>
                      <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                        Batch: {al.crop_name} (ID: {al.batch_id})
                      </span>
                      <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                        <Clock size={12} style={{ marginRight: '3px', verticalAlign: 'middle' }} />
                        {new Date(al.created_at).toLocaleString()}
                      </span>
                    </div>

                    <h3 style={{ fontSize: '1.15rem', marginTop: '6px', color: '#f8fafc' }}>
                      {al.message}
                    </h3>

                    {al.measured_value != null && (
                      <div style={{ fontSize: '0.86rem', color: '#cbd5e1', marginTop: '4px' }}>
                        Measured Reading: <strong style={{ color: isCrit ? '#f87171' : '#fbbf24' }}>{al.measured_value}{al.unit || '°C'}</strong>
                        {al.target_range_min != null && al.target_range_max != null && (
                          <span> • Target Limit: <strong style={{ color: '#34d399' }}>{al.target_range_min}{al.unit}–{al.target_range_max}{al.unit}</strong></span>
                        )}
                      </div>
                    )}

                    <div style={{ marginTop: '10px', background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '8px', fontSize: '0.88rem', color: '#cbd5e1' }}>
                      <strong>Recommended Corrective Action:</strong> {al.recommended_action}
                    </div>

                    <div style={{ marginTop: '8px', display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '0.8rem', color: '#94a3b8' }}>
                      {al.whatsapp_recipient_masked && (
                        <span>Destination: <strong style={{ color: '#e2e8f0' }}>{al.whatsapp_recipient_masked}</strong></span>
                      )}
                      {al.whatsapp_last_attempt_at && (
                        <span>Last Attempt: <strong style={{ color: '#e2e8f0' }}>{new Date(al.whatsapp_last_attempt_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong></span>
                      )}
                    </div>

                    {al.whatsapp_delivery_error && (
                      <div style={{
                        marginTop: '8px',
                        background: 'rgba(239, 68, 68, 0.1)',
                        borderLeft: '3px solid #ef4444',
                        padding: '8px 12px',
                        borderRadius: '6px',
                        fontSize: '0.82rem',
                        color: '#fca5a5'
                      }}>
                        ⚠️ <strong>Delivery Error / Action Required:</strong> {al.whatsapp_delivery_error}
                      </div>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
                  <span className={`badge ${isActive ? 'badge-warning' : 'badge-verified'}`}>
                    Alert State: {al.status?.toUpperCase()}
                  </span>

                  {isActive && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
                      <button
                        className="btn-primary"
                        style={{ fontSize: '0.82rem', padding: '6px 12px', whiteSpace: 'nowrap' }}
                        disabled={dispatchingId === al.alert_id}
                        onClick={() => handleDispatchWhatsApp(al.alert_id)}
                      >
                        <Send size={14} /> {dispatchingId === al.alert_id ? 'Dispatching…' : 'Dispatch WhatsApp Alert'}
                      </button>
                      <button
                        className="btn-secondary"
                        style={{ fontSize: '0.82rem', padding: '6px 12px', whiteSpace: 'nowrap' }}
                        onClick={() => handleResolve(al.alert_id)}
                      >
                        Mark as Resolved
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
