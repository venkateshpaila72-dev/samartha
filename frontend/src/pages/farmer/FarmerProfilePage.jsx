import React, { useMemo, useState, useEffect } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import {
  Mail,
  MapPin,
  MessageCircle,
  UserRound,
  Languages,
  RefreshCw,
  TrendingUp,
  Sprout,
  Navigation,
  Save,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  ExternalLink,
  Calendar,
  Database,
  Building2,
  Loader2,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { apiRequest } from '../../services/apiClient';
import { marketService } from '../../services/marketService';

const INDIAN_STATES = [
  'Andhra Pradesh',
  'Arunachal Pradesh',
  'Assam',
  'Bihar',
  'Chhattisgarh',
  'Goa',
  'Gujarat',
  'Haryana',
  'Himachal Pradesh',
  'Jharkhand',
  'Karnataka',
  'Kerala',
  'Madhya Pradesh',
  'Maharashtra',
  'Manipur',
  'Meghalaya',
  'Mizoram',
  'Nagaland',
  'Odisha',
  'Punjab',
  'Rajasthan',
  'Sikkim',
  'Tamil Nadu',
  'Telangana',
  'Tripura',
  'Uttar Pradesh',
  'Uttarakhand',
  'West Bengal',
  'Andaman and Nicobar Islands',
  'Chandigarh',
  'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi',
  'Jammu and Kashmir',
  'Ladakh',
  'Lakshadweep',
  'Puducherry',
];

const COMMON_CROPS = [
  'Tomato',
  'Onion',
  'Potato',
  'Paddy (Rice)',
  'Wheat',
  'Maize (Corn)',
  'Cotton',
  'Soybean',
  'Chilli',
  'Turmeric',
  'Sugarcane',
  'Groundnut',
  'Gram (Chickpea)',
  'Banana',
  'Mango',
  'Mustard',
  'Garlic',
  'Ginger',
];

export default function FarmerProfilePage({ onNavigate }) {
  const { user, updateUser, refreshUser } = useAuth();

  const [profileState, setProfileState] = useState(user?.state || '');
  const [district, setDistrict] = useState(user?.district || '');
  const [selectedCrop, setSelectedCrop] = useState(user?.selected_crop || 'Tomato');

  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(null);
  const [saveError, setSaveError] = useState(null);

  const [isSyncing, setIsSyncing] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState(null);
  const [syncError, setSyncError] = useState(null);

  const [isDetecting, setIsDetecting] = useState(false);
  const [detectSuccess, setDetectSuccess] = useState(null);
  const [detectError, setDetectError] = useState(null);

  useEffect(() => {
    if (user) {
      if (user.state && !profileState) setProfileState(user.state);
      if (user.district && !district) setDistrict(user.district);
      if (user.selected_crop && !selectedCrop) setSelectedCrop(user.selected_crop);
    }
  }, [user]);

  const whatsappUrl = useMemo(() => {
    const savedUrl = user?.whatsapp_url?.trim();
    if (savedUrl) return savedUrl;
    const digits = (user?.phone_number || '').replace(/\D/g, '');
    return digits ? `https://wa.me/${digits}` : '';
  }, [user]);

  const copyUrl = async () => {
    if (!whatsappUrl) return;
    try {
      await navigator.clipboard.writeText(whatsappUrl);
      window.alert('WhatsApp URL copied.');
    } catch (error) {
      console.error('Could not copy WhatsApp URL:', error);
      window.alert('Could not copy the URL. Please copy it manually.');
    }
  };

  const handleDetectLocation = () => {
    setDetectSuccess(null);
    setDetectError(null);
    if (!navigator.geolocation) {
      setDetectError('Geolocation is not supported by your browser.');
      return;
    }
    setIsDetecting(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          const res = await apiRequest(`/auth/reverse-geocode?latitude=${lat}&longitude=${lon}`);
          if (res?.data) {
            const detectedState = res.data.state || '';
            const detectedDistrict = res.data.district || '';
            if (detectedState) setProfileState(detectedState);
            if (detectedDistrict) setDistrict(detectedDistrict);
            setDetectSuccess(
              `Detected: ${detectedDistrict ? detectedDistrict + ', ' : ''}${detectedState}. Save preferences to apply.`
            );
          }
        } catch (err) {
          setDetectError(err.message || 'Reverse-geocoding failed.');
        } finally {
          setIsDetecting(false);
        }
      },
      (err) => {
        setIsDetecting(false);
        let msg = 'Failed to detect location.';
        if (err.code === 1) msg = 'Location access permission was denied. Please select your state manually.';
        else if (err.code === 2) msg = 'Location is currently unavailable.';
        else if (err.code === 3) msg = 'Location request timed out.';
        setDetectError(msg);
      },
      { timeout: 10000, enableHighAccuracy: false }
    );
  };

  const handleSavePreferences = async (e) => {
    if (e) e.preventDefault();
    setIsSaving(true);
    setSaveSuccess(null);
    setSaveError(null);
    try {
      const res = await apiRequest('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({
          state: profileState.trim() || null,
          district: district.trim() || null,
          selected_crop: selectedCrop.trim() || null,
        }),
      });
      if (res?.data) {
        if (updateUser) updateUser(res.data);
        setProfileState(res.data.state || '');
        setDistrict(res.data.district || '');
        setSelectedCrop(res.data.selected_crop || '');
        setSaveSuccess('Market preferences saved successfully.');
      }
    } catch (err) {
      setSaveError(err.message || 'Failed to save market preferences.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSyncMarketPrices = async () => {
    setIsSyncing(true);
    setSyncFeedback(null);
    setSyncError(null);

    const targetState = user?.state || profileState;
    if (!targetState) {
      setSyncError('Farmer state is not configured. Please select and save your state before syncing market prices.');
      setIsSyncing(false);
      return;
    }

    if (profileState && profileState !== user?.state) {
      try {
        const patchRes = await apiRequest('/auth/me', {
          method: 'PATCH',
          body: JSON.stringify({
            state: profileState,
            district,
            selected_crop: selectedCrop,
          }),
        });
        if (patchRes?.data && updateUser) updateUser(patchRes.data);
      } catch (err) {
        setSyncError('Could not save updated state before sync.');
        setIsSyncing(false);
        return;
      }
    }

    try {
      const res = await marketService.syncMarketPrices(selectedCrop, {
        state: targetState,
        district: district || user?.district,
      });
      setSyncFeedback(res?.sync_result || res);
      if (refreshUser) await refreshUser();
    } catch (err) {
      setSyncError(err.message || 'Failed to synchronize market prices. Please verify provider and try again.');
    } finally {
      setIsSyncing(false);
    }
  };

  const lastSyncAt = user?.last_market_sync_at;
  const syncSummary = syncFeedback || user?.last_market_sync_summary;

  return (
    <section style={{ maxWidth: '1020px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h1 style={{ margin: 0, fontSize: '1.75rem', letterSpacing: '-0.02em' }}>
          My Farmer Profile
        </h1>
        <p style={{ color: '#94a3b8', marginTop: '6px', fontSize: '0.92rem' }}>
          Manage your location, state-specific mandi market preferences, and contact details.
        </p>
      </div>

      {/* TOP GRID: Farmer Information & WhatsApp Contact */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '20px',
        }}
      >
        {/* Account Details Panel */}
        <div className="glass-panel" style={{ padding: '24px', borderRadius: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '14px',
                background: 'rgba(16,185,129,.15)',
                display: 'grid',
                placeItems: 'center',
              }}
            >
              <UserRound size={24} color="#34d399" />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.18rem' }}>{user?.full_name || 'Farmer'}</h2>
              <span style={{ color: '#34d399', fontSize: '.8rem', textTransform: 'capitalize' }}>
                {user?.role || 'farmer'} account
              </span>
            </div>
          </div>

          <ProfileRow icon={<Mail size={17} />} label="Email" value={user?.email || 'Not provided'} />
          <ProfileRow icon={<MessageCircle size={17} />} label="Phone / WhatsApp" value={user?.phone_number || 'Not provided'} />
          <ProfileRow icon={<MapPin size={17} />} label="Configured State" value={user?.state ? `${user.state}${user.district ? ` (${user.district})` : ''}` : 'Not configured'} />
          <ProfileRow icon={<Languages size={17} />} label="Preferred Language" value={user?.preferred_language || 'English'} />
        </div>

        {/* WhatsApp QR Panel */}
        <div className="glass-panel" style={{ padding: '24px', borderRadius: '16px', textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginBottom: '8px' }}>
            <MessageCircle size={20} color="#34d399" />
            <h2 style={{ margin: 0, fontSize: '1.15rem' }}>WhatsApp Contact</h2>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '.85rem', margin: '0 0 16px' }}>
            Scan this QR code with any phone camera to initiate communication.
          </p>

          {whatsappUrl ? (
            <>
              <div style={{ display: 'inline-block', background: '#fff', padding: '12px', borderRadius: '12px' }}>
                <QRCodeSVG value={whatsappUrl} size={175} level="M" includeMargin />
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '10px', marginTop: '16px' }}>
                <button type="button" className="btn-secondary" onClick={copyUrl} style={{ padding: '8px 14px', fontSize: '.85rem' }}>
                  Copy Link
                </button>
                <a
                  href={whatsappUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-primary"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', textDecoration: 'none', padding: '8px 14px', fontSize: '.85rem' }}
                >
                  Open WhatsApp
                </a>
              </div>
            </>
          ) : (
            <div style={{ padding: '24px 12px', border: '1px dashed rgba(148,163,184,.3)', borderRadius: '12px', color: '#94a3b8' }}>
              No WhatsApp URL is saved for this account.
            </div>
          )}
        </div>
      </div>

      {/* DEDICATED SECTION: Market Prices & Synchronization */}
      <div
        className="glass-panel glow-border"
        style={{
          padding: '28px',
          borderRadius: '16px',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          background: 'linear-gradient(180deg, rgba(16, 185, 129, 0.04) 0%, rgba(15, 23, 42, 0.6) 100%)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
            marginBottom: '20px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            paddingBottom: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                background: 'rgba(16, 185, 129, 0.2)',
                display: 'grid',
                placeItems: 'center',
              }}
            >
              <TrendingUp size={22} color="#10b981" />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc' }}>
                Market Prices & Synchronization
              </h2>
              <p style={{ margin: '3px 0 0', color: '#94a3b8', fontSize: '0.84rem' }}>
                Strict state-isolated mandi price integration for authenticated farmers
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => (onNavigate ? onNavigate('market') : null)}
            className="btn-secondary"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '9px 15px',
              fontSize: '0.86rem',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: '#34d399',
              cursor: 'pointer',
            }}
          >
            Open Market Prices Page <ExternalLink size={14} />
          </button>
        </div>

        {/* Preferences Form */}
        <form onSubmit={handleSavePreferences} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '16px',
            }}
          >
            {/* State Selection */}
            <div>
              <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: 600, color: '#e2e8f0', marginBottom: '6px' }}>
                Farmer State <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <select
                required
                className="input-field"
                value={profileState}
                onChange={(e) => setProfileState(e.target.value)}
                style={{ width: '100%', boxSizing: 'border-box' }}
              >
                <option value="">-- Select Your State --</option>
                {INDIAN_STATES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <small style={{ color: '#94a3b8', fontSize: '0.76rem', display: 'block', marginTop: '4px' }}>
                Market prices will synchronize strictly for this state.
              </small>
            </div>

            {/* District Selection */}
            <div>
              <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: 600, color: '#e2e8f0', marginBottom: '6px' }}>
                District (optional)
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g. Nashik, Warangal, Kolar"
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                style={{ width: '100%', boxSizing: 'border-box' }}
              />
              <small style={{ color: '#94a3b8', fontSize: '0.76rem', display: 'block', marginTop: '4px' }}>
                Filters mandi prices to nearby APMCs when available.
              </small>
            </div>

            {/* Crop Filter / Primary Crop */}
            <div>
              <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: 600, color: '#e2e8f0', marginBottom: '6px' }}>
                Selected Crop Filter
              </label>
              <select
                className="input-field"
                value={selectedCrop}
                onChange={(e) => setSelectedCrop(e.target.value)}
                style={{ width: '100%', boxSizing: 'border-box' }}
              >
                <option value="">-- All Agricultural Staples --</option>
                {COMMON_CROPS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <small style={{ color: '#94a3b8', fontSize: '0.76rem', display: 'block', marginTop: '4px' }}>
                Primary crop for synchronization and daily advisory.
              </small>
            </div>
          </div>

          {/* Location Detection & Save Row */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
              background: 'rgba(255, 255, 255, 0.03)',
              padding: '12px 16px',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.06)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                type="button"
                onClick={handleDetectLocation}
                disabled={isDetecting}
                className="btn-secondary"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 14px',
                  fontSize: '0.84rem',
                  cursor: isDetecting ? 'not-allowed' : 'pointer',
                }}
              >
                {isDetecting ? (
                  <>
                    <Loader2 size={14} className="spin-animation" /> Detecting Location...
                  </>
                ) : (
                  <>
                    <Navigation size={14} /> Detect My Location
                  </>
                )}
              </button>
              <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>
                Resolves approximate state and district via reverse-geocoding
              </span>
            </div>

            <button
              type="submit"
              disabled={isSaving}
              className="btn-secondary"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 16px',
                fontSize: '0.84rem',
                border: '1px solid #10b981',
                color: '#34d399',
                cursor: isSaving ? 'not-allowed' : 'pointer',
              }}
            >
              <Save size={14} /> {isSaving ? 'Saving...' : 'Save Market Preferences'}
            </button>
          </div>

          {/* Feedback messages for Detection & Save */}
          {detectSuccess && (
            <div style={{ color: '#34d399', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={15} /> {detectSuccess}
            </div>
          )}
          {detectError && (
            <div style={{ color: '#f87171', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertCircle size={15} /> {detectError}
            </div>
          )}
          {saveSuccess && (
            <div style={{ color: '#34d399', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={15} /> {saveSuccess}
            </div>
          )}
          {saveError && (
            <div style={{ color: '#f87171', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertCircle size={15} /> {saveError}
            </div>
          )}
        </form>

        {/* SYNCHRONIZATION STATUS & ACTION BOX */}
        <div
          style={{
            marginTop: '24px',
            background: 'rgba(15, 23, 42, 0.75)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            borderRadius: '14px',
            padding: '20px',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '14px',
              marginBottom: '16px',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span
                  style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    background: lastSyncAt ? '#10b981' : '#f59e0b',
                    display: 'inline-block',
                    boxShadow: lastSyncAt ? '0 0 8px #10b981' : 'none',
                  }}
                />
                <span style={{ fontSize: '0.96rem', fontWeight: 600, color: '#f1f5f9' }}>
                  Synchronization Status:{' '}
                  <span style={{ color: lastSyncAt ? '#34d399' : '#fbbf24' }}>
                    {isSyncing ? 'Synchronizing Live Records...' : lastSyncAt ? 'Active & Up-to-Date' : 'Pending Initial Sync'}
                  </span>
                </span>
              </div>
              <div style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '4px' }}>
                Restricted to State:{' '}
                <strong style={{ color: '#e2e8f0' }}>{user?.state || profileState || 'Not configured'}</strong>
                {user?.district ? ` | District: ${user.district}` : ''}
              </div>
            </div>

            <button
              type="button"
              onClick={handleSyncMarketPrices}
              disabled={isSyncing || (!user?.state && !profileState)}
              className="btn-primary"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 22px',
                fontSize: '0.92rem',
                fontWeight: 600,
                cursor: isSyncing || (!user?.state && !profileState) ? 'not-allowed' : 'pointer',
                opacity: !user?.state && !profileState ? 0.6 : 1,
              }}
            >
              <RefreshCw size={16} className={isSyncing ? 'spin-animation' : ''} />
              {isSyncing ? 'Syncing Mandi Records...' : 'Sync Market Prices Now'}
            </button>
          </div>

          {/* Sync Stats Cards */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '12px',
              marginTop: '16px',
            }}
          >
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Last Synchronized
              </div>
              <div style={{ color: '#f1f5f9', fontSize: '0.88rem', fontWeight: 600, marginTop: '4px' }}>
                {lastSyncAt ? new Date(lastSyncAt).toLocaleString('en-IN') : 'Never'}
              </div>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Records Processed
              </div>
              <div style={{ color: '#34d399', fontSize: '1.05rem', fontWeight: 700, marginTop: '4px' }}>
                {syncSummary?.records_inserted_or_updated ?? 0}
              </div>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Observation Date
              </div>
              <div style={{ color: '#f1f5f9', fontSize: '0.88rem', fontWeight: 600, marginTop: '4px' }}>
                {syncSummary?.today_date || new Date().toISOString().slice(0, 10)}
              </div>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Provider Source
              </div>
              <div style={{ color: '#f1f5f9', fontSize: '0.82rem', fontWeight: 500, marginTop: '4px', overflowWrap: 'anywhere' }}>
                {syncSummary?.provider || 'AGMARKNET / e-NAM'}
              </div>
            </div>
          </div>

          {/* Sync Success / Note / Error Callouts */}
          {syncFeedback?.note && (
            <div
              style={{
                marginTop: '14px',
                padding: '10px 14px',
                borderRadius: '8px',
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                color: '#34d399',
                fontSize: '0.84rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <CheckCircle2 size={16} />
              {syncFeedback.note}
            </div>
          )}

          {syncSummary?.records_inserted_or_updated === 0 && !isSyncing && lastSyncAt && (
            <div
              style={{
                marginTop: '14px',
                padding: '10px 14px',
                borderRadius: '8px',
                background: 'rgba(245, 158, 11, 0.12)',
                border: '1px solid rgba(245, 158, 11, 0.35)',
                color: '#fbbf24',
                fontSize: '0.84rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertTriangle size={16} />
              Provider returned zero records for this crop and state. Try syncing with a different crop or state.
            </div>
          )}

          {syncError && (
            <div
              style={{
                marginTop: '14px',
                padding: '10px 14px',
                borderRadius: '8px',
                background: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                color: '#f87171',
                fontSize: '0.84rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertCircle size={16} />
              {syncError}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function ProfileRow({ icon, label, value }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '13px 0',
        borderBottom: '1px solid rgba(255,255,255,.07)',
      }}
    >
      <span style={{ color: '#34d399', marginTop: '2px' }}>{icon}</span>
      <div style={{ minWidth: 0 }}>
        <div style={{ color: '#94a3b8', fontSize: '.78rem', marginBottom: '4px' }}>{label}</div>
        <div style={{ color: '#e2e8f0', overflowWrap: 'anywhere' }}>{value}</div>
      </div>
    </div>
  );
}