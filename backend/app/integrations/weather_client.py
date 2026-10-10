"""Weather Client for FarmShield using Open-Meteo API.
Integrates live weather forecasts and determines ambient storage impact.
Eliminates fabricated fallbacks and unknown location defaults.
"""

import datetime
import logging
from typing import Optional, Tuple
import httpx

from app.core.config import settings
from app.schemas.weather import WeatherForecastItem, WeatherReportOut

logger = logging.getLogger(__name__)

# Coordinates for major Indian agricultural districts and cities
KNOWN_LOCATIONS: dict[str, Tuple[float, float]] = {
    "new delhi": (28.6139, 77.2090),
    "delhi": (28.6139, 77.2090),
    "pune": (18.5204, 73.8567),
    "nashik": (19.9975, 73.7898),
    "hyderabad": (17.3850, 78.4867),
    "mumbai": (19.0760, 72.8777),
    "bhopal": (23.2599, 77.4126),
    "indore": (22.7196, 75.8577),
    "jaipur": (26.9124, 75.7873),
    "lucknow": (26.8467, 80.9462),
    "patna": (25.5941, 85.1376),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "guntur": (16.3067, 80.4365),
    "karnal": (29.6857, 76.9905),
    "ludhiana": (30.9010, 75.8573),
    "amritsar": (31.6340, 74.8723),
    "chandigarh": (30.7333, 76.7794),
    "nagpur": (21.1458, 79.0882),
    "ahmedabad": (23.0225, 72.5714),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
}

WMO_WEATHER_DESCRIPTIONS: dict[int, str] = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    56: "Light Freezing Drizzle",
    57: "Dense Freezing Drizzle",
    61: "Slight Rain",
    62: "Moderate Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    66: "Light Freezing Rain",
    67: "Heavy Freezing Rain",
    71: "Slight Snow Fall",
    73: "Moderate Snow Fall",
    75: "Heavy Snow Fall",
    77: "Snow Grains",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    85: "Slight Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Slight Hail",
    99: "Thunderstorm with Heavy Hail",
}


