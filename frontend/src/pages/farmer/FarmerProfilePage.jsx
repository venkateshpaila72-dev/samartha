import React, { useEffect, useMemo, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Mail, MapPin, MessageCircle, UserRound, Languages, Pencil, Save, X } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { apiRequest } from '../../services/apiClient';

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'te', label: 'Telugu' },
  { value: 'hi', label: 'Hindi' },
  { value: 'ta', label: 'Tamil' },
  { value: 'kn', label: 'Kannada' },
  { value: 'mr', label: 'Marathi' },
  { value: 'pa', label: 'Punjabi' },
  { value: 'bn', label: 'Bengali' },
];

const inputStyle = {
  width: '100%', boxSizing: 'border-box', padding: '11px 12px',
  borderRadius: '9px', border: '1px solid rgba(148,163,184,.3)',
  background: '#0f172a', color: '#e2e8f0', marginTop: '6px',
};

export default function FarmerProfilePage() {
  const { user } = useAuth();
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [form, setForm] = useState({
    full_name: '', phone_number: '', village_or_location: '', preferred_language: 'en',
  });

  useEffect(() => {
    setForm({
      full_name: user?.full_name || '',
      phone_number: user?.phone_number || '',
      village_or_location: user?.village_or_location || '',
      preferred_language: user?.preferred_language || 'en',
    });
  }, [user]);

  // Twilio WhatsApp Sandbox sender is the provider's number, never the farmer's number.
  // VITE_WHATSAPP_JOIN_KEYWORD must exactly match the phrase shown in Twilio Console.
  const whatsappUrl = useMemo(() => {
    const senderDigits = (import.meta.env.VITE_WHATSAPP_OPT_IN_NUMBER || '14155238886').replace(/\\D/g, '');
    const joinKeyword = (import.meta.env.VITE_WHATSAPP_JOIN_KEYWORD || '').trim();
    if (!senderDigits || !joinKeyword) return '';
    return `https://wa.me/${senderDigits}?text=${encodeURIComponent(joinKeyword)}`;
  }, []);

  const setField = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  const saveProfile = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const response = await apiRequest('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({
          full_name: form.full_name.trim(),
          phone_number: form.phone_number.trim() || null,
          village_or_location: form.village_or_location.trim() || null,
          preferred_language: form.preferred_language,
        }),
      });
      // apiRequest returns the parsed API response; AuthContext owns the user state.
      // Reloading /auth/me updates the displayed profile without exposing the JWT.
      const refreshed = await apiRequest('/auth/me');
      window.dispatchEvent(new CustomEvent('farmshield:profile-updated', { detail: refreshed.data }));
      setSuccess(response.message || 'Profile saved successfully.');
      setEditing(false);
      window.location.reload();
    } catch (err) {
      setError(err.message || 'Could not save profile. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const copyUrl = async () => {
    if (!whatsappUrl) return;
    try {
      await navigator.clipboard.writeText(whatsappUrl);
      setSuccess('WhatsApp opt-in link copied.');
    } catch {
      setError('Could not copy the link. Please copy it from the link below.');
    }
  };

  return (
    <section style={{ maxWidth: '980px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.7rem' }}>My Farmer Profile</h1>
          <p style={{ color: '#94a3b8', marginTop: '8px' }}>Edit your contact details, location and alert language.</p>
        </div>
        {!editing && <button type="button" className="btn-primary" onClick={() => { setError(''); setSuccess(''); setEditing(true); }}><Pencil size={16} /> Edit Profile</button>}
      </div>

      {error && <div role="alert" style={{ padding: '12px', marginBottom: '14px', borderRadius: '9px', color: '#fecaca', background: 'rgba(239,68,68,.12)' }}>{error}</div>}
      {success && <div role="status" style={{ padding: '12px', marginBottom: '14px', borderRadius: '9px', color: '#a7f3d0', background: 'rgba(16,185,129,.12)' }}>{success}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
        <div className="glass-panel" style={{ padding: '24px', borderRadius: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '22px' }}>
            <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'rgba(16,185,129,.15)', display: 'grid', placeItems: 'center' }}><UserRound size={24} color="#34d399" /></div>
            <div><h2 style={{ margin: 0, fontSize: '1.15rem' }}>{user?.full_name || 'Farmer'}</h2><span style={{ color: '#34d399', fontSize: '.8rem', textTransform: 'capitalize' }}>{user?.role || 'farmer'} account</span></div>
          </div>

          {editing ? (
            <form onSubmit={saveProfile} style={{ display: 'grid', gap: '14px' }}>
              <label>Full name<input required minLength={2} style={inputStyle} value={form.full_name} onChange={(e) => setField('full_name', e.target.value)} /></label>
              <label>WhatsApp phone number<input type="tel" style={inputStyle} placeholder="+91XXXXXXXXXX" value={form.phone_number} onChange={(e) => setField('phone_number', e.target.value)} /></label>
              <label>Village / location<input style={inputStyle} value={form.village_or_location} onChange={(e) => setField('village_or_location', e.target.value)} /></label>
              <label>Preferred language<select style={inputStyle} value={form.preferred_language} onChange={(e) => setField('preferred_language', e.target.value)}>{LANGUAGES.map((language) => <option key={language.value} value={language.value}>{language.label}</option>)}</select></label>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button type="submit" className="btn-primary" disabled={saving}><Save size={16} /> {saving ? 'Saving…' : 'Save Profile'}</button>
                <button type="button" className="btn-secondary" disabled={saving} onClick={() => { setEditing(false); setForm({ full_name: user?.full_name || '', phone_number: user?.phone_number || '', village_or_location: user?.village_or_location || '', preferred_language: user?.preferred_language || 'en' }); }}><X size={16} /> Cancel</button>
              </div>
            </form>
          ) : (
            <>
              <ProfileRow icon={<Mail size={17} />} label="Email (cannot be changed here)" value={user?.email || 'Not provided'} />
              <ProfileRow icon={<MessageCircle size={17} />} label="WhatsApp Number" value={user?.phone_number || 'Not provided'} />
              <ProfileRow icon={<MapPin size={17} />} label="Village / Location" value={user?.village_or_location || 'Not provided'} />
              <ProfileRow icon={<Languages size={17} />} label="Preferred Language" value={LANGUAGES.find((item) => item.value === user?.preferred_language)?.label || 'English'} />
            </>
          )}
        </div>

        <div className="glass-panel" style={{ padding: '24px', borderRadius: '16px', textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginBottom: '8px' }}><MessageCircle size={20} color="#34d399" /><h2 style={{ margin: 0, fontSize: '1.15rem' }}>WhatsApp Alert Opt-in</h2></div>
          <p style={{ color: '#94a3b8', fontSize: '.86rem', margin: '0 0 18px' }}>Scan this QR to open the configured Twilio WhatsApp sender. WhatsApp will prefill the sandbox join phrase; tap Send to opt in. Alerts can only start after the provider confirms opt-in.</p>
          {whatsappUrl ? (
            <>
              <div style={{ display: 'inline-block', background: '#fff', padding: '14px', borderRadius: '12px' }}><QRCodeSVG value={whatsappUrl} size={210} level="M" includeMargin /></div>
              <a href={whatsappUrl} target="_blank" rel="noreferrer" style={{ display: 'block', color: '#34d399', marginTop: '16px', overflowWrap: 'anywhere', fontSize: '.9rem' }}>{whatsappUrl}</a>
              <button type="button" className="btn-secondary" onClick={copyUrl} style={{ marginTop: '14px' }}>Copy opt-in link</button>
            </>
          ) : (
            <div style={{ padding: '24px 12px', border: '1px dashed rgba(148,163,184,.35)', borderRadius: '12px', color: '#94a3b8' }}>
              Add VITE_WHATSAPP_JOIN_KEYWORD to frontend/.env. Copy the exact “join …” phrase from Twilio Console → Messaging → Try it out → Send a WhatsApp message / Sandbox settings. Do not guess the phrase.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function ProfileRow({ icon, label, value }) {
  return <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', padding: '13px 0', borderBottom: '1px solid rgba(255,255,255,.07)' }}>
    <span style={{ color: '#34d399', marginTop: '2px' }}>{icon}</span>
    <div style={{ minWidth: 0 }}>
      <div style={{ color: '#94a3b8', fontSize: '.78rem', marginBottom: '4px' }}>{label}</div>
      <div style={{ color: '#e2e8f0', overflowWrap: 'anywhere' }}>{value}</div>
    </div>
  </div>;
}
