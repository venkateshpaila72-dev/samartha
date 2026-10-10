"""Market Price Schemas."""

from typing import Optional, List
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


class MarketPriceReportOut(BaseModel):
    crop_name: str
    latest_prices: List[MarketPriceItem] = Field(default_factory=list)
    average_modal_price: Optional[float] = None
    price_trend: str = "unknown"  # rising, stable, declining, unknown
    recommendation: str
    retrieval_timestamp: str
    freshness: str  # live, cached, reference_sample, unavailable
