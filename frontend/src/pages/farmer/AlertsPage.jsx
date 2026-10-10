import React, { useState, useEffect } from 'react';
import { monitoringService } from '../../services/monitoringService';
import {
  AlertTriangle,
  CheckCircle,
  Bell,
  Clock,
  ShieldAlert,
  Send,
  RefreshCw,
} from 'lucide-react';

export default function AlertsPage({ activeBatch }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');

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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <span className="badge badge-warning">Workflow 11: Threshold Alerts & WhatsApp Notification Engine</span>
          <h1 style={{ fontSize: '1.8rem', marginTop: '4px' }}>Storage Alerts & Incident Log</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
            Active thresholds evaluated against verified crop limits with automatic debounce and resolution tracking.
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
          <button className="btn-secondary" onClick={loadAlerts}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

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
            return (
              <div
                key={al.alert_id}
                className="glass-panel"
                style={{
                  padding: '20px 24px',
                  borderLeft: isCrit ? '4px solid #ef4444' : (isActive ? '4px solid #f59e0b' : '4px solid #10b981'),
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '16px'
                }}
              >
                <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                  <div style={{
                    background: isCrit ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                    padding: '12px',
                    borderRadius: '12px'
                  }}>
                    <AlertTriangle size={24} color={isCrit ? '#ef4444' : '#f59e0b'} />
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span className={`badge ${isCrit ? 'badge-critical' : 'badge-warning'}`}>
                        {al.condition_type?.replace('_', ' ').toUpperCase()}
                      </span>
                      <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                        Batch: {al.crop_name} (ID: {al.batch_id})
                      </span>
                      <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                        {new Date(al.created_at).toLocaleString()}
                      </span>
                    </div>

                    <h3 style={{ fontSize: '1.15rem', marginTop: '6px', color: '#f8fafc' }}>
                      {al.message}
                    </h3>

                    <div style={{ marginTop: '8px', background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '8px', fontSize: '0.88rem', color: '#cbd5e1' }}>
                      <strong>Recommended Corrective Action:</strong> {al.recommended_action}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
                  <span className={`badge ${isActive ? 'badge-warning' : 'badge-verified'}`}>
                    Status: {al.status?.toUpperCase()}
                  </span>
                  {isActive && (
                    <button
                      className="btn-primary"
                      style={{ fontSize: '0.85rem', padding: '6px 14px' }}
                      onClick={() => handleResolve(al.alert_id)}
                    >
                      Mark as Resolved
                    </button>
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
