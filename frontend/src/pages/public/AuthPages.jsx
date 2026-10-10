import React, { useMemo, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Shield, Sprout, ArrowRight, ShieldCheck, MessageCircle } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

export default function AuthPages() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState('farmer');
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [language, setLanguage] = useState('en');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [whatsappUrl, setWhatsappUrl] = useState('');
  const [village, setVillage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const suggestedWhatsAppUrl = useMemo(() => {
    const digits = phoneNumber.replace(/\D/g, '');
    return digits ? `https://wa.me/${digits}` : '';
  }, [phoneNumber]);

  const currentWhatsAppUrl = (whatsappUrl.trim() || suggestedWhatsAppUrl).trim();

  const handleModeChange = (nextMode) => {
    setMode(nextMode);
    setIsRegister(false);
    setError(null);
    setPassword('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isRegister) {
        await register({
          email,
          password,
          full_name: fullName,
          preferred_language: language,
          phone_number: phoneNumber.trim() || null,
          whatsapp_url: currentWhatsAppUrl || null,
          village_or_location: village.trim() || null,
        });
      } else {
        await login(email, password, mode);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check your details.');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    if (mode === 'admin') return;
    setIsRegister((current) => !current);
    setError(null);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        className="glass-panel glow-border"
        style={{
          maxWidth: '500px',
          width: '100%',
          padding: '32px',
          boxSizing: 'border-box',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div
            style={{
              width: '54px',
              height: '54px',
              borderRadius: '14px',
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 12px',
              boxShadow: '0 6px 20px rgba(16, 185, 129, 0.4)',
            }}
          >
            <Shield size={28} color="#fff" />
          </div>

          <h1 style={{ fontSize: '1.75rem', letterSpacing: '-0.02em', margin: 0 }}>
            Farm<span style={{ color: '#10b981' }}>Shield</span>
          </h1>

          <p style={{ color: '#94a3b8', fontSize: '0.88rem', marginTop: '8px' }}>
            AI-Powered Crop Storage & Environmental Monitoring
          </p>
        </div>

        <div
          role="group"
          aria-label="Choose login type"
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '10px',
            marginBottom: '22px',
          }}
        >
          <button
            type="button"
            onClick={() => handleModeChange('farmer')}
            aria-pressed={mode === 'farmer'}
            className={mode === 'farmer' ? 'btn-primary' : 'btn-secondary'}
            style={{
              padding: '12px 8px',
              justifyContent: 'center',
              border: mode === 'farmer'
                ? '1px solid #10b981'
                : '1px solid rgba(255,255,255,.12)',
            }}
          >
            <Sprout size={17} /> Farmer Login
          </button>

          <button
            type="button"
            onClick={() => handleModeChange('admin')}
            aria-pressed={mode === 'admin'}
            className={mode === 'admin' ? 'btn-primary' : 'btn-secondary'}
            style={{
              padding: '12px 8px',
              justifyContent: 'center',
              border: mode === 'admin'
                ? '1px solid #10b981'
                : '1px solid rgba(255,255,255,.12)',
            }}
          >
            <ShieldCheck size={17} /> Admin Login
          </button>
        </div>

        <h2 style={{ fontSize: '1.15rem', margin: '0 0 16px' }}>
          {isRegister
            ? 'Create Farmer Account'
            : mode === 'admin'
              ? 'Administrator Sign In'
              : 'Farmer Sign In'}
        </h2>

        {mode === 'admin' && !isRegister && (
          <p
            style={{
              color: '#94a3b8',
              fontSize: '.84rem',
              marginTop: '-8px',
              marginBottom: '16px',
            }}
          >
            Admin access is available only for provisioned administrator accounts.
            Farmer registration is not available from this tab.
          </p>
        )}

        {error && (
          <div
            role="alert"
            style={{
              background: 'rgba(239,68,68,.15)',
              border: '1px solid #ef4444',
              color: '#f87171',
              padding: '10px 14px',
              borderRadius: '8px',
              fontSize: '.88rem',
              marginBottom: '16px',
            }}
          >
            {error}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          style={{ display: 'flex', flexDirection: 'column', gap: '13px' }}
        >
          {isRegister && mode === 'farmer' && (
            <Field label="Full Name">
              <input
                type="text"
                required
                minLength={2}
                autoComplete="name"
                className="input-field"
                placeholder="Your full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </Field>
          )}

          <Field label="Email Address">
            <input
              type="email"
              required
              autoComplete="username"
              className="input-field"
              placeholder={mode === 'admin' ? 'admin@example.com' : 'farmer@example.com'}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>

          <Field label="Password">
            <input
              type="password"
              required
              minLength={isRegister ? 6 : undefined}
              autoComplete={isRegister ? 'new-password' : 'current-password'}
              className="input-field"
              placeholder="Enter password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>

          {isRegister && mode === 'farmer' && (
            <>
              <Field label="Preferred Language">
                <select
                  className="input-field"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="en">English</option>
                  <option value="hi">हिंदी (Hindi)</option>
                  <option value="te">తెలుగు (Telugu)</option>
                  <option value="ta">தமிழ் (Tamil)</option>
                </select>
              </Field>

              <Field label="Village / Location (optional)">
                <input
                  type="text"
                  className="input-field"
                  placeholder="Village, town or district"
                  value={village}
                  onChange={(e) => setVillage(e.target.value)}
                />
              </Field>

              <Field label="WhatsApp Number (include country code)">
                <input
                  type="tel"
                  autoComplete="tel"
                  className="input-field"
                  placeholder="+919876543210"
                  value={phoneNumber}
                  onChange={(e) => {
                    setPhoneNumber(e.target.value);
                    if (whatsappUrl) setWhatsappUrl('');
                  }}
                />
                <small
                  style={{
                    display: 'block',
                    color: '#94a3b8',
                    marginTop: '5px',
                    lineHeight: 1.5,
                  }}
                >
                  Include your country code, for example +91. Sending automated alerts
                  requires a WhatsApp provider configured in the backend.
                </small>
              </Field>

              <Field label="WhatsApp Chat URL (optional)">
                <input
                  type="url"
                  className="input-field"
                  placeholder="https://wa.me/919876543210"
                  value={whatsappUrl || suggestedWhatsAppUrl}
                  onChange={(e) => setWhatsappUrl(e.target.value)}
                />
                <small style={{ display: 'block', color: '#94a3b8', marginTop: '5px' }}>
                  <MessageCircle
                    size={13}
                    style={{ verticalAlign: 'middle', marginRight: '4px' }}
                  />
                  The URL is generated from your number. You can edit it if needed.
                </small>
              </Field>

              {currentWhatsAppUrl && (
                <div
                  style={{
                    border: '1px solid rgba(16,185,129,.35)',
                    borderRadius: '12px',
                    padding: '16px',
                    textAlign: 'center',
                    background: 'rgba(16,185,129,.06)',
                  }}
                >
                  <h3
                    style={{
                      margin: '0 0 8px',
                      fontSize: '1rem',
                      color: '#e2e8f0',
                    }}
                  >
                    Your WhatsApp QR Code
                  </h3>

                  <p
                    style={{
                      margin: '0 0 12px',
                      color: '#94a3b8',
                      fontSize: '.82rem',
                    }}
                  >
                    Scan this QR code to open your WhatsApp chat link.
                  </p>

                  <div
                    style={{
                      display: 'inline-block',
                      background: '#fff',
                      padding: '12px',
                      borderRadius: '8px',
                    }}
                  >
                    <QRCodeSVG
                      value={currentWhatsAppUrl}
                      size={176}
                      level="M"
                      includeMargin
                    />
                  </div>

                  <a
                    href={currentWhatsAppUrl}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display: 'block',
                      marginTop: '12px',
                      color: '#34d399',
                      overflowWrap: 'anywhere',
                      fontSize: '.85rem',
                    }}
                  >
                    {currentWhatsAppUrl}
                  </a>
                </div>
              )}
            </>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary"
            style={{
              marginTop: '7px',
              justifyContent: 'center',
              padding: '12px',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading
              ? 'Please wait...'
              : isRegister
                ? 'Create Farmer Account'
                : mode === 'admin'
                  ? 'Sign In as Admin'
                  : 'Sign In as Farmer'}
            <ArrowRight size={16} />
          </button>
        </form>

        {mode === 'farmer' && (
          <div
            style={{
              textAlign: 'center',
              marginTop: '20px',
              paddingTop: '16px',
              borderTop: '1px solid rgba(255,255,255,.08)',
            }}
          >
            <button
              type="button"
              onClick={switchMode}
              style={{
                background: 'none',
                border: 'none',
                color: '#10b981',
                fontSize: '.88rem',
                cursor: 'pointer',
                fontWeight: '600',
              }}
            >
              {isRegister
                ? 'Already have an account? Sign in'
                : 'New farmer? Create an account'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label
        style={{
          fontSize: '.82rem',
          color: '#94a3b8',
          display: 'block',
          marginBottom: '5px',
        }}
      >
        {label}
      </label>
      {children}
    </div>
  );
}