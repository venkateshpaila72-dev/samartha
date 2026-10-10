import React, { useState, useEffect } from 'react';
import { marketService } from '../../services/monitoringService';
import { TrendingUp, DollarSign, Store, ShieldCheck, MapPin } from 'lucide-react';

export default function MarketPricesPage({ activeBatch }) {
  const [market, setMarket] = useState(null);
  const [cropQuery, setCropQuery] = useState('Wheat');
  const [loading, setLoading] = useState(false);

  const fetchPrices = async (cropName = null) => {
    setLoading(true);
    try {
      const crop = cropName || (activeBatch?.crop_profile?.crop_name || 'Wheat');
      const data = await marketService.getMarketPrices(crop);
      setMarket(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeBatch?.crop_profile?.crop_name) {
      setCropQuery(activeBatch.crop_profile.crop_name);
      fetchPrices(activeBatch.crop_profile.crop_name);
    } else {
      fetchPrices('Wheat');
    }
  }, [activeBatch]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <span className="badge badge-verified">Workflow 10: Mandi Market Prices & Selling Advisory</span>
          <h1 style={{ fontSize: '1.8rem', marginTop: '4px' }}>APMC Agricultural Mandi Prices</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
            Current modal market prices and economic storage holding guidance across Indian wholesale mandis.
          </p>
        </div>

        <form onSubmit={(e) => { e.preventDefault(); fetchPrices(cropQuery); }} style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            className="input-field"
            value={cropQuery}
            onChange={(e) => setCropQuery(e.target.value)}
            style={{ width: '220px' }}
          />
          <button type="submit" className="btn-primary">Search Mandi</button>
        </form>
      </div>

      {market && (
        <>
          {/* Advisory & Trend Banner */}
          <div className="glass-panel glow-border" style={{ padding: '28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
            <div>
              <span className="badge badge-verified">
                <TrendingUp size={14} /> Trend: {market.price_trend?.toUpperCase()}
              </span>
              <h2 style={{ fontSize: '2.2rem', marginTop: '10px', color: '#34d399' }}>
                ₹{market.average_modal_price?.toLocaleString()} <span style={{ fontSize: '1rem', color: '#94a3b8' }}>/ Quintal (100 kg)</span>
              </h2>
              <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '4px' }}>
                Benchmark: AGMARKNET Wholesale Arrivals
              </div>
            </div>

            <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '20px 24px', borderRadius: '14px', maxWidth: '520px' }}>
              <div style={{ fontWeight: '700', color: '#f59e0b', marginBottom: '8px' }}>
                💼 Storage vs Selling Advisory
              </div>
              <p style={{ fontSize: '0.92rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                {market.recommendation}
              </p>
            </div>
          </div>

          {/* Mandi Table */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '16px' }}>
              Active APMC Mandi Benchmark Prices for {market.crop_name}
            </h3>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.92rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
                    <th style={{ padding: '12px 14px' }}>Mandi / Market</th>
                    <th style={{ padding: '12px 14px' }}>District & State</th>
                    <th style={{ padding: '12px 14px' }}>Modal Price</th>
                    <th style={{ padding: '12px 14px' }}>Min – Max Price</th>
                    <th style={{ padding: '12px 14px' }}>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {market.latest_prices.map((p, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                      <td style={{ padding: '12px 14px', fontWeight: '700', color: '#f8fafc' }}>
                        <Store size={14} color="#10b981" style={{ display: 'inline', marginRight: '6px' }} />
                        {p.market_name}
                      </td>
                      <td style={{ padding: '12px 14px', color: '#cbd5e1' }}>
                        {p.district}, {p.state}
                      </td>
                      <td style={{ padding: '12px 14px', fontWeight: '800', color: '#34d399', fontSize: '1.05rem' }}>
                        ₹{p.modal_price_per_quintal?.toLocaleString()}
                      </td>
                      <td style={{ padding: '12px 14px', color: '#94a3b8' }}>
                        ₹{p.min_price_per_quintal} – ₹{p.max_price_per_quintal}
                      </td>
                      <td style={{ padding: '12px 14px', color: '#64748b' }}>
                        {p.price_date}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
