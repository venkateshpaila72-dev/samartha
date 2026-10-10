import React, { useCallback, useEffect, useState } from 'react';
import { marketService } from '../../services/marketService';
import { TrendingUp, Store, MapPin, RefreshCw, AlertCircle, ShoppingBag, Truck, ShieldAlert, CheckCircle2, Award } from 'lucide-react';
import TranslatedText from '../../components/TranslatedText';

export default function MarketPricesPage({ activeBatch }) {
  const batchCrop = activeBatch?.crop_profile?.crop_name || '';
  const [cropQuery, setCropQuery] = useState(() => {
    try { return batchCrop || localStorage.getItem('farmshield_selected_crop') || ''; } catch { return batchCrop; }
  });
  const [state, setState] = useState(() => { try { return localStorage.getItem('farmshield_state') || ''; } catch { return ''; } });
  const [district, setDistrict] = useState(() => { try { return localStorage.getItem('farmshield_district') || ''; } catch { return ''; } });
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
    try {
      localStorage.setItem('farmshield_selected_crop', cropQuery.trim());
      localStorage.setItem('farmshield_state', state.trim());
      localStorage.setItem('farmshield_district', district.trim());
    } catch { /* The selected values still work for this session when storage is unavailable. */ }
    fetchPrices(cropQuery);
  };

  const prices = Array.isArray(market?.latest_prices) ? market.latest_prices : [];
  const history = Array.isArray(market?.historical_prices) ? market.historical_prices : [];
  const forecast = Array.isArray(market?.forecast_prices) ? market.forecast_prices : [];
  const chartValues = [
    ...history.map((point) => Number(point.average_modal_price_per_quintal)),
    ...forecast.map((point) => Number(point.predicted_modal_price_per_quintal)),
  ].filter(Number.isFinite);
  const chartMin = chartValues.length ? Math.min(...chartValues) : 0;
  const chartMax = chartValues.length ? Math.max(...chartValues) : 1;
  const chartPoints = chartValues.map((value, index) => {
    const x = chartValues.length <= 1 ? 10 : 10 + (index * 580) / (chartValues.length - 1);
    const y = 150 - ((value - chartMin) / Math.max(1, chartMax - chartMin)) * 125;
    return { x, y };
  });
  const historyPath = chartPoints.slice(0, history.length).map((p) => `${p.x},${p.y}`).join(' ');
  const forecastPath = chartPoints.slice(Math.max(0, history.length - 1)).map((p) => `${p.x},${p.y}`).join(' ');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <section className="glass-panel" style={{ padding: '24px' }}>
        <span className="badge badge-verified"><TranslatedText text="Mandi Market Prices" /></span>
        <h1 style={{ fontSize: '1.8rem', marginTop: '8px' }}><TranslatedText text="Agricultural Market Prices" /></h1>
        <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '18px' }}>
          <TranslatedText text="Search actual market records imported into FarmShield. Prices are not estimated or replaced with sample values." />
        </p>

        <form onSubmit={submit} style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span><TranslatedText text="Selected crop" /></span>
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
            <span><TranslatedText text="State" /></span>
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
            <span><TranslatedText text="District (optional)" /></span>
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
            {loading ? <TranslatedText text="Loading…" /> : <TranslatedText text="Search Prices" />}
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
            <strong><TranslatedText text="Market prices unavailable" /></strong>
            <p style={{ color: '#94a3b8', marginTop: '6px' }}>{error}</p>
          </div>
        </div>
      )}

      {!loading && market && prices.length > 0 && (
        <>
          <section className="glass-panel glow-border" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '18px' }}>
            <div>
              <span className="badge badge-verified">
                <TrendingUp size={14} /> <TranslatedText text="Trend:" /> <TranslatedText text={(market.price_trend || 'unknown').toUpperCase()} />
              </span>
              <h2 style={{ fontSize: '2rem', marginTop: '10px', color: '#34d399' }}>
                {market.average_modal_price == null
                  ? '—'
                  : `₹${Number(market.average_modal_price).toLocaleString('en-IN')}`}
                <span style={{ fontSize: '1rem', color: '#94a3b8' }}> / <TranslatedText text="Quintal" /></span>
              </h2>
              <p style={{ color: '#94a3b8', marginTop: '6px' }}>
                {market.crop_name} · {state}{district ? `, ${district}` : ''}
              </p>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '18px 20px', borderRadius: '14px', maxWidth: '520px' }}>
              <strong style={{ color: '#f59e0b' }}><TranslatedText text="Market information" /></strong>
              <p style={{ fontSize: '0.92rem', color: '#cbd5e1', lineHeight: 1.5, marginTop: '8px' }}>
                {market.recommendation}
              </p>
              <p style={{ color: '#94a3b8', fontSize: '0.8rem', marginTop: '8px' }}>
                <TranslatedText text="Source: imported market dataset · Retrieved" /> {market.retrieval_timestamp ? new Date(market.retrieval_timestamp).toLocaleString() : <TranslatedText text="recently" />}
              </p>
            </div>
          </section>

          {market.selling_recommendation && (
            <section className="glass-panel" style={{ padding: '24px', borderLeft: '4px solid #10b981' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ShoppingBag size={22} color="#34d399" />
                  <h3 style={{ fontSize: '1.3rem', margin: 0, fontWeight: 700, color: '#34d399' }}>
                    <TranslatedText text={market.selling_recommendation.decision} />
                  </h3>
                </div>
                <span className={`badge ${market.selling_recommendation.confidence === 'strong' ? 'badge-verified' : market.selling_recommendation.confidence === 'moderate' ? 'badge-info' : 'badge-warning'}`}>
                  Confidence: {market.selling_recommendation.confidence?.toUpperCase()}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px', marginBottom: '18px' }}>
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '12px' }}>
                  <div style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '4px' }}>Current Market Price</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#34d399' }}>
                    {market.selling_recommendation.current_price ? `₹${Number(market.selling_recommendation.current_price).toLocaleString('en-IN')}` : '—'} <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>/ qtl</span>
                  </div>
                  {market.selling_recommendation.best_alternative_market && (
                    <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '6px' }}>
                      Best Alt: <strong>{market.selling_recommendation.best_alternative_market}</strong> (₹{Number(market.selling_recommendation.best_alternative_price).toLocaleString('en-IN')})
                    </div>
                  )}
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f59e0b', fontSize: '0.8rem', marginBottom: '4px' }}>
                    <ShieldAlert size={14} /> Storage Condition & Risk
                  </div>
                  <div style={{ fontSize: '0.88rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                    <TranslatedText text={market.selling_recommendation.storage_risk} />
                  </div>
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '12px' }}>
                  <div style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '4px' }}>Weather & Transport Risk</div>
                  <div style={{ fontSize: '0.88rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                    <TranslatedText text={market.selling_recommendation.weather_considerations} />
                  </div>
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '12px' }}>
                  <div style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '4px' }}>Estimated Net Return</div>
                  <div style={{ fontSize: '0.88rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                    <TranslatedText text={market.selling_recommendation.estimated_net_return || 'Requires lot weight and transport distance'} />
                  </div>
                </div>
              </div>

              <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.25)', padding: '12px 16px', borderRadius: '10px', fontSize: '0.88rem', color: '#cbd5e1' }}>
                <strong style={{ color: '#34d399' }}>Price Outlook: </strong>
                <TranslatedText text={market.selling_recommendation.short_term_outlook} />
              </div>

              {market.selling_recommendation.ranked_options && market.selling_recommendation.ranked_options.length > 0 && (
                <div style={{ marginTop: '20px' }}>
                  <h4 style={{ fontSize: '1.05rem', margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Award size={16} color="#f59e0b" /> <TranslatedText text="Top Recommended Mandis (Ranked by Expected Net Return)" />
                  </h4>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8' }}>
                          <th style={{ padding: '8px 10px' }}>Rank</th>
                          <th style={{ padding: '8px 10px' }}>Mandi / Location</th>
                          <th style={{ padding: '8px 10px' }}>Modal Price</th>
                          <th style={{ padding: '8px 10px' }}>Est. Transport</th>
                          <th style={{ padding: '8px 10px' }}>Est. Net Return</th>
                          <th style={{ padding: '8px 10px' }}>Notes / Timing</th>
                        </tr>
                      </thead>
                      <tbody>
                        {market.selling_recommendation.ranked_options.map((opt) => (
                          <tr key={`rank-${opt.rank}-${opt.market_name}`} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ padding: '10px', fontWeight: 800, color: opt.rank === 1 ? '#34d399' : '#e2e8f0' }}>
                              #{opt.rank}
                            </td>
                            <td style={{ padding: '10px', fontWeight: 600 }}>
                              <Store size={13} style={{ display: 'inline', marginRight: '5px' }} />
                              {opt.market_name}
                              <div style={{ fontSize: '0.78rem', color: '#94a3b8', fontWeight: 400 }}>
                                {opt.district}, {opt.state}
                              </div>
                            </td>
                            <td style={{ padding: '10px', fontWeight: 700, color: '#34d399' }}>
                              ₹{Number(opt.modal_price).toLocaleString('en-IN')}/qtl
                            </td>
                            <td style={{ padding: '10px', color: '#cbd5e1' }}>
                              <Truck size={13} style={{ display: 'inline', marginRight: '4px' }} />
                              ₹{opt.transport_cost_per_quintal || 0}/qtl
                              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}> (~{opt.distance_km || 0} km)</span>
                            </td>
                            <td style={{ padding: '10px', fontWeight: 700, color: '#38bdf8' }}>
                              ₹{Number(opt.net_return_per_quintal || opt.modal_price).toLocaleString('en-IN')}/qtl
                            </td>
                            <td style={{ padding: '10px', color: '#94a3b8', fontSize: '0.82rem' }}>
                              {opt.notes || 'Normal delivery'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p style={{ color: '#64748b', fontSize: '0.78rem', margin: '10px 0 0 0' }}>
                    * Transport estimate benchmark: ₹1.50/qtl/km. Actual haulage depends on vehicle capacity, road conditions, and mandi handling charges. Never sell on credit without verified weighment slips.
                  </p>
                </div>
              )}
            </section>
          )}

          <section className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '16px' }}>
              Mandi records for {market.crop_name}
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.92rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8' }}>
                    <th style={{ padding: '12px' }}><TranslatedText text="Mandi / Market" /></th>
                    <th style={{ padding: '12px' }}><TranslatedText text="District & State" /></th>
                    <th style={{ padding: '12px' }}><TranslatedText text="Modal Price" /></th>
                    <th style={{ padding: '12px' }}><TranslatedText text="Min – Max" /></th>
                    <th style={{ padding: '12px' }}><TranslatedText text="Reported Date" /></th>
                    <th style={{ padding: '12px' }}><TranslatedText text="Source" /></th>
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

          <section className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>
              <TranslatedText text="Historical market prices" />
            </h3>
            <p style={{ color: '#94a3b8', marginBottom: '16px' }}>
              <TranslatedText text="Actual stored market observations for the selected crop and location. Missing dates are not filled with invented values." />
            </p>
            {history.length >= 2 ? (
              <>
                <div style={{ overflowX: 'auto' }}>
                  <svg viewBox="0 0 600 175" role="img" aria-label="Historical and forecast crop market prices" style={{ width: '100%', minWidth: '320px', height: 'auto' }}>
                    <line x1="10" y1="150" x2="590" y2="150" stroke="currentColor" opacity=".25" />
                    <polyline points={historyPath} fill="none" stroke="#34d399" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
                    {forecast.length > 0 && <polyline points={forecastPath} fill="none" stroke="#f59e0b" strokeWidth="3" strokeDasharray="7 5" strokeLinejoin="round" strokeLinecap="round" />}
                  </svg>
                </div>
                <div style={{ display: 'flex', gap: '18px', flexWrap: 'wrap', color: '#94a3b8', fontSize: '.85rem' }}>
                  <span>🟢 <TranslatedText text="Actual historical prices" /></span>
                  <span>🟠 <TranslatedText text="Indicative forecast" /></span>
                </div>
                <div style={{ maxHeight: '260px', overflowY: 'auto', marginTop: '14px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '.9rem' }}>
                    <thead><tr><th style={{ padding: '8px' }}><TranslatedText text="Date" /></th><th style={{ padding: '8px' }}><TranslatedText text="Average modal price / quintal" /></th><th style={{ padding: '8px' }}><TranslatedText text="Observations" /></th></tr></thead>
                    <tbody>{history.map((point) => <tr key={point.date}><td style={{ padding: '8px' }}>{point.date}</td><td style={{ padding: '8px' }}>₹{Number(point.average_modal_price_per_quintal).toLocaleString('en-IN')}</td><td style={{ padding: '8px' }}>{point.observations}</td></tr>)}</tbody>
                  </table>
                </div>
              </>
            ) : (
              <p style={{ color: '#f59e0b' }}><TranslatedText text="Not enough dated historical observations to draw a reliable trend." /></p>
            )}
          </section>

          <section className="glass-panel" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '8px' }}><TranslatedText text="7-day price outlook" /></h3>
            <p style={{ color: '#94a3b8', marginBottom: '14px' }}>{market.forecast_note || <TranslatedText text="Forecast unavailable" />}</p>
            {forecast.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '.9rem' }}>
                  <thead><tr><th style={{ padding: '10px' }}><TranslatedText text="Forecast date" /></th><th style={{ padding: '10px' }}><TranslatedText text="Estimated price / quintal" /></th><th style={{ padding: '10px' }}><TranslatedText text="Indicative range" /></th></tr></thead>
                  <tbody>{forecast.map((point) => <tr key={point.date}><td style={{ padding: '10px' }}>{point.date}</td><td style={{ padding: '10px' }}>₹{Number(point.predicted_modal_price_per_quintal).toLocaleString('en-IN')}</td><td style={{ padding: '10px' }}>₹{Number(point.lower_estimate).toLocaleString('en-IN')} – ₹{Number(point.upper_estimate).toLocaleString('en-IN')}</td></tr>)}</tbody>
                </table>
              </div>
            ) : <p style={{ color: '#f59e0b' }}><TranslatedText text="Forecast will appear when at least seven distinct dates of valid market data are available." /></p>}
          </section>
        </>
      )}
    </div>
  );
}
