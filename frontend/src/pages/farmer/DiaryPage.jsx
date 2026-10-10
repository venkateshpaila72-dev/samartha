import React, { useState, useEffect, useRef } from 'react';
import { diaryService } from '../../services/monitoringService';
import { uploadImage } from '../../services/uploadService';
import { speechService } from '../../services/speechService';
import { useAuth } from '../../context/AuthContext';
import {
  BookOpen,
  PlusCircle,
  Trash2,
  Mic,
  MicOff,
  Camera,
  Calendar,
  AlertCircle,
  CheckCircle,
  UploadCloud,
  Volume2,
  VolumeX,
  Loader2,
  Square,
  Sparkles,
} from 'lucide-react';

export default function DiaryPage({ activeBatch }) {
  const { user } = useAuth();
  const [entries, setEntries] = useState([]);
  const [text, setText] = useState('');
  const [category, setCategory] = useState('general_inspection');
  const [severity, setSeverity] = useState('normal');
  const [photoUrl, setPhotoUrl] = useState('');
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Voice Recording (STT) & Audio Playback (TTS)
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [activePlayingId, setActivePlayingId] = useState(null);

  const timerRef = useRef(null);

  const loadDiary = async () => {
    if (!activeBatch) return;
    setLoading(true);
    try {
      const data = await diaryService.getBatchEntries(activeBatch.batch_id);
      setEntries(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDiary();
  }, [activeBatch]);

  useEffect(() => {
    return () => {
      speechService.stopAudio();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Real Azure Speech-to-Text recording
  const handleStartVoice = async () => {
    try {
      speechService.stopAudio();
      setActivePlayingId(null);
      await speechService.startRecording();
      setIsRecording(true);
      setRecordingSeconds(0);
      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      alert(`Could not access microphone: ${err.message}`);
    }
  };

  const handleStopVoice = async () => {
    if (!isRecording) return;
    if (timerRef.current) clearInterval(timerRef.current);
    setIsRecording(false);
    setIsTranscribing(true);

    try {
      const audioBlob = await speechService.stopRecording();
      const res = await speechService.transcribeAudio(
        audioBlob,
        user?.preferred_language || 'en'
      );
      if (res?.transcript) {
        setVoiceTranscript(res.transcript);
        setText((prev) => {
          const newText = prev ? `${prev} ${res.transcript}` : res.transcript;
          return newText;
        });

        // Smart category heuristic
        const lower = res.transcript.toLowerCase();
        if (lower.includes('beetle') || lower.includes('insect') || lower.includes('pest') || lower.includes('weevil')) {
          setCategory('insect_activity');
          setSeverity('minor_concern');
        } else if (lower.includes('smell') || lower.includes('odor') || lower.includes('musty') || lower.includes('sour')) {
          setCategory('smell');
        } else if (lower.includes('water') || lower.includes('damp') || lower.includes('moisture') || lower.includes('leak')) {
          setCategory('moisture_leakage');
        } else if (lower.includes('hot') || lower.includes('heat') || lower.includes('warm')) {
          setCategory('temperature_hotspot');
        }
      }
    } catch (err) {
      alert(`Voice transcription error: ${err.message}`);
    } finally {
      setIsTranscribing(false);
      setRecordingSeconds(0);
    }
  };

  // Real Azure Text-to-Speech playback
  const handlePlayTTS = async (entryId, textToSpeak) => {
    if (activePlayingId === entryId) {
      speechService.stopAudio();
      setActivePlayingId(null);
      return;
    }

    setActivePlayingId(entryId);
    try {
      await speechService.speakText(
        textToSpeak,
        user?.preferred_language || 'en',
        () => setActivePlayingId(entryId),
        () => setActivePlayingId(null)
      );
    } catch (err) {
      console.error('Audio playback failed:', err);
      setActivePlayingId(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!activeBatch || !text.trim()) return;
    setSubmitting(true);
    try {
      await diaryService.createEntry(activeBatch.batch_id, {
        batch_id: activeBatch.batch_id,
        observation_text: text.trim(),
        observation_category: category,
        severity_assessment: severity,
        photo_urls: photoUrl ? [photoUrl] : [],
        voice_transcript: voiceTranscript || null,
        provenance: voiceTranscript ? 'voice_transcription' : 'farmer_visual_report',
      });
      setText('');
      setPhotoUrl('');
      setVoiceTranscript('');
      setUploadSuccess(false);
      await loadDiary();
      alert('Diary observation logged and stored successfully!');
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

  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingPhoto(true);
    setUploadSuccess(false);
    try {
      const data = await uploadImage(file, 'farmshield/diary');
      const url = data.secure_url || data.url;
      setPhotoUrl(url);
      setUploadSuccess(true);
    } catch (err) {
      alert(`Photo upload failed: ${err.message || 'Check network / Cloudinary configuration'}`);
    } finally {
      setUploadingPhoto(false);
    }
  };

  if (!activeBatch) {
    return (
      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center' }}>
        Please select a batch from the top navigation.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <span className="badge badge-verified">
          <Sparkles size={13} /> Workflow 6: Farmer Diary & Voice Observation Log
        </span>
        <h1 style={{ fontSize: '1.8rem', marginTop: '4px' }}>Crop Storage Diary</h1>
        <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
          Record manual inspections by <strong>typing text</strong> or <strong>speaking in voice</strong> (powered by Microsoft Azure Speech) for{' '}
          <strong>{activeBatch.custom_batch_name}</strong>. All observations are permanently stored.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px' }}>
        {/* New Entry Form */}
        <div className="glass-panel glow-border" style={{ padding: '24px', height: 'fit-content' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <PlusCircle size={20} color="#10b981" /> Record Observation
            </h3>

            {/* Azure STT Voice Observation Button */}
            {!isRecording ? (
              <button
                type="button"
                className="btn-secondary"
                onClick={handleStartVoice}
                disabled={isTranscribing}
                style={{
                  fontSize: '0.8rem',
                  padding: '6px 12px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  border: '1px solid #10b981',
                  color: '#34d399',
                  cursor: 'pointer',
                }}
                title="Speak observation using Azure Speech"
              >
                <Mic size={15} color="#10b981" /> Tell in Voice (Azure Speech)
              </button>
            ) : (
              <button
                type="button"
                className="btn-secondary"
                onClick={handleStopVoice}
                style={{
                  fontSize: '0.8rem',
                  padding: '6px 12px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: '#ef4444',
                  color: '#fff',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <Square size={13} /> Done Speaking ({recordingSeconds}s)
              </button>
            )}
          </div>

          {/* Voice Recording / Transcribing Indicator */}
          {isRecording && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 14px',
                marginBottom: '14px',
                borderRadius: '8px',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#f87171',
                fontSize: '0.86rem',
              }}
            >
              <span
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: '#ef4444',
                  display: 'inline-block',
                }}
              />
              <strong>Listening to observation... ({recordingSeconds}s)</strong> Speak clearly in {user?.preferred_language?.toUpperCase() || 'EN'}.
            </div>
          )}

          {isTranscribing && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 12px',
                marginBottom: '14px',
                color: '#34d399',
                fontSize: '0.84rem',
              }}
            >
              <Loader2 size={16} className="spin-animation" />
              Transcribing audio with Azure Cognitive Speech Services...
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
                Observation Category
              </label>
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
              <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>
                Severity Assessment
              </label>
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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                  Detailed Inspection Notes (Text or Voice)
                </label>
                {voiceTranscript && (
                  <span style={{ fontSize: '0.74rem', color: '#34d399', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <CheckCircle size={12} /> Voice Transcribed
                  </span>
                )}
              </div>
              <textarea
                required
                rows={4}
                className="input-field"
                placeholder="Type your notes or click 'Tell in Voice' above to speak your observation..."
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>
                Storage Inspection Photo (Cloudinary Upload)
              </label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <label
                    htmlFor="diary-photo-input"
                    className="btn-secondary"
                    style={{
                      cursor: uploadingPhoto ? 'not-allowed' : 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      fontSize: '0.85rem',
                      padding: '8px 14px',
                    }}
                  >
                    <Camera size={16} color="#38bdf8" />
                    {uploadingPhoto ? 'Uploading to Cloudinary...' : 'Upload Photo'}
                  </label>
                  <input
                    id="diary-photo-input"
                    type="file"
                    accept="image/*"
                    onChange={handlePhotoUpload}
                    disabled={uploadingPhoto}
                    style={{ display: 'none' }}
                  />
                  {uploadSuccess && (
                    <span style={{ fontSize: '0.8rem', color: '#4ade80', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <CheckCircle size={14} /> Uploaded to Cloudinary
                    </span>
                  )}
                </div>

                <input
                  type="text"
                  className="input-field"
                  placeholder="Or paste image URL (https://...)"
                  value={photoUrl}
                  onChange={(e) => {
                    setPhotoUrl(e.target.value);
                    setUploadSuccess(false);
                  }}
                  style={{ fontSize: '0.85rem' }}
                />

                {photoUrl && (
                  <div style={{ position: 'relative', width: 'fit-content', marginTop: '4px' }}>
                    <img
                      src={photoUrl}
                      alt="Inspection preview"
                      style={{
                        width: '90px',
                        height: '90px',
                        objectFit: 'cover',
                        borderRadius: '8px',
                        border: '1px solid rgba(56, 189, 248, 0.4)',
                      }}
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => {
                        setPhotoUrl('');
                        setUploadSuccess(false);
                      }}
                      style={{
                        position: 'absolute',
                        top: '-6px',
                        right: '-6px',
                        background: '#ef4444',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '50%',
                        width: '20px',
                        height: '20px',
                        cursor: 'pointer',
                        fontSize: '12px',
                        lineHeight: '1',
                      }}
                    >
                      ×
                    </button>
                  </div>
                )}
              </div>
            </div>

            <button type="submit" disabled={submitting || isRecording} className="btn-primary" style={{ justifyContent: 'center' }}>
              {submitting ? 'Saving Observation to Storage...' : 'Save Observation to Diary'}
            </button>
          </form>
        </div>

        {/* Diary Timeline with Audio Read-Aloud */}
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
                const isPlayingThis = activePlayingId === entry.entry_id;

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
                      gap: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span className={`badge ${isUrgent ? 'badge-critical' : isMinor ? 'badge-warning' : 'badge-verified'}`}>
                          {entry.observation_category?.replace('_', ' ').toUpperCase()}
                        </span>
                        {entry.provenance === 'voice_transcription' && (
                          <span
                            style={{
                              fontSize: '0.72rem',
                              color: '#34d399',
                              background: 'rgba(16, 185, 129, 0.12)',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              border: '1px solid rgba(16, 185, 129, 0.3)',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            <Mic size={11} /> Voice Note
                          </span>
                        )}
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

                    {/* Azure TTS Listen Button on each Observation Card */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '4px' }}>
                      <button
                        type="button"
                        onClick={() => handlePlayTTS(entry.entry_id, entry.observation_text)}
                        className="btn-secondary"
                        style={{
                          padding: '4px 10px',
                          fontSize: '0.78rem',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          border: isPlayingThis ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.1)',
                          background: isPlayingThis ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
                          color: isPlayingThis ? '#34d399' : '#94a3b8',
                          cursor: 'pointer',
                        }}
                      >
                        {isPlayingThis ? (
                          <>
                            <VolumeX size={14} color="#34d399" /> Stop Audio
                          </>
                        ) : (
                          <>
                            <Volume2 size={14} /> Listen (Azure Speech)
                          </>
                        )}
                      </button>

                      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        Provenance: {entry.provenance}
                      </div>
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
