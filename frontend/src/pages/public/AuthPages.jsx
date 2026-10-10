import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Shield, Sprout, ArrowRight, UserCheck, ShieldAlert } from 'lucide-react';

export default function AuthPages() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [language, setLanguage] = useState('en');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
        });
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDemo = async () => {
    if (!import.meta.env.DEV) return;
    setLoading(true);
    setError(null);
    const demoEmail = 'farmer_demo@farmshield.org';
    const demoPass = 'DemoPassword123';
    try {
      try {
        await login(demoEmail, demoPass);
      } catch {
        await register({
          email: demoEmail,
          password: demoPass,
          full_name: 'Kisan Ramesh Patel',
          preferred_language: 'en',
          village_or_location: 'Nashik Granary',
        });
      }
    } catch (err) {
      setError(err.message || 'Demo authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px'
    }}>
      <div className="glass-panel glow-border" style={{
        maxWidth: '460px',
        width: '100%',
        padding: '36px 32px'
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div style={{
            width: '54px',
            height: '54px',
            borderRadius: '14px',
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 12px',
            boxShadow: '0 6px 20px rgba(16, 185, 129, 0.4)'
          }}>
            <Shield size={28} color="#fff" />
          </div>
          <h1 style={{ fontSize: '1.75rem', letterSpacing: '-0.02em' }}>
            Farm<span style={{ color: '#10b981' }}>Shield</span>
          </h1>
          <p style={{ color: '#94a3b8', fontSize: '0.88rem', marginTop: '4px' }}>
            AI-Powered Crop Storage & Environmental Monitoring
          </p>
        </div>

        {/* Quick Demo Login Button (Dev mode only) */}
        {import.meta.env.DEV && (
          <div style={{
            background: 'rgba(15, 23, 42, 0.7)',
            padding: '12px 14px',
            borderRadius: '12px',
            marginBottom: '20px',
            border: '1px solid rgba(255, 255, 255, 0.08)'
          }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block', marginBottom: '8px', textAlign: 'center', fontWeight: '600', textTransform: 'uppercase' }}>
              ⚡ Development Mode Quick Access
            </span>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleQuickDemo}
              style={{ width: '100%', fontSize: '0.82rem', padding: '8px 12px', justifyContent: 'center' }}
            >
              <UserCheck size={14} color="#10b981" /> Kisan Farmer Demo
            </button>
          </div>
        )}

        {error && (
          <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#f87171', padding: '10px 14px', borderRadius: '8px', fontSize: '0.88rem', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {isRegister && (
            <div>
              <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Full Name</label>
              <input
                type="text"
                required
                className="input-field"
                placeholder="Ramesh Kumar"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>
          )}

          <div>
            <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Email Address</label>
            <input
              type="email"
              required
              className="input-field"
              placeholder="farmer@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Password</label>
            <input
              type="password"
              required
              className="input-field"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {isRegister && (
            <div>
              <label style={{ fontSize: '0.82rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Preferred Language</label>
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
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary"
            style={{ marginTop: '8px', justifyContent: 'center', padding: '12px' }}
          >
            {loading ? 'Authenticating...' : (isRegister ? 'Create Account' : 'Sign In')} <ArrowRight size={16} />
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '20px', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <button
            type="button"
            onClick={() => { setIsRegister(!isRegister); setError(null); }}
            style={{ background: 'none', border: 'none', color: '#10b981', fontSize: '0.88rem', cursor: 'pointer', fontWeight: '600' }}
          >
            {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Create one"}
          </button>
        </div>
      </div>
    </div>
  );
}
