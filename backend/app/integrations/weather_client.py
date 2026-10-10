"""Weather Client for FarmShield.
Integrates external weather forecasts and determines ambient storage impact.
"""

import datetime
from typing import Optional
import httpx

from app.core.config import settings
from app.schemas.weather import WeatherForecastItem, WeatherReportOut


class WeatherClient:
    @classmethod
    async def get_weather(cls, location: str = "New Delhi, IN") -> WeatherReportOut:
        api_key = settings.WEATHER_API_KEY.strip()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if api_key and not api_key.startswith("your_"):
            try:
                url = f"{settings.WEATHER_API_BASE_URL}/forecast"
                params = {"q": location, "appid": api_key, "units": "metric"}
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        current_item = data["list"][0]
                        forecast_items = []
                        for item in data["list"][:6]:
                            forecast_items.append(
                                WeatherForecastItem(
                                    timestamp=item["dt_txt"],
                                    temperature_c=item["main"]["temp"],
                                    humidity_percent=item["main"]["humidity"],
                                    rainfall_probability_percent=item.get("pop", 0.0) * 100,
                                    weather_condition=item["weather"][0]["main"],
                                    wind_speed_kmh=item["wind"]["speed"] * 3.6,
                                )
                            )

                        impact = "Ambient conditions are moderate. Standard ventilation procedures apply."
                        if current_item["main"]["humidity"] > 75:
                            impact = "High outdoor humidity detected. Keep storage ventilators sealed to avoid damp air intake."

                        return WeatherReportOut(
                            location=location,
                            provider="OpenWeatherMap (Live)",
                            retrieval_timestamp=now_iso,
                            freshness_status="live",
                            current_temperature_c=current_item["main"]["temp"],
                            current_humidity_percent=current_item["main"]["humidity"],
                            weather_condition=current_item["weather"][0]["description"].title(),
                            forecast=forecast_items,
                            storage_impact_summary=impact,
                        )
            except Exception:
                pass

        # Fallback realistic forecast with disclosure
        forecast = [
            WeatherForecastItem(
                timestamp="Today 12:00 PM",
                temperature_c=28.5,
                humidity_percent=58.0,
                rainfall_probability_percent=10.0,
                weather_condition="Clear Sky",
                wind_speed_kmh=12.0,
            ),
            WeatherForecastItem(
                timestamp="Today 06:00 PM",
                temperature_c=25.0,
                humidity_percent=65.0,
                rainfall_probability_percent=15.0,
                weather_condition="Partly Cloudy",
                wind_speed_kmh=9.0,
            ),
            WeatherForecastItem(
                timestamp="Tomorrow 06:00 AM",
                temperature_c=20.0,
                humidity_percent=72.0,
                rainfall_probability_percent=5.0,
                weather_condition="Clear Sky",
                wind_speed_kmh=6.0,
            ),
            WeatherForecastItem(
                timestamp="Tomorrow 12:00 PM",
                temperature_c=29.0,
                humidity_percent=54.0,
                rainfall_probability_percent=10.0,
                weather_condition="Sunny",
                wind_speed_kmh=11.0,
            ),
        ]

        return WeatherReportOut(
            location=location,
            provider="AgriWeather Simulated Service (API Key Pending)",
            retrieval_timestamp=now_iso,
            freshness_status="fallback",
            current_temperature_c=27.5,
            current_humidity_percent=60.0,
            weather_condition="Partly Cloudy",
            forecast=forecast,
            storage_impact_summary="Favorable dry weather for afternoon grain aeration. Keep storage ventilators closed during night and early morning hours when RH rises.",
        )
