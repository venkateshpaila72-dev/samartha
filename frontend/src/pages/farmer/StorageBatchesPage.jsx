import React from 'react';
import { Sprout, PlusCircle, CheckCircle, ArrowRight, ShieldCheck, Calendar, MapPin, Scale } from 'lucide-react';

export default function StorageBatchesPage({ batches, activeBatch, onSelectBatch, onNavigate }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <span className="badge badge-verified">Workflow 3: Storage Batches & Multi-Crop Management</span>
          <h1 style={{ fontSize: '1.8rem', marginTop: '4px' }}>My Crop Storage Batches</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
            Manage multiple harvested crops, bins, and granary structures with isolated telemetry.
          </p>
        </div>

        <button className="btn-primary" onClick={() => onNavigate('onboarding')}>
          <PlusCircle size={18} /> New Storage Batch
        </button>
      </div>

      {/* Batches Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '20px' }}>
        {batches.map((b) => {
          const isSelected = activeBatch?.batch_id === b.batch_id;
          const crop = b.crop_profile || {};
          return (
            <div
              key={b.batch_id}
              className={`glass-panel ${isSelected ? 'glow-border' : ''}`}
              style={{
                padding: '24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
                border: isSelected ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.08)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <span className="badge badge-verified">{crop.crop_name || 'Crop'}</span>
                  <h3 style={{ fontSize: '1.25rem', marginTop: '6px', color: '#f8fafc' }}>
                    {b.custom_batch_name}
                  </h3>
                </div>
                {isSelected ? (
                  <span className="badge badge-verified" style={{ background: '#10b981', color: '#fff' }}>ACTIVE</span>
                ) : (
                  <button
                    className="btn-secondary"
                    style={{ fontSize: '0.8rem', padding: '4px 10px' }}
                    onClick={() => onSelectBatch(b)}
                  >
                    Select Batch
                  </button>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.86rem', color: '#cbd5e1' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Scale size={15} color="#94a3b8" /> {b.quantity_kg?.toLocaleString()} kg
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <MapPin size={15} color="#94a3b8" /> {b.storage_location}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Calendar size={15} color="#94a3b8" /> In: {b.storage_start_date}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Sprout size={15} color="#94a3b8" /> {b.storage_structure_type}
                </div>
              </div>

              {/* Target Limits Preview */}
              <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px 14px', borderRadius: '10px', fontSize: '0.82rem', color: '#94a3b8' }}>
                Target: <strong>{crop.recommended_temperature_min_c}–{crop.recommended_temperature_max_c}°C</strong> • RH: <strong>{crop.recommended_relative_humidity_min_percent}–{crop.recommended_relative_humidity_max_percent}%</strong> • Moisture: <strong>{crop.recommended_crop_moisture_percent}%</strong>
              </div>

              <div style={{ marginTop: 'auto', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                  ID: {b.batch_id}
                </span>
                <button
                  className="btn-primary"
                  style={{ fontSize: '0.85rem', padding: '6px 14px' }}
                  onClick={() => {
                    onSelectBatch(b);
                    onNavigate('dashboard');
                  }}
                >
                  Open Dashboard <ArrowRight size={14} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
