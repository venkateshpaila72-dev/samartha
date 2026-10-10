
import React, { useState, useEffect, useCallback } from 'react';
import {
  CloudSun,
  ShieldCheck,
  Search,
  RefreshCw,
  Calendar,
  Sun,
  Droplets,
  Wind,
  AlertTriangle,
  Info,
  Sprout,
  Compass,
} from 'lucide-react';

import { weatherService } from '../../services/monitoringService';
import { useLanguage } from '../../context/LanguageContext';

export default function WeatherPage({ activeBatch }) {
  const {
    currentLang,
    translateText,
    t,
    isTranslating,
  } = useLanguage();

  const [weather, setWeather] = useState(null);
  const [translatedWeather, setTranslatedWeather] = useState(null);
  const [locationInput, setLocationInput] = useState('New Delhi, IN');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchWeather = useCallback(async (loc = null) => {
    setLoading(true);
    setError('');

    try {
      const data = loc
        ? await weatherService.getWeather(loc)
        : activeBatch
          ? await weatherService.getBatchWeather(activeBatch.batch_id)
          : await weatherService.getWeather('New Delhi, IN');

      setWeather(data);
    } catch (err) {
      console.error('Unable to load weather:', err);
      setError(t('error'));
      setWeather(null);
      setTranslatedWeather(null);
    } finally {
      setLoading(false);
    }
  }, [activeBatch, t]);

  useEffect(() => {
    fetchWeather();
  }, [fetchWeather]);

  useEffect(() => {
    let cancelled = false;

    async function translateWeatherData() {
      if (!weather) {
        setTranslatedWeather(null);
        return;
      }

      // Keep numbers, measurements, dates, and identifiers unchanged.
      // Translate only user-facing descriptions.
      const translateDescription = async (value) => {
        if (typeof value !== 'string' || !value.trim()) {
          return value;
        }

        return translateText(value, {
          sourceLanguage: 'en',
          targetLanguage: currentLang,
        });
      };

      try {
        const translated = {
          ...weather,

          weather_condition: await translateDescription(
            weather.weather_condition,
          ),

          storage_impact_summary: await translateDescription(
            weather.storage_impact_summary,
          ),

          forecast: await Promise.all(
            (weather.forecast || []).map(async (forecastItem) => ({
              ...forecastItem,
              weather_condition: await translateDescription(
                forecastItem.weather_condition,
              ),
            })),
          ),
        };

        if (!cancelled) {
          setTranslatedWeather(translated);
        }
      } catch (err) {
        console.error('Weather translation failed:', err);

        if (!cancelled) {
          setTranslatedWeather(weather);
        }
      }
    }

    translateWeatherData();

    return () => {
      cancelled = true;
    };
  }, [weather, currentLang, translateText]);

  const displayWeather = translatedWeather || weather;

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';

    // Keep the original timestamp if it cannot be parsed.
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
      return timestamp;
    }

    try {
      return new Intl.DateTimeFormat(currentLang, {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      }).format(date);
    } catch {
      return timestamp;
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        position: 'relative',
      }}
    >
      {/* Page header */}
      <div
        className="glass-panel"
        style={{
          padding: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <span className="badge badge-info">
            {t('workflow_weather')}
          </span>

          <h1
            style={{
              fontSize: '1.8rem',
              marginTop: '8px',
            }}
          >
            {t('weather_title')}
          </h1>

          <p
            style={{
              color: '#94a3b8',
              fontSize: '0.9rem',
              marginTop: '8px',
              maxWidth: '650px',
            }}
          >
            {t('weather_subtitle')}
          </p>
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            fetchWeather(locationInput.trim());
          }}
          style={{
            display: 'flex',
            gap: '10px',
            flexWrap: 'wrap',
          }}
        >
          <input
            type="text"
            className="input-field"
            value={locationInput}
            onChange={(event) => setLocationInput(event.target.value)}
            placeholder={t('search_location')}
            aria-label={t('search_location')}
            style={{ width: '220px' }}
          />

          <button
            type="submit"
            className="btn-primary"
            disabled={loading || !locationInput.trim()}
          >
            <Search size={16} style={{ marginRight: '6px' }} />
            {t('search')}
          </button>

          <button
            type="button"
            className="btn-secondary"
            onClick={() => fetchWeather()}
            disabled={loading}
            aria-label={t('refresh')}
            title={t('refresh')}
          >
            <RefreshCw
              size={16}
              className={loading ? 'weather-refresh-spin' : ''}
            />
          </button>
        </form>
      </div>

      {/* Loading state */}
      {loading && (
        <div
          className="glass-panel"
          role="status"
          aria-live="polite"
          style={{
            padding: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            color: '#94a3b8',
          }}
        >
          <span className="translation-spinner" />
          <span>{t('loading_data')}</span>
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div
          className="glass-panel"
          role="alert"
          style={{
            padding: '20px',
            color: '#fca5a5',
          }}
        >
          <p>{error}</p>
          <button
            type="button"
            className="btn-primary"
            onClick={() => fetchWeather()}
            style={{ marginTop: '12px' }}
          >
            {t('try_again')}
          </button>
        </div>
      )}

      {/* Translation indicator */}
      {!loading && weather && isTranslating && (
        <div
          className="translation-progress-inline"
          role="status"
          aria-live="polite"
        >
          <span className="translation-spinner" />
          <span>{t('translating')}</span>
        </div>
      )}

      {/* Weather content */}
      {!loading && displayWeather && (
        <>
          {/* Current weather and storage impact */}
          <div
            className="glass-panel glow-border"
            style={{
              padding: '30px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '24px',
            }}
          >
            <div>
              <span className="badge badge-verified">
                {displayWeather.location}
                {displayWeather.provider
                  ? ` • ${displayWeather.provider}`
                  : ''}
              </span>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '20px',
                  marginTop: '16px',
                }}
              >
                <CloudSun size={64} color="#60a5fa" />

                <div>
                  <div
                    style={{
                      fontSize: '3.2rem',
                      fontWeight: '800',
                      lineHeight: 1,
                    }}
                  >
                    {displayWeather.current_temperature_c ?? '--'}°C
                  </div>

                  <div
                    style={{
                      fontSize: '1.1rem',
                      color: '#94a3b8',
                      marginTop: '8px',
                    }}
                  >
                    {displayWeather.weather_condition || ''}
                  </div>
                </div>
              </div>
            </div>

            <div
              style={{
                background: 'rgba(15, 23, 42, 0.7)',
                padding: '20px 24px',
                borderRadius: '14px',
                maxWidth: '480px',
                flex: '1 1 280px',
              }}
            >
              <div
                style={{
                  fontWeight: '700',
                  color: '#10b981',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '10px',
                }}
              >
                <ShieldCheck size={18} />
                {t('storage_impact')}
              </div>

              <p
                style={{
                  fontSize: '0.92rem',
                  color: '#cbd5e1',
                  lineHeight: 1.6,
                }}
              >
                {displayWeather.storage_impact_summary ||
                  t('no_data')}
              </p>
            </div>
          </div>

          {/* Forecast */}
          <h3 style={{ fontSize: '1.3rem' }}>
            {t('next_forecast')}
          </h3>

          {displayWeather.forecast?.length > 0 ? (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns:
                  'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '16px',
              }}
            >
              {displayWeather.forecast.map((forecastItem, index) => (
                <div
                  key={forecastItem.timestamp || index}
                  className="glass-panel"
                  style={{
                    padding: '18px',
                    textAlign: 'center',
                  }}
                >
                  <div
                    style={{
                      fontSize: '0.82rem',
                      color: '#94a3b8',
                      marginBottom: '8px',
                    }}
                  >
                    {formatTimestamp(forecastItem.timestamp)}
                  </div>

                  <CloudSun
                    size={32}
                    color="#60a5fa"
                    style={{ margin: '0 auto 8px' }}
                  />

                  <div
                    style={{
                      fontSize: '1.4rem',
                      fontWeight: '700',
                    }}
                  >
                    {forecastItem.temperature_c ?? '--'}°C
                  </div>

                  <div
                    style={{
                      fontSize: '0.85rem',
                      color: '#cbd5e1',
                      marginTop: '6px',
                    }}
                  >
                    {forecastItem.weather_condition || ''}
                  </div>

                  <div
                    style={{
                      fontSize: '0.78rem',
                      color: '#94a3b8',
                      marginTop: '10px',
                    }}
                  >
                    💧 {t('humidity')}: {forecastItem.humidity_percent ?? '--'}%
                    {' • '}
                    💨 {forecastItem.wind_speed_kmh ?? '--'} km/h
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="glass-panel" style={{ padding: '24px' }}>
              {t('no_data')}
            </div>
          )}

          {/* 7-Day Daily Forecast & Agronomic Advisory */}
          {displayWeather.seven_day_forecast?.length > 0 && (
            <div style={{ marginTop: '30px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '1.35rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Calendar size={20} color="#38bdf8" /> 7-Day Daily Forecast & Crop Operations Advisory
                  </h3>
                  <p style={{ color: '#94a3b8', fontSize: '0.86rem', marginTop: '4px' }}>
                    Verified daily agronomic guidance for harvesting, solar drying, irrigation, and granary ventilation.
                  </p>
                </div>
                <span className="badge badge-verified">LIVE 7-DAY MODEL</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
                {displayWeather.seven_day_forecast.map((item, idx) => {
                  const isRainy = (item.precipitation_probability_percent || 0) >= 35.0 || (item.precipitation_sum_mm || 0) >= 2.0;
                  return (
                    <div
                      key={item.date || idx}
                      className="glass-panel"
                      style={{
                        padding: '20px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px',
                        borderLeft: isRainy ? '4px solid #f59e0b' : '4px solid #10b981',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ fontWeight: '700', fontSize: '1.05rem', color: '#f8fafc' }}>
                            {item.day_name}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                            {item.date}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <span style={{ fontSize: '1.25rem', fontWeight: '800', color: '#38bdf8' }}>
                            {item.temp_max_c}°
                          </span>
                          <span style={{ fontSize: '0.9rem', color: '#94a3b8', marginLeft: '4px' }}>
                            / {item.temp_min_c}°C
                          </span>
                          <div style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>
                            {item.weather_condition}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '14px', fontSize: '0.8rem', color: '#cbd5e1', background: 'rgba(255, 255, 255, 0.04)', padding: '8px 12px', borderRadius: '8px' }}>
                        <div>
                          💧 Rain Chance: <strong style={{ color: isRainy ? '#f59e0b' : '#34d399' }}>{item.precipitation_probability_percent}%</strong> ({item.precipitation_sum_mm}mm)
                        </div>
                        <div>
                          💨 Wind: <strong>{item.wind_speed_max_kmh} km/h</strong>
                        </div>
                      </div>

                      {/* Practical Farming Operational Guidance */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.82rem', lineHeight: 1.4 }}>
                        <div style={{ color: '#cbd5e1' }}>
                          🌾 <strong>Harvesting:</strong> {item.harvest_recommendation}
                        </div>
                        <div style={{ color: '#cbd5e1' }}>
                          ☀️ <strong>Solar Drying:</strong> {item.drying_recommendation}
                        </div>
                        <div style={{ color: '#cbd5e1' }}>
                          💧 <strong>Irrigation:</strong> {item.irrigation_recommendation}
                        </div>
                        <div style={{ color: '#cbd5e1' }}>
                          💨 <strong>Ventilation:</strong> {item.ventilation_recommendation}
                        </div>
                        <div style={{ color: '#94a3b8', fontSize: '0.78rem' }}>
                          🐛 <strong>Pest/Mould Risk:</strong> {item.pest_disease_risk}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 30-Day Seasonal Agro-Climatic Outlook */}
          {displayWeather.thirty_day_outlook && (
            <div style={{ marginTop: '36px' }}>
              <div className="glass-panel" style={{ padding: '24px', borderLeft: '4px solid #38bdf8' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '14px' }}>
                  <div>
                    <span className="badge badge-info" style={{ marginBottom: '6px' }}>
                      <Compass size={12} /> Extended Climate Model
                    </span>
                    <h3 style={{ fontSize: '1.35rem', color: '#f8fafc' }}>
                      {displayWeather.thirty_day_outlook.coverage}
                    </h3>
                  </div>
                  <div style={{
                    fontSize: '0.76rem',
                    color: '#fbbf24',
                    background: 'rgba(245, 158, 11, 0.15)',
                    padding: '6px 12px',
                    borderRadius: '8px',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    maxWidth: '480px'
                  }}>
                    ⚠️ <strong>Uncertainty Notice:</strong> {displayWeather.thirty_day_outlook.uncertainty_level}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '20px' }}>
                  <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '10px' }}>
                    <div style={{ color: '#38bdf8', fontWeight: '600', fontSize: '0.88rem', marginBottom: '4px' }}>
                      🌡️ Temperature Pattern
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                      {displayWeather.thirty_day_outlook.temperature_outlook_summary}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '10px' }}>
                    <div style={{ color: '#34d399', fontWeight: '600', fontSize: '0.88rem', marginBottom: '4px' }}>
                      🌧️ Precipitation Outlook
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                      {displayWeather.thirty_day_outlook.precipitation_outlook_summary}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '10px' }}>
                    <div style={{ color: '#f59e0b', fontWeight: '600', fontSize: '0.88rem', marginBottom: '4px' }}>
                      💡 Strategic Advisory
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                      {displayWeather.thirty_day_outlook.seasonal_advisory}
                    </div>
                  </div>
                </div>

                {/* 10-Day Dekad Periods */}
                <h4 style={{ fontSize: '1.05rem', color: '#f8fafc', marginBottom: '12px' }}>
                  Dekad Progression (10-Day Outlook Phases)
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
                  {displayWeather.thirty_day_outlook.periods?.map((p, pIdx) => (
                    <div key={pIdx} style={{
                      background: 'rgba(15, 23, 42, 0.7)',
                      padding: '16px',
                      borderRadius: '10px',
                      border: '1px solid rgba(255, 255, 255, 0.06)'
                    }}>
                      <div style={{ fontWeight: '700', color: '#38bdf8', fontSize: '0.92rem' }}>
                        {p.period_name}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginBottom: '8px' }}>
                        {p.date_range}
                      </div>
                      <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginBottom: '6px' }}>
                        Target Temp: <strong>{p.expected_temp_range_c}</strong>
                      </div>
                      <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginBottom: '8px' }}>
                        Rainfall: <strong>{p.expected_rainfall}</strong>
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#94a3b8', borderTop: '1px solid rgba(255, 255, 255, 0.05)', paddingTop: '6px', lineHeight: 1.4 }}>
                        {p.farming_advisory}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}

    </div>
  );
}
