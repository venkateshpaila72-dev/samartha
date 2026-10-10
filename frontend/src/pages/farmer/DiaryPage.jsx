import React, { useState, useEffect } from 'react';
import { diaryService } from '../../services/monitoringService';
import {
  BookOpen,
  PlusCircle,
  Trash2,
  Mic,
  Camera,
  Calendar,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';

export default function DiaryPage({ activeBatch }) {
  const [entries, setEntries] = useState([]);
  const [text, setText] = useState('');
  const [category, setCategory] = useState('general_inspection');
  const [severity, setSeverity] = useState('normal');
  const [photoUrl, setPhotoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const loadDiary = async () => {
    if (!activeBatch) return;
    setLoading(true);
    try {
      const data = await diaryService.getBatchEntries(activeBatch.batch_id);
      setEntries(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDiary();
  }, [activeBatch]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!activeBatch || !text.trim()) return;
    setSubmitting(true);
    try {
      await diaryService.createEntry(activeBatch.batch_id, {
        batch_id: activeBatch.batch_id,
        observation_text: text,
        observation_category: category,
        severity_assessment: severity,
        photo_urls: photoUrl ? [photoUrl] : [],
        provenance: 'farmer_visual_report',
      });
      setText('');
      setPhotoUrl('');
      await loadDiary();
      alert('Diary observation logged successfully!');
    } catch (err) {
      alert(err.message || 'Error recording diary entry');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (entryId) => {
    if (!confirm('Are you sure you want to remove this observation?')) return;
    try {
      await diaryService.deleteEntry(entryId);
      await loadDiary();
    } catch (err) {
      alert(err.message || 'Error deleting entry');
    }
  };

  const handleSimulateVoice = () => {
    setText('Voice Memo: Inspected bottom sacks in center stack. Grain feels dry, no musty odor detected, but saw 2 small beetles near the north wall corner.');
    setCategory('insect_activity');
    setSeverity('minor_concern');
  };

  if (!activeBatch) {
    return <div className="glass-panel" style={{ padding: '40px', textAlign: 'center' }}>Please select a batch from the top navigation.</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <span className="badge badge-verified">Workflow 6: Farmer Diary & Observation Log</span>
        <h1 style={{ fontSize: '1.8rem', marginTop: '4px' }}>Crop Storage Diary</h1>
        <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
          Record manual inspections, unusual odors, insect sightings, moisture changes, and voice notes for <strong>{activeBatch.custom_batch_name}</strong>.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px' }}>
        {/* New Entry Form */}
        <div className="glass-panel glow-border" style={{ padding: '24px', height: 'fit-content' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <PlusCircle size={20} color="#10b981" /> Record Observation
            </h3>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleSimulateVoice}
              style={{ fontSize: '0.78rem', padding: '4px 10px' }}
              title="Transcribe Voice Note"
            >
              <Mic size={14} color="#f59e0b" /> Voice Note Simulation
            </button>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Observation Category</label>
              <select
                className="input-field"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="general_inspection">General Visual Inspection</option>
                <option value="smell">Unusual Smell / Odor (Musty, Sour)</option>
                <option value="insect_activity">Insect / Pest Activity Sighted</option>
                <option value="moisture_leakage">Dampness or Water Condensation</option>
                <option value="temperature_hotspot">Grain Heating / Localized Hotspot</option>
                <option value="color_change">Discoloration or Mold Growth</option>
                <option value="caking">Grain Clumping / Caking</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Severity Assessment</label>
              <select
                className="input-field"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
              >
                <option value="normal">Normal (Routine inspection, no issues)</option>
                <option value="minor_concern">Minor Concern (Monitor closely)</option>
                <option value="urgent_attention">Urgent Attention (Action needed)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Detailed Inspection Notes</label>
              <textarea
                required
                rows={4}
                className="input-field"
                placeholder="Describe what you saw, smelled, or felt inside the storage structure..."
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Inspection Photo URL (Optional)</label>
              <input
                type="text"
                className="input-field"
                placeholder="https://example.com/storage-inspection.jpg"
                value={photoUrl}
                onChange={(e) => setPhotoUrl(e.target.value)}
              />
            </div>

            <button type="submit" disabled={submitting} className="btn-primary" style={{ justifyContent: 'center' }}>
              {submitting ? 'Saving Observation...' : 'Save to Diary'}
            </button>
          </form>
        </div>

        {/* Diary Timeline */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1.2rem', marginBottom: '16px' }}>Observation Timeline ({entries.length})</h3>

          {entries.length === 0 ? (
            <div style={{ color: '#64748b', textAlign: 'center', padding: '40px' }}>
              No diary observations logged for this batch yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', maxHeight: '550px', overflowY: 'auto' }}>
              {entries.map((entry) => {
                const isUrgent = entry.severity_assessment === 'urgent_attention';
                const isMinor = entry.severity_assessment === 'minor_concern';
                return (
                  <div
                    key={entry.entry_id}
                    style={{
                      background: 'rgba(15, 23, 42, 0.7)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '12px',
                      padding: '16px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className={`badge ${isUrgent ? 'badge-critical' : (isMinor ? 'badge-warning' : 'badge-verified')}`}>
                          {entry.observation_category?.replace('_', ' ').toUpperCase()}
                        </span>
                        <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                          {new Date(entry.created_at).toLocaleString()}
                        </span>
                      </div>
                      <button
                        onClick={() => handleDelete(entry.entry_id)}
                        style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
                        title="Delete note"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>

                    <p style={{ color: '#f8fafc', fontSize: '0.92rem', lineHeight: 1.5, margin: '4px 0' }}>
                      {entry.observation_text}
                    </p>

                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                      Provenance: {entry.provenance}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
