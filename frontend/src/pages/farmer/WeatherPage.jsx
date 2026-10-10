
import React, { useState, useEffect, useCallback } from 'react';
import {
  CloudSun,
  ShieldCheck,
  Search,
  RefreshCw,
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
        </>
      )}
    </div>
  );
}
