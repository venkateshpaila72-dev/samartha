import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';
import { Shield, Bell, Globe, LogOut, UserCheck } from 'lucide-react';

export default function Navbar({ activeBatch, batches, onSelectBatch, activeAlertsCount = 0 }) {
  const { user, logout } = useAuth();
  const { currentLang, changeLanguage, supportedLanguages } = useLanguage();

  return (
    <header style={{
      background: 'rgba(15, 23, 42, 0.85)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      padding: '12px 28px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 30
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
          width: '40px',
          height: '40px',
          borderRadius: '10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 12px rgba(16, 185, 129, 0.35)'
        }}>
          <Shield size={22} color="#ffffff" />
        </div>
        <div>
          <span style={{ fontSize: '1.25rem', fontWeight: '800', letterSpacing: '-0.02em', color: '#f8fafc' }}>
            Farm<span style={{ color: '#10b981' }}>Shield</span>
          </span>
          <span style={{ display: 'block', fontSize: '0.72rem', color: '#94a3b8', marginTop: '-2px' }}>
            AI Crop Storage & Preservation
          </span>
        </div>
      </div>

      {/* Middle: Active Storage Batch Selector */}
      {batches && batches.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Monitoring Batch:</span>
          <select
            value={activeBatch?.batch_id || ''}
            onChange={(e) => {
              const selected = batches.find(b => b.batch_id === e.target.value);
              if (selected) onSelectBatch(selected);
            }}
            style={{
              background: 'rgba(30, 41, 59, 0.9)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: '#f8fafc',
              padding: '6px 14px',
              borderRadius: '8px',
              fontSize: '0.9rem',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            {batches.map((b) => (
              <option key={b.batch_id} value={b.batch_id}>
                🌾 {b.custom_batch_name} ({b.crop_profile?.crop_name || 'Crop'})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Right Controls: Language, Alerts, User Menu */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
        {/* Language Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Globe size={18} color="#94a3b8" />
          <select
            value={currentLang}
            onChange={(e) => changeLanguage(e.target.value)}
            style={{
              background: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#cbd5e1',
              padding: '5px 10px',
              borderRadius: '6px',
              fontSize: '0.85rem',
              cursor: 'pointer'
            }}
          >
            {supportedLanguages.map(l => (
              <option key={l.code} value={l.code}>{l.native} ({l.name})</option>
            ))}
          </select>
        </div>

        {/* Alert Indicator */}
        <div style={{ position: 'relative', cursor: 'pointer' }}>
          <Bell size={20} color={activeAlertsCount > 0 ? '#f59e0b' : '#94a3b8'} />
          {activeAlertsCount > 0 && (
            <span style={{
              position: 'absolute',
              top: '-6px',
              right: '-8px',
              background: '#ef4444',
              color: '#fff',
              fontSize: '0.7rem',
              fontWeight: '700',
              borderRadius: '999px',
              padding: '1px 6px'
            }}>
              {activeAlertsCount}
            </span>
          )}
        </div>

        {/* User Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '999px',
            padding: '4px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <UserCheck size={16} color="#10b981" />
            <span style={{ fontSize: '0.85rem', fontWeight: '600', color: '#f8fafc' }}>
              {user?.full_name || 'Farmer'}
            </span>
            <span style={{ fontSize: '0.72rem', color: '#10b981', textTransform: 'uppercase' }}>
              [{user?.role || 'farmer'}]
            </span>
          </div>

          <button
            onClick={logout}
            title="Log out"
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: '#ef4444',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </header>
  );
}
