import React, { useMemo, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiRequest } from '../../services/apiClient';
import {
  Shield,
  Sprout,
  ArrowRight,
  ShieldCheck,
  MessageCircle,
  MapPin,
  Navigation,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

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
  const [state, setState] = useState('');
  const [district, setDistrict] = useState('');
  const [selectedCrop, setSelectedCrop] = useState('');
  const [latitude, setLatitude] = useState(null);
  const [longitude, setLongitude] = useState(null);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState(null);
  const [locationSuccess, setLocationSuccess] = useState(null);
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

  const handleDetectLocation = () => {
    setLocationError(null);
    setLocationSuccess(null);

    if (!navigator.geolocation) {
      setLocationError(
        'Geolocation is not supported by your browser. Please select your state and district manually.'
      );
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          setLatitude(lat);
          setLongitude(lon);

          const res = await apiRequest(
            `/auth/reverse-geocode?latitude=${lat}&longitude=${lon}`
          );
          if (res?.data) {
            const detectedState = res.data.state || '';
            const detectedDistrict = res.data.district || '';
            if (detectedState) setState(detectedState);
            if (detectedDistrict) setDistrict(detectedDistrict);
            setLocationSuccess(
              `Location detected: ${detectedDistrict ? detectedDistrict + ', ' : ''}${detectedState}`
            );
          }
        } catch (err) {
          setLocationError(
            err.message ||
              'Reverse-geocoding failed. Please select your state and district manually.'
          );
        } finally {
          setLocating(false);
        }
      },
      (err) => {
        setLocating(false);
        let msg = 'Failed to detect location. Please select manually.';
        if (err.code === 1) {
          msg =
            'Location permission denied. Please select your state and district manually.';
        } else if (err.code === 2) {
          msg =
            'Location is unavailable. Please select your state and district manually.';
        } else if (err.code === 3) {
          msg =
            'Location request timed out. Please select your state and district manually.';
        }
        setLocationError(msg);
      },
      { timeout: 10000, enableHighAccuracy: false }
    );
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
          state: state.trim() || null,
          district: district.trim() || null,
          selected_crop: selectedCrop.trim() || null,
          latitude: latitude || null,
          longitude: longitude || null,
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

              {/* Location Detection Banner */}
              <div
                style={{
                  background: 'rgba(16, 185, 129, 0.05)',
                  border: '1px solid rgba(16, 185, 129, 0.25)',
                  borderRadius: '10px',
                  padding: '12px 14px',
                  marginBottom: '2px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '8px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <MapPin size={18} color="#10b981" />
                    <div>
                      <div
                        style={{
                          fontSize: '0.86rem',
                          fontWeight: 600,
                          color: '#f1f5f9',
                        }}
                      >
                        Farmer Location & Mandi State
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                        Required for state-wise mandi price synchronization
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleDetectLocation}
                    disabled={locating}
                    className="btn-secondary"
                    style={{
                      padding: '7px 12px',
                      fontSize: '0.82rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      border: '1px solid rgba(16, 185, 129, 0.4)',
                      background: 'rgba(16, 185, 129, 0.1)',
                      color: '#34d399',
                      cursor: locating ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {locating ? (
                      <>
                        <Loader2 size={14} className="spin-animation" />
                        Detecting...
                      </>
                    ) : (
                      <>
                        <Navigation size={14} />
                        Detect My Location
                      </>
                    )}
                  </button>
                </div>

                {locationSuccess && (
                  <div
                    style={{
                      marginTop: '8px',
                      fontSize: '0.8rem',
                      color: '#34d399',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                    }}
                  >
                    <CheckCircle2 size={14} />
                    {locationSuccess}
                  </div>
                )}

                {locationError && (
                  <div
                    style={{
                      marginTop: '8px',
                      fontSize: '0.8rem',
                      color: '#f87171',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                    }}
                  >
                    <AlertCircle size={14} />
                    {locationError}
                  </div>
                )}
              </div>

              {/* State Field */}
              <Field label="State (Required for Mandi Prices)">
                <select
                  required
                  className="input-field"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                >
                  <option value="">-- Select Your State --</option>
                  {INDIAN_STATES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </Field>

              {/* District Field */}
              <Field label="District (optional)">
                <input
                  type="text"
                  className="input-field"
                  placeholder="e.g. Nashik, Warangal, Kolar"
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                />
              </Field>

              {/* Primary / Selected Crop Field */}
              <Field label="Primary Crop (for Market Prices)">
                <select
                  className="input-field"
                  value={selectedCrop}
                  onChange={(e) => setSelectedCrop(e.target.value)}
                >
                  <option value="">-- Select Primary Crop --</option>
                  {COMMON_CROPS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </Field>

              <Field label="Village / Location (optional)">
                <input
                  type="text"
                  className="input-field"
                  placeholder="Village, town or locality"
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