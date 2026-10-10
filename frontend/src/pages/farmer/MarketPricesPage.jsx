import React, { useCallback, useEffect, useState } from 'react';
import { marketService } from '../../services/marketService';
import { TrendingUp, Store, MapPin, RefreshCw, AlertCircle } from 'lucide-react';

export default function MarketPricesPage({ activeBatch }) {
  const batchCrop = activeBatch?.crop_profile?.crop_name || '';
  const [cropQuery, setCropQuery] = useState(batchCrop);
  const [state, setState] = useState(() => localStorage.getItem('farmshield_state') || '');
  const [district, setDistrict] = useState(() => localStorage.getItem('farmshield_district') || '');
  const [market, setMarket] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchPrices = useCallback(async (crop = cropQuery) => {
    if (!crop?.trim()) {
      setMarket(null);
      setError('Select a crop or open a storage batch with a crop assigned.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const data = await marketService.getMarketPrices(crop.trim(), {
        state: state.trim(),
        district: district.trim(),
      });
      setMarket(data);
      if (!data?.latest_prices?.length) {
        setError(data?.recommendation || 'No market-price records were found for this crop and location.');
      }
    } catch (err) {
      setMarket(null);
      setError(err?.message || 'Unable to load market prices. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [cropQuery, state, district]);

  useEffect(() => {
    if (batchCrop) {
      setCropQuery(batchCrop);
      fetchPrices(batchCrop);
    } else {
      setMarket(null);
      setError('Enter the crop and location to search the imported mandi-price dataset.');
    }
    // Refresh when the active storage batch changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchCrop]);

  const submit = (event) => {
    event.preventDefault();
    localStorage.setItem('farmshield_state', state.trim());
    localStorage.setItem('farmshield_district', district.trim());
    fetchPrices(cropQuery);
  };

  const prices = Array.isArray(market?.latest_prices) ? market.latest_prices : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <section className="glass-panel" style={{ padding: '24px' }}>
        <span className="badge badge-verified">Mandi Market Prices</span>
        <h1 style={{ fontSize: '1.8rem', marginTop: '8px' }}>Agricultural Market Prices</h1>
        <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '18px' }}>
          Search actual market records imported into FarmShield. Prices are not estimated or replaced with sample values.
        </p>

        <form onSubmit={submit} style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span>Selected crop</span>
            <input
              type="text"
              className="input-field"
              value={cropQuery}
              onChange={(event) => setCropQuery(event.target.value)}
              placeholder="Enter your crop"
              required
              style={{ minWidth: '180px' }}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span>State</span>
            <input
              type="text"
              className="input-field"
              value={state}
              onChange={(event) => setState(event.target.value)}
              placeholder="Your state"
              required
              style={{ minWidth: '160px' }}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span>District (optional)</span>
            <input
              type="text"
              className="input-field"
              value={district}
              onChange={(event) => setDistrict(event.target.value)}
              placeholder="Your district"
              style={{ minWidth: '160px' }}
            />
          </label>
          <button type="submit" className="btn-primary" disabled={loading} style={{ alignSelf: 'end' }}>
            {loading ? 'Loading…' : 'Search Prices'}
          </button>
        </form>
      </section>

      {loading && (
        <div className="glass-panel" role="status" style={{ padding: '24px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <RefreshCw size={18} className="animate-spin" />
          Loading market records…
        </div>
      )}

      {!loading && error && (
        <div className="glass-panel" role="status" style={{ padding: '20px', display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
          <AlertCircle size={20} color="#f59e0b" style={{ flexShrink: 0 }} />
          <div>
            <strong>Market prices unavailable</strong>
            <p style={{ color: '#94a3b8', marginTop: '6px' }}>{error}</p>
          </div>
        </div>
      )}

      {!loading && market && prices.length > 0 && (
        <>
          <section className="glass-panel glow-border" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '18px' }}>
            <div>
              <span className="badge badge-verified">
                <TrendingUp size={14} /> Trend: {(market.price_trend || 'unknown').toUpperCase()}
              </span>
              <h2 style={{ fontSize: '2rem', marginTop: '10px', color: '#34d399' }}>
                {market.average_modal_price == null
                  ? '—'
                  : `₹${Number(market.average_modal_price).toLocaleString('en-IN')}`}
                <span style={{ fontSize: '1rem', color: '#94a3b8' }}> / Quintal</span>
              </h2>
              <p style={{ color: '#94a3b8', marginTop: '6px' }}>
                {market.crop_name} · {state}{district ? `, ${district}` : ''}
              </p>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '18px 20px', borderRadius: '14px', maxWidth: '520px' }}>
              <strong style={{ color: '#f59e0b' }}>Market information</strong>
              <p style={{ fontSize: '0.92rem', color: '#cbd5e1', lineHeight: 1.5, marginTop: '8px' }}>
                {market.recommendation}
              </p>
              <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '8px' }}>
                Source: imported market dataset · Retrieved {market.retrieval_timestamp ? new Date(market.retrieval_timestamp).toLocaleString() : 'recently'}
              </p>
            </div>
          </section>

          <section className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '16px' }}>
              Mandi records for {market.crop_name}
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.92rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8' }}>
                    <th style={{ padding: '12px' }}>Mandi / Market</th>
                    <th style={{ padding: '12px' }}>District & State</th>
                    <th style={{ padding: '12px' }}>Modal Price</th>
                    <th style={{ padding: '12px' }}>Min – Max</th>
                    <th style={{ padding: '12px' }}>Reported Date</th>
                    <th style={{ padding: '12px' }}>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {prices.map((price, index) => (
                    <tr key={`${price.market_name}-${price.price_date}-${index}`} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '12px', fontWeight: 700 }}>
                        <Store size={14} style={{ display: 'inline', marginRight: '6px' }} />
                        {price.market_name}
                      </td>
                      <td style={{ padding: '12px', color: '#cbd5e1' }}>
                        <MapPin size={13} style={{ display: 'inline', marginRight: '4px' }} />
                        {price.district}, {price.state}
                      </td>
                      <td style={{ padding: '12px', fontWeight: 800, color: '#34d399' }}>
                        ₹{Number(price.modal_price_per_quintal).toLocaleString('en-IN')}
                      </td>
                      <td style={{ padding: '12px', color: '#94a3b8' }}>
                        ₹{Number(price.min_price_per_quintal).toLocaleString('en-IN')} – ₹{Number(price.max_price_per_quintal).toLocaleString('en-IN')}
                      </td>
                      <td style={{ padding: '12px', color: '#94a3b8' }}>{price.price_date}</td>
                      <td style={{ padding: '12px', color: '#94a3b8' }}>{price.source || 'Imported dataset'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
