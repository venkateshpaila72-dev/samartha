import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { marketService } from '../../services/marketService';
import TranslatedText from '../../components/TranslatedText';
import { UserRound, Save, RefreshCw, TrendingUp, CheckCircle2, AlertCircle, MapPin } from 'lucide-react';

const fieldStyle = {
  width: '100%', minWidth: 0, boxSizing: 'border-box', padding: '11px 12px',
  borderRadius: '9px', border: '1px solid rgba(148,163,184,.28)',
  background: 'rgba(15,23,42,.75)', color: '#f8fafc', fontSize: '.95rem',
};
const labelStyle = { display: 'flex', flexDirection: 'column', gap: '7px', color: '#cbd5e1', fontSize: '.9rem' };
const panelStyle = { padding: 'clamp(16px, 3vw, 26px)', minWidth: 0 };

export default function FarmerProfilePage({ onNavigate }) {
  const { user, updateProfile } = useAuth();
  const [form, setForm] = useState({
    full_name: user?.full_name || '',
    phone_number: user?.phone_number || '',
    village_or_location: user?.village_or_location || '',
    selected_crop: user?.selected_crop || '',
    state: user?.state || '',
    district: user?.district || '',
  });
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [notice, setNotice] = useState(null);
  const [syncResult, setSyncResult] = useState(null);

  useEffect(() => {
    setForm({
      full_name: user?.full_name || '',
      phone_number: user?.phone_number || '',
      village_or_location: user?.village_or_location || '',
      selected_crop: user?.selected_crop || '',
      state: user?.state || '',
      district: user?.district || '',
    });
  }, [user]);

  const setField = (key, value) => setForm((previous) => ({ ...previous, [key]: value }));

  const saveProfile = async (event) => {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    try {
      const payload = {
        full_name: form.full_name.trim(),
        phone_number: form.phone_number.trim() || null,
        village_or_location: form.village_or_location.trim() || null,
        selected_crop: form.selected_crop.trim() || null,
        state: form.state.trim() || null,
        district: form.district.trim() || null,
      };
      const updated = await updateProfile(payload);
      try {
        if (updated.selected_crop) localStorage.setItem('farmshield_selected_crop', updated.selected_crop);
        if (updated.state) localStorage.setItem('farmshield_state', updated.state);
        if (updated.district) localStorage.setItem('farmshield_district', updated.district);
      } catch { /* Server profile is authoritative if browser storage is disabled. */ }
      setNotice({ type: 'success', text: 'Your profile and market preferences have been saved.' });
    } catch (error) {
      setNotice({ type: 'error', text: error?.message || 'Unable to save your profile. Please try again.' });
    } finally {
      setSaving(false);
    }
  };

  const syncMarket = async () => {
    if (!form.selected_crop.trim()) {
      setNotice({ type: 'error', text: 'Choose and save your crop before syncing market prices.' });
      return;
    }
    if (!form.state.trim()) {
      setNotice({ type: 'error', text: 'Enter and save your state to sync the relevant mandi records.' });
      return;
    }
    setSyncing(true);
    setNotice(null);
    setSyncResult(null);
    try {
      // Save first so the selected crop/location are the profile's source of truth.
      await updateProfile({
        full_name: form.full_name.trim(),
        phone_number: form.phone_number.trim() || null,
        village_or_location: form.village_or_location.trim() || null,
        selected_crop: form.selected_crop.trim(),
        state: form.state.trim(),
        district: form.district.trim() || null,
      });
      const result = await marketService.syncMarketPrices({
        crop: form.selected_crop.trim(),
        state: form.state.trim(),
        district: form.district.trim(),
      });
      setSyncResult(result);
      setNotice({
        type: 'success',
        text: 'Market sync completed. Open Market Prices to review the imported records and history.',
      });
    } catch (error) {
      setNotice({ type: 'error', text: error?.message || 'Market sync failed. Check server configuration and try again later.' });
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', minWidth: 0 }}>
      <section className="glass-panel glow-border" style={panelStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <UserRound size={26} color="#34d399" />
          <div>
            <h1 style={{ fontSize: 'clamp(1.45rem, 3vw, 1.9rem)', margin: 0 }}><TranslatedText text="Farmer Profile" /></h1>
            <p style={{ color: '#94a3b8', fontSize: '.9rem', marginTop: '4px' }}><TranslatedText text="Manage your account and saved crop-market preferences." /></p>
          </div>
        </div>
        <form onSubmit={saveProfile} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: '16px', marginTop: '22px' }}>
          <label style={labelStyle}>
            <TranslatedText text="Full name" />
            <input style={fieldStyle} value={form.full_name} onChange={(e) => setField('full_name', e.target.value)} minLength={2} required autoComplete="name" />
          </label>
          <label style={labelStyle}>
            <TranslatedText text="Email address" />
            <input style={{ ...fieldStyle, opacity: .75 }} value={user?.email || ''} readOnly aria-readonly="true" />
          </label>
          <label style={labelStyle}>
            <TranslatedText text="Phone number" />
            <input style={fieldStyle} value={form.phone_number} onChange={(e) => setField('phone_number', e.target.value)} type="tel" autoComplete="tel" />
          </label>
          <label style={labelStyle}>
            <TranslatedText text="Village / Location" />
            <input style={fieldStyle} value={form.village_or_location} onChange={(e) => setField('village_or_location', e.target.value)} autoComplete="address-level4" />
          </label>
          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end' }}>
            <button className="btn-primary" type="submit" disabled={saving || syncing} style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <Save size={16} /> {saving ? <TranslatedText text="Saving…" /> : <TranslatedText text="Save Profile" />}
            </button>
          </div>
        </form>
      </section>

      <section className="glass-panel" style={panelStyle}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '12px' }}>
          <TrendingUp size={26} color="#34d399" style={{ flexShrink: 0, marginTop: '3px' }} />
          <div>
            <h2 style={{ fontSize: '1.3rem', margin: 0 }}><TranslatedText text="Market Prices & Sync" /></h2>
            <p style={{ color: '#94a3b8', fontSize: '.9rem', marginTop: '6px', lineHeight: 1.55 }}>
              <TranslatedText text="Choose the crop you grow and your mandi location. Sync imports real provider records for this selection; it never invents missing daily prices." />
            </p>
          </div>
        </div>

        <form onSubmit={saveProfile} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: '16px', marginTop: '18px' }}>
          <label style={labelStyle}>
            <TranslatedText text="My selected crop" />
            <input style={fieldStyle} value={form.selected_crop} onChange={(e) => setField('selected_crop', e.target.value)} placeholder="e.g. Paddy, Chilli, Cotton" maxLength={100} required />
          </label>
          <label style={labelStyle}>
            <TranslatedText text="State" />
            <input style={fieldStyle} value={form.state} onChange={(e) => setField('state', e.target.value)} placeholder="e.g. Andhra Pradesh" maxLength={100} required />
          </label>
          <label style={labelStyle}>
            <TranslatedText text="District (optional)" />
            <input style={fieldStyle} value={form.district} onChange={(e) => setField('district', e.target.value)} placeholder="e.g. Guntur" maxLength={100} />
          </label>
          <div style={{ gridColumn: '1 / -1', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button className="btn-secondary" type="submit" disabled={saving || syncing} style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <Save size={16} /> <TranslatedText text="Save Market Preferences" />
            </button>
            <button className="btn-primary" type="button" onClick={syncMarket} disabled={saving || syncing || !form.selected_crop.trim() || !form.state.trim()} style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
              {syncing ? <TranslatedText text="Syncing market records…" /> : <TranslatedText text="Sync Market Prices Now" />}
            </button>
            <button className="btn-secondary" type="button" onClick={() => onNavigate('market')} style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <TrendingUp size={16} /> <TranslatedText text="View Market Prices" />
            </button>
          </div>
        </form>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginTop: '18px', padding: '12px', borderRadius: '10px', background: 'rgba(148,163,184,.08)', color: '#94a3b8', fontSize: '.84rem', lineHeight: 1.5 }}>
          <MapPin size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
          <span><TranslatedText text="Sync is limited to one request every 15 minutes per account. Availability depends on the data provider; only valid returned observations are stored." /></span>
        </div>

        {syncResult && (
          <div style={{ marginTop: '14px', padding: '14px', borderRadius: '10px', background: 'rgba(16,185,129,.1)', border: '1px solid rgba(16,185,129,.25)', overflowWrap: 'anywhere' }}>
            <strong style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle2 size={17} /> <TranslatedText text="Sync result" /></strong>
            <p style={{ color: '#cbd5e1', marginTop: '8px', fontSize: '.9rem' }}>
              <TranslatedText text="Records fetched" />: {syncResult.records_fetched ?? 0} · <TranslatedText text="Inserted or updated" />: {syncResult.records_inserted_or_updated ?? 0} · <TranslatedText text="Rejected" />: {syncResult.records_rejected ?? 0}
            </p>
            <p style={{ color: '#94a3b8', marginTop: '5px', fontSize: '.82rem' }}>{syncResult.provider || 'Market data provider'} · {syncResult.completed_at || ''}</p>
          </div>
        )}
      </section>

      {notice && (
        <div role="status" aria-live="polite" className="glass-panel" style={{ ...panelStyle, display: 'flex', gap: '10px', alignItems: 'flex-start', border: notice.type === 'error' ? '1px solid rgba(248,113,113,.35)' : '1px solid rgba(52,211,153,.25)' }}>
          {notice.type === 'error' ? <AlertCircle size={19} color="#f87171" style={{ flexShrink: 0 }} /> : <CheckCircle2 size={19} color="#34d399" style={{ flexShrink: 0 }} />}
          <span style={{ color: notice.type === 'error' ? '#fca5a5' : '#a7f3d0', lineHeight: 1.5 }}>{notice.text}</span>
        </div>
      )}
    </div>
  );
}
