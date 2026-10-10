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


class DailyWeatherForecastItem(BaseModel):
    date: str
    day_name: str
    temp_max_c: float
    temp_min_c: float
    precipitation_sum_mm: float
    precipitation_probability_percent: float
    weather_condition: str
    wind_speed_max_kmh: float
    harvest_recommendation: str
    drying_recommendation: str
    irrigation_recommendation: str
    ventilation_recommendation: str
    pest_disease_risk: str


class ExtendedOutlookPeriod(BaseModel):
    period_name: str  # e.g., "Day 1–10 (Early Outlook)", "Day 11–20", "Day 21–30"
    date_range: str
    expected_temp_range_c: str
    expected_rainfall: str
    farming_advisory: str


class ThirtyDayOutlook(BaseModel):
    coverage: str = "30-Day Extended Agro-Climatic Outlook"
    provider: str = "Open-Meteo & IMD Historical Patterns"
    uncertainty_level: str = "High (Indicative Seasonal Estimate — Not a Daily Guarantee)"
    retrieval_timestamp: str
    temperature_outlook_summary: str
    precipitation_outlook_summary: str
    seasonal_advisory: str
    periods: list[ExtendedOutlookPeriod] = Field(default_factory=list)


class WeatherReportOut(BaseModel):
    location: str
    provider: str
    retrieval_timestamp: str
    freshness_status: str  # live, cached, stale
    current_temperature_c: float
    current_humidity_percent: float
    weather_condition: str
    forecast: list[WeatherForecastItem] = Field(default_factory=list)
    seven_day_forecast: list[DailyWeatherForecastItem] = Field(default_factory=list)
    thirty_day_outlook: Optional[ThirtyDayOutlook] = None
    storage_impact_summary: str
