"""Database-backed agricultural market prices with historical trend and cautious forecasts.

Only imported mandi observations are treated as actual prices. Forecasts are simple
linear-regression estimates over daily market averages and are explicitly labelled.
"""
import datetime
import logging
import math
import re
from collections import defaultdict
from typing import Any, Optional

from app.db.collection_names import MARKET_PRICES_COLLECTION
from app.db.mongo import get_db
from app.schemas.market import (
    MarketPriceForecastPoint,
    MarketPriceItem,
    MarketPricePoint,
    MarketPriceReportOut,
)

logger = logging.getLogger(__name__)


def _text(record: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _price(record: dict, *keys: str) -> Optional[float]:
    for key in keys:
        value = record.get(key)
        if value is None or value == "":
            continue
        try:
            number = float(str(value).replace(",", "").replace("₹", "").strip())
            if math.isfinite(number) and number >= 0:
                return number
        except (TypeError, ValueError):
            continue
    return None


def _date(record: dict) -> Optional[datetime.date]:
    raw = _text(
        record, "price_date", "arrival_date", "arrivalDate", "date", "reported_date"
    )
    if not raw:
        return None
    raw = raw[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y"):
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def _forecast(
    points: list[MarketPricePoint],
) -> tuple[list[MarketPriceForecastPoint], str, str]:
    """Forecast 7 days from at least 7 distinct dates; not a guaranteed price."""
    if len(points) < 7:
        return (
            [],
            "unknown",
            (
                "Forecast unavailable: at least 7 distinct dates of valid market prices are required. "
                "A forecast is an estimate, not a guaranteed future price."
            ),
        )

    # Use elapsed calendar days rather than row positions: market records often skip
    # weekends or dates with no reported arrivals, and those gaps must not be treated
    # as one-day intervals.
    dates = [datetime.date.fromisoformat(point.date) for point in points]
    values = [p.average_modal_price_per_quintal for p in points]
    origin = dates[0]
    xs = [(day - origin).days for day in dates]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(values) / len(values)
    denom = sum((x - x_mean) ** 2 for x in xs)
    slope = (
        sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values)) / denom
        if denom
        else 0.0
    )
    intercept = y_mean - slope * x_mean
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, values)]
    residual_std = math.sqrt(
        sum(r * r for r in residuals) / max(1, len(residuals) - 2)
    )
    baseline = max(1.0, abs(y_mean))
    last_date = dates[-1]
    forecasts = []
    for day in range(1, 8):
        future_x = (last_date - origin).days + day
        prediction = max(0.0, intercept + slope * future_x)
        leverage = (
            math.sqrt(1 + ((future_x - x_mean) ** 2 / denom)) if denom else 1.0
        )
        uncertainty = max(1.96 * residual_std * leverage, baseline * 0.03)
        forecasts.append(
            MarketPriceForecastPoint(
                date=(last_date + datetime.timedelta(days=day)).isoformat(),
                predicted_modal_price_per_quintal=round(prediction, 2),
                lower_estimate=round(max(0.0, prediction - uncertainty), 2),
                upper_estimate=round(prediction + uncertainty, 2),
            )
        )

    first = sum(values[: max(1, len(values) // 3)]) / len(
        values[: max(1, len(values) // 3)]
    )
    last_values = values[-max(1, len(values) // 3) :]
    last = sum(last_values) / len(last_values)
    delta = (last - first) / first if first else 0.0
    trend = (
        "rising" if delta > 0.03 else "declining" if delta < -0.03 else "stable"
    )
    note = (
        "7-day indicative linear-regression estimate based on stored daily averages. "
        "The range is a simple residual-based uncertainty band, not a statistical guarantee. "
        "Prices can change due to weather, arrivals, policy and local demand."
    )
    return forecasts, trend, note


class MarketClient:
    """Read imported mandi observations for the exact farmer-selected crop."""

    @classmethod
    async def get_market_prices(
        cls,
        crop_name: str,
        state: Optional[str] = None,
        district: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> MarketPriceReportOut:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        crop = (crop_name or "").strip()
        if not crop:
            return cls._unavailable(
                "", timestamp, "Select a crop to view market prices."
            )
        db = get_db()
        if db is None:
            return cls._unavailable(
                crop,
                timestamp,
                "No stored market-price records can be queried because market-price storage is unavailable. Please try again later.",
            )

        crop_pattern = {"$regex": f"^{re.escape(crop)}$", "$options": "i"}
        query: dict[str, Any] = {
            "$or": [
                {"crop_name": crop_pattern},
                {"crop": crop_pattern},
                {"commodity": crop_pattern},
                {"commodity_name": crop_pattern},
            ]
        }
        if state and state.strip():
            query["state"] = {
                "$regex": f"^{re.escape(state.strip())}$",
                "$options": "i",
            }
        if district and district.strip():
            query["district"] = {
                "$regex": f"^{re.escape(district.strip())}$",
                "$options": "i",
            }

        try:
            collection = db[MARKET_PRICES_COLLECTION]
            records = list(
                collection.find(query, {"_id": 0})
                .sort(
                    [
                        ("price_date", -1),
                        ("arrival_date", -1),
                        ("date", -1),
                    ]
                )
                .limit(5000)
            )
        except Exception:
            logger.exception("Failed querying stored market prices")
            return cls._unavailable(
                crop,
                timestamp,
                "Could not read market-price records from the database.",
            )

        valid: list[tuple[dict, float]] = []
        daily: dict[datetime.date, list[float]] = defaultdict(list)
        for record in records:
            modal = _price(
                record,
                "modal_price_per_quintal",
                "modal_price",
                "modalPrice",
                "modal",
            )
            if modal is None or modal <= 0:
                continue
            valid.append((record, modal))
            day = _date(record)
            if day:
                daily[day].append(modal)

        if not valid:
            location = ", ".join(part for part in (district, state) if part)
            message = f"No stored market-price records found for {crop}"
            if location:
                message += f" in {location}"
            return cls._unavailable(
                crop,
                timestamp,
                message + ". Import actual mandi records and try again.",
            )

        # Daily averages combine available market observations; no missing dates are fabricated.
        historical = [
            MarketPricePoint(
                date=day.isoformat(),
                average_modal_price_per_quintal=round(
                    sum(prices) / len(prices), 2
                ),
                observations=len(prices),
            )
            for day, prices in sorted(daily.items())
        ]
        forecasts, trend, forecast_note = _forecast(historical)
        valid.sort(
            key=lambda pair: _date(pair[0]) or datetime.date.min, reverse=True
        )
        page = valid[max(0, skip) : max(0, skip) + min(max(1, limit), 500)]
        items = []
        for record, modal in page:
            minimum = _price(
                record,
                "min_price_per_quintal",
                "min_price",
                "minPrice",
                "minimum_price",
            )
            maximum = _price(
                record,
                "max_price_per_quintal",
                "max_price",
                "maxPrice",
                "maximum_price",
            )
            items.append(
                MarketPriceItem(
                    crop_name=_text(
                        record,
                        "crop_name",
                        "commodity",
                        "commodity_name",
                        default=crop,
                    ),
                    variety=_text(
                        record, "variety", "variety_name", default="Not specified"
                    ),
                    market_name=_text(
                        record,
                        "market_name",
                        "market",
                        "apmc",
                        default="Market not specified",
                    ),
                    district=_text(
                        record, "district", default=district or "Not specified"
                    ),
                    state=_text(record, "state", default=state or "Not specified"),
                    modal_price_per_quintal=modal,
                    min_price_per_quintal=(
                        minimum if minimum is not None else modal
                    ),
                    max_price_per_quintal=(
                        maximum if maximum is not None else modal
                    ),
                    price_date=_text(
                        record,
                        "price_date",
                        "arrival_date",
                        "arrivalDate",
                        "date",
                        "reported_date",
                        default="Date not supplied",
                    ),
                    source=_text(
                        record, "source", default="Imported mandi dataset"
                    ),
                )
            )
        average = (
            round(sum(item.modal_price_per_quintal for item in items) / len(items), 2)
            if items
            else None
        )
        latest_date = historical[-1].date if historical else "unknown"
        return MarketPriceReportOut(
            crop_name=crop,
            latest_prices=items,
            historical_prices=historical,
            forecast_prices=forecasts,
            forecast_note=forecast_note,
            average_modal_price=average,
            price_trend=trend,
            recommendation=(
                f"Showing stored mandi observations for {crop}. Latest dated history: {latest_date}. "
                "Compare the market and report date before deciding when to sell."
            ),
            retrieval_timestamp=timestamp,
            freshness="cached",
        )

    @staticmethod
    def _unavailable(
        crop_name: str, timestamp: str, message: str
    ) -> MarketPriceReportOut:
        return MarketPriceReportOut(
            crop_name=crop_name,
            latest_prices=[],
            historical_prices=[],
            forecast_prices=[],
            forecast_note="Forecast unavailable because usable historical market data is missing.",
            average_modal_price=None,
            price_trend="unknown",
            recommendation=message,
            retrieval_timestamp=timestamp,
            freshness="unavailable",
        )
