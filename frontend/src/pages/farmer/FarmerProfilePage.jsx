import React, { useMemo, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import {
  Mail,
  MapPin,
  MessageCircle,
  UserRound,
  Languages,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { marketService } from '../../services/marketService';
import { useLanguage } from '../../context/LanguageContext';

const profileInputStyle = { width: '100%', boxSizing: 'border-box', padding: '10px 12px', borderRadius: '9px', border: '1px solid rgba(148,163,184,.3)', background: 'rgba(15,23,42,.75)', color: '#f8fafc' };

export default function FarmerProfilePage({ onNavigate }) {
  const { user, updateProfile } = useAuth();
  const { currentLang } = useLanguage();
  const [crop, setCrop] = useState(user?.selected_crop || '');
  const [state, setState] = useState(user?.state || '');
  const [district, setDistrict] = useState(user?.district || '');
  const [busy, setBusy] = useState(false);
  const [marketMessage, setMarketMessage] = useState('');
  const [syncResult, setSyncResult] = useState(null);

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

  return (
    <section style={{ maxWidth: '980px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ margin: 0, fontSize: '1.7rem' }}>
          My Farmer Profile
        </h1>
        <p style={{ color: '#94a3b8', marginTop: '8px' }}>
          Your account information and WhatsApp contact QR code.
        </p>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '20px',
        }}
      >
        <div
          className="glass-panel"
          style={{ padding: '24px', borderRadius: '16px' }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '22px',
            }}
          >
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
              <h2 style={{ margin: 0, fontSize: '1.15rem' }}>
                {user?.full_name || 'Farmer'}
              </h2>
              <span
                style={{
                  color: '#34d399',
                  fontSize: '.8rem',
                  textTransform: 'capitalize',
                }}
              >
                {user?.role || 'farmer'} account
              </span>
            </div>
          </div>

          <ProfileRow
            icon={<Mail size={17} />}
            label="Email"
            value={user?.email || 'Not provided'}
          />

          <ProfileRow
            icon={<MessageCircle size={17} />}
            label="WhatsApp Number"
            value={user?.phone_number || 'Not provided'}
          />

          <ProfileRow
            icon={<MapPin size={17} />}
            label="Village / Location"
            value={user?.village_or_location || 'Not provided'}
          />

          <ProfileRow
            icon={<Languages size={17} />}
            label="Preferred Language"
            value={user?.preferred_language || 'English'}
          />
        </div>

        <div
          className="glass-panel"
          style={{
            padding: '24px',
            borderRadius: '16px',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              marginBottom: '8px',
            }}
          >
            <MessageCircle size={20} color="#34d399" />
            <h2 style={{ margin: 0, fontSize: '1.15rem' }}>
              WhatsApp Contact
            </h2>
          </div>

          <p
            style={{
              color: '#94a3b8',
              fontSize: '.86rem',
              margin: '0 0 18px',
            }}
          >
            Scan this code with a phone camera to open the WhatsApp chat link.
          </p>

          {whatsappUrl ? (
            <>
              <div
                style={{
                  display: 'inline-block',
                  background: '#fff',
                  padding: '14px',
                  borderRadius: '12px',
                }}
              >
                <QRCodeSVG
                  value={whatsappUrl}
                  size={210}
                  level="M"
                  includeMargin
                />
              </div>

              <a
                href={whatsappUrl}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: 'block',
                  color: '#34d399',
                  marginTop: '16px',
                  overflowWrap: 'anywhere',
                  fontSize: '.9rem',
                }}
              >
                {whatsappUrl}
              </a>

              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  justifyContent: 'center',
                  gap: '10px',
                  marginTop: '16px',
                }}
              >
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={copyUrl}
                >
                  Copy WhatsApp URL
                </button>

                <a
                  href={whatsappUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-primary"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    textDecoration: 'none',
                    padding: '10px 14px',
                  }}
                >
                  Open WhatsApp
                </a>
              </div>
            </>
          ) : (
            <div
              style={{
                padding: '24px 12px',
                border: '1px dashed rgba(148,163,184,.35)',
                borderRadius: '12px',
                color: '#94a3b8',
              }}
            >
              No WhatsApp URL is saved for this account. Add a WhatsApp number
              and URL during registration.
            </div>
          )}
        </div>
      </div>

      <div className="glass-panel" style={{ marginTop: '24px', padding: '24px' }}>
        <h2 style={{ marginTop: 0 }}>Market Prices &amp; Sync</h2>
        <p style={{ color: '#94a3b8', lineHeight: 1.6 }}>Save the crop and mandi location you want FarmShield to use. Sync imports real provider observations; it does not create missing prices.</p>
        <form onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true); setMarketMessage(''); setSyncResult(null);
          try {
            const updated = await updateProfile({ selected_crop: crop.trim(), state: state.trim(), district: district.trim() || null });
            try {
              localStorage.setItem('farmshield_selected_crop', updated.selected_crop || crop.trim());
              localStorage.setItem('farmshield_state', updated.state || state.trim());
              if (district.trim()) localStorage.setItem('farmshield_district', district.trim());
            } catch { /* Server profile is authoritative. */ }
            setMarketMessage('Market preferences saved.');
          } catch (error) {
            setMarketMessage(error?.message || 'Could not save market preferences.');
          } finally { setBusy(false); }
        }} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: '12px' }}>
          <label style={{ display: 'grid', gap: '6px' }}>Selected crop
            <input value={crop} onChange={(event) => setCrop(event.target.value)} required maxLength={100} placeholder="e.g. Wheat" style={profileInputStyle} />
          </label>
          <label style={{ display: 'grid', gap: '6px' }}>State
            <input value={state} onChange={(event) => setState(event.target.value)} required maxLength={100} placeholder="e.g. Telangana" style={profileInputStyle} />
          </label>
          <label style={{ display: 'grid', gap: '6px' }}>District (optional)
            <input value={district} onChange={(event) => setDistrict(event.target.value)} maxLength={100} placeholder="e.g. Mancherial" style={profileInputStyle} />
          </label>
          <div style={{ display: 'flex', alignItems: 'end', gap: '10px', flexWrap: 'wrap' }}>
            <button className="btn-secondary" type="submit" disabled={busy}>Save Market Preferences</button>
            <button className="btn-primary" type="button" disabled={busy || !crop.trim() || !state.trim()} onClick={async () => {
              setBusy(true); setMarketMessage(''); setSyncResult(null);
              try {
                await updateProfile({ selected_crop: crop.trim(), state: state.trim(), district: district.trim() || null });
                const result = await marketService.syncMarketPrices({ crop: crop.trim(), state: state.trim(), district: district.trim() || undefined });
                setSyncResult(result);
                setMarketMessage('Sync request completed. Review the returned record counts below.');
              } catch (error) {
                setMarketMessage(error?.message || 'Market sync failed. Check provider configuration and try again later.');
              } finally { setBusy(false); }
            }}>{busy ? 'Working…' : 'Sync Market Prices Now'}</button>
            <button className="btn-secondary" type="button" onClick={() => onNavigate?.('market')}>View Market Prices</button>
          </div>
        </form>
        {marketMessage && <p role="status" aria-live="polite" style={{ marginTop: '14px', color: syncResult ? '#34d399' : '#cbd5e1' }}>{marketMessage}</p>}
        {syncResult?.data && <p style={{ color: '#cbd5e1', overflowWrap: 'anywhere' }}>
          Fetched: {syncResult.data.records_fetched ?? 0} · Inserted/updated: {syncResult.data.records_inserted_or_updated ?? 0} · Rejected: {syncResult.data.records_rejected ?? 0}
        </p>}
        <p style={{ color: '#94a3b8', fontSize: '.85rem' }}>Manual sync is limited to one request per account every 15 minutes. Availability depends on provider configuration and data coverage.</p>
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
      <span style={{ color: '#34d399', marginTop: '2px' }}>
        {icon}
      </span>

      <div style={{ minWidth: 0 }}>
        <div
          style={{
            color: '#94a3b8',
            fontSize: '.78rem',
            marginBottom: '4px',
          }}
        >
          {label}
        </div>

        <div
          style={{
            color: '#e2e8f0',
            overflowWrap: 'anywhere',
          }}
        >
          {value}
        </div>
      </div>
    </div>
  );
}