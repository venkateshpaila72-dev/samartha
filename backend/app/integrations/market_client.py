<<<<<<< HEAD

"""AGMARKNET 2.0 client for FarmShield market prices."""
=======
"""Database-backed agricultural market prices with historical trend and cautious forecasts.
>>>>>>> e593938731cffe4d25d52e76603c5c3a00419be2

Only imported mandi observations are treated as actual prices. Forecasts are simple
linear-regression estimates over daily market averages and are explicitly labelled.
"""
import datetime
import json
import logging
<<<<<<< HEAD
import os
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.schemas.market import MarketPriceItem, MarketPriceReportOut

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.agmarknet.gov.in/v1"
PRICE_ENDPOINT = "/prices-and-arrivals/date-wise/specific-commodity"


def _load_json_env(name: str) -> Dict[str, Any]:
    """Load an optional JSON object from an environment variable."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in environment variable %s", name)
        return {}


def _normalise_name(value: Optional[str]) -> str:
    return " ".join((value or "").strip().lower().replace("_", " ").split())


def _first(record: dict, *keys: str, default=None):
    """Return the first non-empty field from a record."""
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return default


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("₹", "").strip())
    except (TypeError, ValueError):
        return None


def _extract_records(payload: Any) -> List[dict]:
    """Handle common list and nested-object response formats."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    for key in ("data", "records", "results", "items", "content"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _extract_records(value)
            if nested:
                return nested

    # Some APIs return one record directly.
    if any(
        key in payload
        for key in ("modal_price", "modalPrice", "commodity", "commodityName")
    ):
        return [payload]

    return []


