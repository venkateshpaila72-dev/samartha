import React, { useState, useEffect } from 'react';
import { cropService, storageBatchService } from '../../services/cropService';
import {
  Sprout,
  CheckCircle,
  ShieldCheck,
  ArrowRight,
  Info,
  Calendar,
  Layers,
  MapPin,
  Scale,
} from 'lucide-react';

export default function CropOnboardingPage({ onBatchCreated }) {
  const [crops, setCrops] = useState([]);
  const [selectedCrop, setSelectedCrop] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Form fields
  const [batchName, setBatchName] = useState('');
  const [quantityKg, setQuantityKg] = useState('');
  const [harvestDate, setHarvestDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [storageStartDate, setStorageStartDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [storageStructure, setStorageStructure] = useState('Hermetic Bag / Traditional Bin');
  const [storageLocation, setStorageLocation] = useState('Farm Main Storage');

  useEffect(() => {
    async function loadCrops() {
      setLoading(true);
      try {
        const data = await cropService.getCrops();
        setCrops(data);
        if (data && data.length > 0) {
          handleSelectCrop(data[0]);
        }
      } catch (err) {
        setError('Failed to load crop profiles from server.');
      } finally {
        setLoading(false);
      }
    }
    loadCrops();
  }, []);

  const handleSelectCrop = (crop) => {
    setSelectedCrop(crop);
    setBatchName(`${crop.crop_name} - ${new Date().toLocaleDateString('en-US', { month: 'short', year: 'numeric' })} Harvest`);
    setStorageStructure(crop.storage_type.split('/')[0].trim());
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedCrop) return;
    if (!quantityKg || Number(quantityKg) <= 0) {
      alert('Please enter a valid harvest quantity in kg.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        crop_id: selectedCrop.crop_id,
        custom_batch_name: batchName,
        quantity_kg: Number(quantityKg),
        harvest_date: harvestDate,
        storage_start_date: storageStartDate,
        storage_structure_type: storageStructure,
        storage_location: storageLocation,
        initial_crop_condition: 'Clean, healthy, sun-dried harvest',
      };

      const newBatch = await storageBatchService.createBatch(payload);
      alert(`Storage batch '${newBatch.custom_batch_name}' created successfully!`);
      if (onBatchCreated) {
        onBatchCreated(newBatch);
      }
    } catch (err) {
      setError(err.message || 'Failed to create storage batch.');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredCrops = crops.filter(c =>
    c.crop_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.crop_category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Header */}
      <div>
        <span className="badge badge-verified" style={{ marginBottom: '8px' }}>
          <ShieldCheck size={14} /> Workflow 2: Crop Onboarding & Scientific Profile Association
        </span>
        <h1 style={{ fontSize: '2rem', marginTop: '6px' }}>First-Time Crop Selection & Storage Onboarding</h1>
        <p style={{ color: '#94a3b8', fontSize: '0.95rem', maxWidth: '750px', lineHeight: 1.5 }}>
          Select your harvested crop to automatically load verified agricultural storage parameters (ICAR/FAO standards). All monitoring rules, alert thresholds, and AI recommendations will be dynamically governed by this profile.
        </p>
      </div>

      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#f87171', padding: '14px 18px', borderRadius: '10px' }}>
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        {/* Step 1: Crop Selection List */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sprout size={20} color="#10b981" /> 1. Select Harvested Crop
            </h3>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{crops.length} Verified Crops</span>
          </div>

          <input
            type="text"
            className="input-field"
            placeholder="Search crop (e.g. Paddy, Wheat, Onion, Chickpea)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ marginBottom: '16px' }}
          />

          <div style={{ maxHeight: '420px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', paddingRight: '4px' }}>
            {filteredCrops.map((c) => {
              const isSelected = selectedCrop?.crop_id === c.crop_id;
              return (
                <div
                  key={c.crop_id}
                  onClick={() => handleSelectCrop(c)}
                  style={{
                    padding: '12px 16px',
                    borderRadius: '10px',
                    cursor: 'pointer',
                    background: isSelected ? 'rgba(16, 185, 129, 0.15)' : 'rgba(15, 23, 42, 0.6)',
                    border: isSelected ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.06)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: '700', color: isSelected ? '#34d399' : '#f8fafc', fontSize: '0.98rem' }}>
                      {c.crop_name}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '2px' }}>
                      {c.crop_category} • {c.crop_form}
                    </div>
                  </div>
                  {isSelected && <CheckCircle size={18} color="#10b981" />}
                </div>
              );
            })}
          </div>
        </div>

        {/* Step 2: Scientific Profile & Storage Form */}
        {selectedCrop && (
          <div className="glass-panel glow-border" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="badge badge-verified">
                  <ShieldCheck size={12} /> Verified Scientific Limits
                </span>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>v{selectedCrop.version}.0</span>
              </div>
              <h2 style={{ fontSize: '1.5rem', marginTop: '6px' }}>{selectedCrop.crop_name}</h2>
              <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '2px' }}>
                Source: {selectedCrop.source_name}
              </div>
            </div>

            {/* Target Limits Summary Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '12px' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Target Temp</span>
                <div style={{ fontWeight: '800', fontSize: '1.05rem', color: '#10b981' }}>
                  {selectedCrop.recommended_temperature_min_c} – {selectedCrop.recommended_temperature_max_c}°C
                </div>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Safe Humidity</span>
                <div style={{ fontWeight: '800', fontSize: '1.05rem', color: '#60a5fa' }}>
                  {selectedCrop.recommended_relative_humidity_min_percent} – {selectedCrop.recommended_relative_humidity_max_percent}%
                </div>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Max Moisture</span>
                <div style={{ fontWeight: '800', fontSize: '1.05rem', color: '#f59e0b' }}>
                  {selectedCrop.recommended_crop_moisture_percent}%
                </div>
              </div>
            </div>

            {/* Storage Guidance Box */}
            <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '12px 14px', borderRadius: '10px', fontSize: '0.84rem', color: '#cbd5e1', lineHeight: 1.5 }}>
              <strong>Ventilation Guidance:</strong> {selectedCrop.ventilation_guidance}
            </div>

            {/* Batch Form */}
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '6px' }}>
              <div>
                <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Custom Batch Label</label>
                <input
                  type="text"
                  required
                  className="input-field"
                  value={batchName}
                  onChange={(e) => setBatchName(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Quantity (kg)</label>
                  <input
                    type="number"
                    required
                    min="1"
                    className="input-field"
                    placeholder="e.g. 2500"
                    value={quantityKg}
                    onChange={(e) => setQuantityKg(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Storage Structure</label>
                  <select
                    className="input-field"
                    value={storageStructure}
                    onChange={(e) => setStorageStructure(e.target.value)}
                  >
                    <option value="Hermetic Pusa Bin">Hermetic Pusa Bin</option>
                    <option value="Covered Warehouse / Silo">Covered Warehouse / Silo</option>
                    <option value="Ventilated Bamboo Chawl">Ventilated Bamboo Chawl</option>
                    <option value="Cold Storage Room">Cold Storage Room</option>
                    <option value="Lined Gunny Bags on Dunnage">Lined Gunny Bags on Dunnage</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Harvest Date</label>
                  <input
                    type="date"
                    required
                    className="input-field"
                    value={harvestDate}
                    onChange={(e) => setHarvestDate(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Storage Location</label>
                  <input
                    type="text"
                    required
                    className="input-field"
                    value={storageLocation}
                    onChange={(e) => setStorageLocation(e.target.value)}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="btn-primary"
                style={{ marginTop: '10px', justifyContent: 'center', padding: '14px' }}
              >
                {submitting ? 'Creating Storage Batch...' : 'Create & Monitor Storage Batch'} <ArrowRight size={18} />
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
