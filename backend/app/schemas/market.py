"""Market Price Schemas."""

from typing import Optional
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
    latest_prices: list[MarketPriceItem] = Field(default_factory=list)
    average_modal_price: float
    price_trend: str  # rising, stable, declining
    recommendation: str
    retrieval_timestamp: str
    freshness: str  # live, cached, fallback
