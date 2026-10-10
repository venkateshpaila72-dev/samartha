import React, { useState, useEffect } from 'react';
import { adminService } from '../../services/monitoringService';
import {
  ShieldAlert,
  Database,
  Cpu,
  CloudCheck,
  CheckCircle,
  AlertTriangle,
  Users,
  RefreshCw,
  Server,
} from 'lucide-react';

export default function AdminDashboard() {
  const [data, setData] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [dash, uList] = await Promise.all([
        adminService.getDashboard(),
        adminService.getUsers(),
      ]);
      setData(dash);
      setUsers(uList);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  if (!data) {
    return <div className="glass-panel" style={{ padding: '40px', textAlign: 'center' }}>Loading system health & telemetry...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <span className="badge badge-warning">Workflow 14: Administrative Integrations & System Monitoring</span>
          <h1 style={{ fontSize: '1.8rem', marginTop: '4px' }}>System Control & Integration Diagnostics</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
            System readiness, MongoDB collection status, cloud credentials health, and notification delivery audit.
          </p>
        </div>

        <button className="btn-secondary" onClick={loadAdminData}>
          <RefreshCw size={16} /> Refresh Diagnostics
        </button>
      </div>

      {/* Top Counters Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Verified Crop Profiles</span>
          <div style={{ fontSize: '2rem', fontWeight: '800', color: '#10b981', marginTop: '4px' }}>
            {data.total_crop_profiles} Seeded
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>ICAR & FAO Standard Benchmarks</div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Registered Farmers</span>
          <div style={{ fontSize: '2rem', fontWeight: '800', color: '#60a5fa', marginTop: '4px' }}>
            {data.total_farmers} Accounts
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Isolated Farmer Tenancies</div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Active Storage Batches</span>
          <div style={{ fontSize: '2rem', fontWeight: '800', color: '#f59e0b', marginTop: '4px' }}>
            {data.total_active_batches} Active
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Across Warehouses & Bins</div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Active Threshold Violations</span>
          <div style={{ fontSize: '2rem', fontWeight: '800', color: data.total_active_alerts > 0 ? '#ef4444' : '#10b981', marginTop: '4px' }}>
            {data.total_active_alerts} Alerts
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Debounced State Tracking</div>
        </div>
      </div>

      {/* External Service Integration Diagnostics */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.25rem', marginBottom: '16px' }}>Service Integration Diagnostics</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
          {data.integrations.map((integ, idx) => {
            const isOk = integ.is_operational;
            return (
              <div
                key={idx}
                style={{
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: isOk ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(245, 158, 11, 0.25)',
                  borderRadius: '12px',
                  padding: '16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start'
                }}
              >
                <div>
                  <h4 style={{ fontSize: '1rem', color: '#f8fafc' }}>{integ.name}</h4>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '2px' }}>
                    Provider: {integ.provider}
                  </div>
                  <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '8px' }}>
                    {integ.notes}
                  </div>
                </div>
                <span className={`badge ${isOk ? 'badge-verified' : 'badge-warning'}`}>
                  {integ.status}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Registered Users Table */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.25rem', marginBottom: '16px' }}>Registered Accounts Audit ({users.length})</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
                <th style={{ padding: '12px 14px' }}>Name</th>
                <th style={{ padding: '12px 14px' }}>Email</th>
                <th style={{ padding: '12px 14px' }}>Role</th>
                <th style={{ padding: '12px 14px' }}>Preferred Language</th>
                <th style={{ padding: '12px 14px' }}>Location</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td style={{ padding: '12px 14px', fontWeight: '600', color: '#f8fafc' }}>{u.full_name}</td>
                  <td style={{ padding: '12px 14px', color: '#cbd5e1' }}>{u.email}</td>
                  <td style={{ padding: '12px 14px' }}>
                    <span className={`badge ${u.role === 'admin' ? 'badge-warning' : 'badge-verified'}`}>
                      {u.role}
                    </span>
                  </td>
                  <td style={{ padding: '12px 14px', color: '#94a3b8' }}>{u.preferred_language?.toUpperCase()}</td>
                  <td style={{ padding: '12px 14px', color: '#94a3b8' }}>{u.village_or_location || 'Not set'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