class MarketClient:
    """Fetches daily mandi prices from AGMARKNET 2.0."""

    @classmethod
    async def get_market_prices(
        cls,
        crop_name: str,
        state: Optional[str] = None,
        district: Optional[str] = None,
    ) -> MarketPriceReportOut:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        crop = (crop_name or "").strip()

        if not crop:
            return cls._unavailable("", now_iso, "Please provide a crop name.")

        base_url = (
            os.getenv("AGMARKNET_BASE_URL", "").strip()
            or getattr(settings, "AGMARKNET_BASE_URL", "").strip()
            or DEFAULT_BASE_URL
        ).rstrip("/")

        # The documented endpoint accepts IDs, not arbitrary crop/state names.
        # Configure these mappings using the IDs provided by AGMARKNET.
        commodity_ids = _load_json_env("AGMARKNET_COMMODITY_IDS")
        state_ids = _load_json_env("AGMARKNET_STATE_IDS")
        district_ids = _load_json_env("AGMARKNET_DISTRICT_IDS")

        commodity_id = commodity_ids.get(crop)
        if commodity_id is None:
            commodity_id = commodity_ids.get(_normalise_name(crop))

        state_id = None
        if state:
            state_id = state_ids.get(state) or state_ids.get(_normalise_name(state))

        district_id = None
        if district:
            district_id = (
                district_ids.get(f"{state or ''}|{district}")
                or district_ids.get(_normalise_name(district))
            )

        if commodity_id is None:
            return cls._unavailable(
                crop,
                now_iso,
                (
                    f"AGMARKNET commodity ID is not configured for '{crop}'. "
                    "Add it to AGMARKNET_COMMODITY_IDS using the official commodity ID."
                ),
            )

        if state and state_id is None:
            return cls._unavailable(
                crop,
                now_iso,
                (
                    f"AGMARKNET state ID is not configured for '{state}'. "
                    "Add it to AGMARKNET_STATE_IDS using the official state ID."
                ),
            )

        # This endpoint requires a year/month and the relevant IDs.
        today = datetime.date.today()
        params: Dict[str, Any] = {
            "year": today.year,
            "month": today.month,
            "commodityId": commodity_id,
        }
        if state_id is not None:
            params["stateId"] = state_id
        if district_id is not None:
            params["districtId"] = district_id

        headers = {
            "Accept": "application/json",
            "User-Agent": "FarmShield/1.0",
        }

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(20.0, connect=8.0),
                follow_redirects=True,
                headers=headers,
            ) as client:
                response = await client.get(
                    f"{base_url}{PRICE_ENDPOINT}",
                    params=params,
                )

            if response.status_code != 200:
                logger.warning(
                    "AGMARKNET returned HTTP %s: %s",
                    response.status_code,
                    response.text[:500],
                )
                return cls._unavailable(
                    crop,
                    now_iso,
                    f"AGMARKNET could not provide prices (HTTP {response.status_code}).",
                )

            try:
                payload = response.json()
            except ValueError:
                logger.warning("AGMARKNET returned non-JSON data")
                return cls._unavailable(
                    crop, now_iso, "AGMARKNET returned an invalid response."
                )

            records = _extract_records(payload)
            items: List[MarketPriceItem] = []

            for record in records:
                modal = _number(
                    _first(record, "modal_price", "modalPrice", "modal", "modal_price_rs")
                )
                minimum = _number(
                    _first(record, "min_price", "minPrice", "minimum_price", "min")
                )
                maximum = _number(
                    _first(record, "max_price", "maxPrice", "maximum_price", "max")
                )

                # A record without a modal price is not useful as a price listing.
                if modal is None or modal <= 0:
                    continue

                record_crop = str(
                    _first(record, "commodity", "commodityName", "crop", default=crop)
                )
                market_name = str(
                    _first(record, "market", "marketName", "apmc", default="Mandi")
                )
                record_state = str(
                    _first(record, "state", "stateName", default=state or "India")
                )
                record_district = str(
                    _first(record, "district", "districtName", default=district or "N/A")
                )

                items.append(
                    MarketPriceItem(
                        crop_name=record_crop,
                        variety=str(
                            _first(record, "variety", "varietyName", default="Standard")
                        ),
                        market_name=market_name,
                        district=record_district,
                        state=record_state,
                        modal_price_per_quintal=modal,
                        min_price_per_quintal=minimum if minimum is not None else modal,
                        max_price_per_quintal=maximum if maximum is not None else modal,
                        price_date=str(
                            _first(
                                record,
                                "arrival_date",
                                "arrivalDate",
                                "date",
                                "price_date",
                                default="Date not supplied",
                            )
                        ),
                        source="AGMARKNET 2.0",
                    )
                )

            if not items:
                return cls._unavailable(
                    crop,
                    now_iso,
                    (
                        f"No matching AGMARKNET price records were returned for {crop}"
                        + (f" in {district}, {state}" if district and state
                           else f" in {state}" if state else "")
                        + ". Try another date or nearby mandi."
                    ),
                )

            average = round(
                sum(item.modal_price_per_quintal for item in items) / len(items), 2
            )

            return MarketPriceReportOut(
                crop_name=crop,
                latest_prices=items,
                average_modal_price=average,
                price_trend="unknown",
                recommendation=(
                    f"AGMARKNET returned {len(items)} daily price record(s) for {crop}. "
                    "Compare the modal price, date, and nearby markets before selling."
                ),
                retrieval_timestamp=now_iso,
                freshness="live",
            )

        except httpx.TimeoutException:
            logger.warning("AGMARKNET request timed out")
            return cls._unavailable(
                crop, now_iso, "AGMARKNET request timed out. Please try again."
            )
        except httpx.HTTPError:
            logger.exception("AGMARKNET HTTP request failed")
            return cls._unavailable(
                crop, now_iso, "Could not connect to AGMARKNET. Please try again later."
            )
        except Exception:
            logger.exception("Unexpected error while processing AGMARKNET response")
            return cls._unavailable(
                crop, now_iso, "An unexpected error occurred while retrieving prices."
            )

    @staticmethod
    def _unavailable(
        crop_name: str, timestamp: str, message: str
    ) -> MarketPriceReportOut:
        return MarketPriceReportOut(
            crop_name=crop_name,
            latest_prices=[],
            average_modal_price=None,
            price_trend="unknown",
            recommendation=message,
            retrieval_timestamp=timestamp,
            freshness="unavailable",
=======
import math
import re
from collections import defaultdict
from typing import Any, Optional

from app.db.collection_names import MARKET_PRICES_COLLECTION
from app.db.mongo import get_db
from app.schemas.market import (
    MarketPriceForecastPoint, MarketPriceItem, MarketPricePoint, MarketPriceReportOut,
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
    raw = _text(record, "price_date", "arrival_date", "arrivalDate", "date", "reported_date")
    if not raw:
        return None
    raw = raw[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y"):
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def _forecast(points: list[MarketPricePoint]) -> tuple[list[MarketPriceForecastPoint], str, str]:
    """Forecast 7 days from at least 7 distinct dates; not a guaranteed price."""
    if len(points) < 7:
        return [], "unknown", (
            "Forecast unavailable: at least 7 distinct dates of valid market prices are required. "
            "A forecast is an estimate, not a guaranteed future price."
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
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values)) / denom if denom else 0.0
    intercept = y_mean - slope * x_mean
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, values)]
    residual_std = math.sqrt(sum(r * r for r in residuals) / max(1, len(residuals) - 2))
    baseline = max(1.0, abs(y_mean))
    last_date = dates[-1]
    forecasts = []
    for day in range(1, 8):
        future_x = (last_date - origin).days + day
        prediction = max(0.0, intercept + slope * future_x)
        leverage = math.sqrt(1 + ((future_x - x_mean) ** 2 / denom)) if denom else 1.0
        uncertainty = max(1.96 * residual_std * leverage, baseline * 0.03)
        forecasts.append(MarketPriceForecastPoint(
            date=(last_date + datetime.timedelta(days=day)).isoformat(),
            predicted_modal_price_per_quintal=round(prediction, 2),
            lower_estimate=round(max(0.0, prediction - uncertainty), 2),
            upper_estimate=round(prediction + uncertainty, 2),
        ))

    first = sum(values[:max(1, len(values)//3)]) / len(values[:max(1, len(values)//3)])
    last_values = values[-max(1, len(values)//3):]
    last = sum(last_values) / len(last_values)
    delta = (last - first) / first if first else 0.0
    trend = "rising" if delta > 0.03 else "declining" if delta < -0.03 else "stable"
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
        cls, crop_name: str, state: Optional[str] = None, district: Optional[str] = None,
        limit: int = 50, skip: int = 0,
    ) -> MarketPriceReportOut:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        crop = (crop_name or "").strip()
        if not crop:
            return cls._unavailable("", timestamp, "Select a crop to view market prices.")
        db = get_db()
        if db is None:
            return cls._unavailable(crop, timestamp, "No stored market-price records can be queried because market-price storage is unavailable. Please try again later.")

        crop_pattern = {"$regex": f"^{re.escape(crop)}$", "$options": "i"}
        query: dict[str, Any] = {"$or": [
            {"crop_name": crop_pattern}, {"crop": crop_pattern}, {"commodity": crop_pattern}, {"commodity_name": crop_pattern}
        ]}
        if state and state.strip():
            query["state"] = {"$regex": f"^{re.escape(state.strip())}$", "$options": "i"}
        if district and district.strip():
            query["district"] = {"$regex": f"^{re.escape(district.strip())}$", "$options": "i"}

        try:
            collection = db[MARKET_PRICES_COLLECTION]
            records = list(collection.find(query, {"_id": 0}).sort([("price_date", -1), ("arrival_date", -1), ("date", -1)]).limit(5000))
        except Exception:
            logger.exception("Failed querying stored market prices")
            return cls._unavailable(crop, timestamp, "Could not read market-price records from the database.")

        valid: list[tuple[dict, float]] = []
        daily: dict[datetime.date, list[float]] = defaultdict(list)
        for record in records:
            modal = _price(record, "modal_price_per_quintal", "modal_price", "modalPrice", "modal")
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
            return cls._unavailable(crop, timestamp, message + ". Import actual mandi records and try again.")

        # Daily averages combine available market observations; no missing dates are fabricated.
        historical = [
            MarketPricePoint(date=day.isoformat(),
                average_modal_price_per_quintal=round(sum(prices)/len(prices), 2),
                observations=len(prices))
            for day, prices in sorted(daily.items())
        ]
        forecasts, trend, forecast_note = _forecast(historical)
        valid.sort(key=lambda pair: _date(pair[0]) or datetime.date.min, reverse=True)
        page = valid[max(0, skip):max(0, skip) + min(max(1, limit), 500)]
        items = []
        for record, modal in page:
            minimum = _price(record, "min_price_per_quintal", "min_price", "minPrice", "minimum_price")
            maximum = _price(record, "max_price_per_quintal", "max_price", "maxPrice", "maximum_price")
            items.append(MarketPriceItem(
                crop_name=_text(record, "crop_name", "commodity", "commodity_name", default=crop),
                variety=_text(record, "variety", "variety_name", default="Not specified"),
                market_name=_text(record, "market_name", "market", "apmc", default="Market not specified"),
                district=_text(record, "district", default=district or "Not specified"),
                state=_text(record, "state", default=state or "Not specified"),
                modal_price_per_quintal=modal,
                min_price_per_quintal=minimum if minimum is not None else modal,
                max_price_per_quintal=maximum if maximum is not None else modal,
                price_date=_text(record, "price_date", "arrival_date", "arrivalDate", "date", "reported_date", default="Date not supplied"),
                source=_text(record, "source", default="Imported mandi dataset"),
            ))
        average = round(sum(item.modal_price_per_quintal for item in items) / len(items), 2) if items else None
        latest_date = historical[-1].date if historical else "unknown"
        return MarketPriceReportOut(
            crop_name=crop, latest_prices=items, historical_prices=historical,
            forecast_prices=forecasts, forecast_note=forecast_note, average_modal_price=average,
            price_trend=trend,
            recommendation=(
                f"Showing stored mandi observations for {crop}. Latest dated history: {latest_date}. "
                "Compare the market and report date before deciding when to sell."
            ),
            retrieval_timestamp=timestamp,
            freshness="cached",
        )

    @staticmethod
    def _unavailable(crop_name: str, timestamp: str, message: str) -> MarketPriceReportOut:
        return MarketPriceReportOut(
            crop_name=crop_name, latest_prices=[], historical_prices=[], forecast_prices=[],
            forecast_note="Forecast unavailable because usable historical market data is missing.",
            average_modal_price=None, price_trend="unknown", recommendation=message,
            retrieval_timestamp=timestamp, freshness="unavailable",
>>>>>>> e593938731cffe4d25d52e76603c5c3a00419be2
        )
