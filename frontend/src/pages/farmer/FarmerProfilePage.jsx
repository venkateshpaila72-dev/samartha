import React, { useMemo } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import {
  Mail,
  MapPin,
  MessageCircle,
  UserRound,
  Languages,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function FarmerProfilePage() {
  const { user } = useAuth();

  // This QR must point to the configured WhatsApp sender, NOT the farmer's own number.
  // Set these in frontend/.env: VITE_WHATSAPP_OPT_IN_NUMBER and
  // VITE_WHATSAPP_JOIN_KEYWORD using the exact number/keyword shown by Twilio.
  const whatsappUrl = useMemo(() => {
    const senderDigits = (import.meta.env.VITE_WHATSAPP_OPT_IN_NUMBER || '')
      .replace(/\D/g, '');
    const joinKeyword = (import.meta.env.VITE_WHATSAPP_JOIN_KEYWORD || '').trim();

    // Never generate a misleading QR if Twilio opt-in details have not been configured.
    if (!senderDigits || !joinKeyword) return '';

    return `https://wa.me/${senderDigits}?text=${encodeURIComponent(joinKeyword)}`;
  }, []);

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
          Your account information and WhatsApp alert opt-in QR code.
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
            Scan to open the configured FarmShield WhatsApp sender with the opt-in message pre-filled. Tap Send in WhatsApp to complete opt-in.
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
              WhatsApp opt-in QR is not configured. Add VITE_WHATSAPP_OPT_IN_NUMBER and VITE_WHATSAPP_JOIN_KEYWORD to frontend/.env using the exact sender number and join keyword from your Twilio WhatsApp setup, then restart the frontend.
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