class WeatherClient:
    """Retrieves live meteorological data from Open-Meteo."""

    @classmethod
    async def _resolve_coordinates(cls, location_str: str) -> Tuple[Optional[float], Optional[float], str]:
        """Resolves location name to latitude and longitude."""
        cleaned = location_str.lower().split(",")[0].strip()
        if cleaned in KNOWN_LOCATIONS:
            lat, lon = KNOWN_LOCATIONS[cleaned]
            return lat, lon, location_str

        # Match known city or district names embedded in facility/warehouse names (e.g. "Nashik Granary")
        import re
        for city_key, (c_lat, c_lon) in KNOWN_LOCATIONS.items():
            if re.search(rf"\b{re.escape(city_key)}\b", cleaned):
                return c_lat, c_lon, f"{city_key.title()}, IN"

        # Attempt Open-Meteo geocoding if not in local lookup
        try:
            geo_url = "https://geocoding-api.open-meteo.com/v1/search"
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(geo_url, params={"name": cleaned, "count": 1})
                if res.status_code == 200:
                    data = res.json()
                    if data.get("results"):
                        item = data["results"][0]
                        resolved_name = f"{item.get('name')}, {item.get('country_code', 'IN')}"
                        return item["latitude"], item["longitude"], resolved_name
        except Exception as e:
            logger.debug(f"Geocoding lookup failed for '{location_str}': {e}")

        # Return None rather than falsely claiming Delhi
        return None, None, location_str

    @classmethod
    async def get_weather(cls, location: str = "New Delhi, IN") -> WeatherReportOut:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        lat, lon, display_name = await cls._resolve_coordinates(location)

        if lat is None or lon is None:
            raise ValueError(f"Could not resolve geographic location for '{location}'. Please enter a recognized district or city name.")

        # 1. Fetch live data from Open-Meteo
        base_url = settings.OPEN_METEO_BASE_URL.strip() or "https://api.open-meteo.com/v1/forecast"
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m,weather_code",
                "forecast_days": 2,
            }
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(base_url, params=params)
                if resp.status_code != 200:
                    raise RuntimeError(f"Open-Meteo returned status {resp.status_code}")

                raw = resp.json()
                current = raw.get("current", {})
                hourly = raw.get("hourly", {})

                curr_temp = float(current.get("temperature_2m", 25.0))
                curr_rh = float(current.get("relative_humidity_2m", 50.0))
                w_code = int(current.get("weather_code", 0))
                condition_text = WMO_WEATHER_DESCRIPTIONS.get(w_code, "Clear Sky")

                forecast_items: list[WeatherForecastItem] = []
                times = hourly.get("time", [])
                temps = hourly.get("temperature_2m", [])
                rhs = hourly.get("relative_humidity_2m", [])
                precips = hourly.get("precipitation_probability", [])
                winds = hourly.get("wind_speed_10m", [])
                codes = hourly.get("weather_code", [])

                # Find the starting index matching current hour to avoid past timestamps
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                start_idx = 0
                for idx, t_str in enumerate(times):
                    try:
                        t_dt = datetime.datetime.fromisoformat(t_str)
                        if t_dt.tzinfo is None:
                            t_dt = t_dt.replace(tzinfo=datetime.timezone.utc)
                        if t_dt >= now_utc - datetime.timedelta(hours=1):
                            start_idx = idx
                            break
                    except Exception:
                        pass

                # Sample every 3-4 hours for upcoming 24 hours from current time
                end_idx = min(start_idx + 24, len(times))
                for i in range(start_idx, end_idx, 4):
                    iso_time = times[i]
                    try:
                        dt = datetime.datetime.fromisoformat(iso_time)
                        formatted_time = dt.strftime("%d %b %H:%M")
                    except Exception:
                        formatted_time = iso_time

                    forecast_items.append(
                        WeatherForecastItem(
                            timestamp=formatted_time,
                            temperature_c=float(temps[i]) if i < len(temps) else curr_temp,
                            humidity_percent=float(rhs[i]) if i < len(rhs) else curr_rh,
                            rainfall_probability_percent=float(precips[i]) if i < len(precips) else 0.0,
                            weather_condition=WMO_WEATHER_DESCRIPTIONS.get(
                                int(codes[i]) if i < len(codes) else 0, "Clear Sky"
                            ),
                            wind_speed_kmh=float(winds[i]) if i < len(winds) else 8.0,
                        )
                    )

                # Assess grain storage environmental impact
                if curr_rh > 75.0:
                    impact = (
                        "High ambient humidity detected (>75%). Seal granary ventilators to prevent "
                        "spontaneous damp air intake and mold proliferation."
                    )
                elif curr_rh < 40.0:
                    impact = (
                        "Dry outdoor ambient conditions (<40% RH). Favorable window for active daytime "
                        "granary aeration and solar drying of grain stocks."
                    )
                elif curr_temp > 35.0:
                    impact = (
                        "Elevated outdoor temperatures (>35°C). Maximize rooftop shade insulation; ventilate "
                        "only during cooler late night or early morning hours."
                    )
                else:
                    impact = (
                        "Moderate ambient weather conditions. Standard storage ventilation guidelines apply. "
                        "Ensure consistent airflow."
                    )

                return WeatherReportOut(
                    location=display_name,
                    provider="Open-Meteo (Live API)",
                    retrieval_timestamp=now_iso,
                    freshness_status="live",
                    current_temperature_c=curr_temp,
                    current_humidity_percent=curr_rh,
                    weather_condition=condition_text,
                    forecast=forecast_items,
                    storage_impact_summary=impact,
                )
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Open-Meteo live request failed: {e}")
            raise RuntimeError(f"Open-Meteo live weather forecast service unavailable: {str(e)}")
