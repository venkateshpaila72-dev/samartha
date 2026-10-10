"""Market-price response schemas, including historical series and transparent forecasts."""

from typing import List, Optional
from pydantic import BaseModel, Field


class MarketPriceItem(BaseModel):
    crop_name: str
    variety: Optional[str] = None
    market_name: str
    district: str
    state: str
    modal_price_per_quintal: float
    min_price_per_quintal: float
    max_price_per_quintal: float
    price_date: str
    source: str


class MarketPricePoint(BaseModel):
    date: str
    average_modal_price_per_quintal: float
    observations: int = 1


class MarketPriceForecastPoint(BaseModel):
    date: str
    predicted_modal_price_per_quintal: float
    lower_estimate: float
    upper_estimate: float


class RankedMarketOption(BaseModel):
    rank: int
    market_name: str
    district: str
    state: str
    modal_price_per_quintal: float
    price_date: str
    transport_distance_category: str  # Local, Nearby District, Regional
    estimated_net_return_per_quintal: Optional[float] = None
    selection_rationale: str
    source: str


class SellingRecommendationOut(BaseModel):
    decision_summary: str  # Consider selling today, Hold for better window, Immediate sale due to storage risk
    current_market_price_per_quintal: Optional[float] = None
    best_alternative_market: Optional[str] = None
    best_alternative_price_per_quintal: Optional[float] = None
    short_term_price_outlook: str
    weather_considerations: str
    storage_risk_assessment: str
    estimated_net_return_total: Optional[float] = None
    confidence_level: str  # Strong, Moderate, Limited
    ranked_options: list[RankedMarketOption] = Field(default_factory=list)
    formatted_advisory: str


class MarketPriceReportOut(BaseModel):
    crop_name: str
    latest_prices: List[MarketPriceItem] = Field(default_factory=list)
    historical_prices: List[MarketPricePoint] = Field(default_factory=list)
    forecast_prices: List[MarketPriceForecastPoint] = Field(default_factory=list)
    forecast_note: str = "Forecast is unavailable until sufficient historical records exist."
    average_modal_price: Optional[float] = None
    price_trend: str = "unknown"
    recommendation: str
    selling_recommendation: Optional[SellingRecommendationOut] = None
    retrieval_timestamp: str
    freshness: str
