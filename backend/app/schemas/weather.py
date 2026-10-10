"""Weather Forecast Schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class WeatherForecastItem(BaseModel):
    timestamp: str
    temperature_c: float
    humidity_percent: float
    rainfall_probability_percent: float
    weather_condition: str
    wind_speed_kmh: float


class WeatherReportOut(BaseModel):
    location: str
    provider: str
    retrieval_timestamp: str
    freshness_status: str  # live, cached, stale
    current_temperature_c: float
    current_humidity_percent: float
    weather_condition: str
    forecast: list[WeatherForecastItem] = Field(default_factory=list)
    storage_impact_summary: str
