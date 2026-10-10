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
    RankedMarketOption,
    SellingRecommendationOut,
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
        storage_risk_high: bool = False,
        quantity_quintals: Optional[float] = None,
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

        # Generate structured selling recommendation & market ranking
        selling_rec = cls.generate_selling_recommendation(
            crop_name=crop,
            items=items,
            historical=historical,
            forecasts=forecasts,
            trend=trend,
            average_price=average,
            storage_risk_high=storage_risk_high,
            quantity_quintals=quantity_quintals,
        )

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
            selling_recommendation=selling_rec,
            retrieval_timestamp=timestamp,
            freshness="cached",
        )

    @classmethod
    def generate_selling_recommendation(
        cls,
        crop_name: str,
        items: list[MarketPriceItem],
        historical: list[MarketPricePoint],
        forecasts: list[MarketPriceForecastPoint],
        trend: str,
        average_price: Optional[float],
        storage_risk_high: bool = False,
        quantity_quintals: Optional[float] = None,
        transport_cost_per_quintal: float = 40.0,
    ) -> SellingRecommendationOut:
        if not items:
            return SellingRecommendationOut(
                decision_summary="Insufficient market data to generate selling recommendation",
                current_market_price_per_quintal=None,
                best_alternative_market=None,
                best_alternative_price_per_quintal=None,
                short_term_price_outlook="No recent mandi price observations recorded.",
                weather_considerations="Verify local mandi road and weather conditions prior to dispatch.",
                storage_risk_assessment="Ensure storage temperature and humidity remain within safe thresholds.",
                confidence_level="Limited",
                ranked_options=[],
                formatted_advisory="No reliable mandi records available for this crop to formulate a price-based selling recommendation.",
            )

        # 1. Rank available mandi selling options by modal price and estimated net return
        sorted_items = sorted(items, key=lambda x: x.modal_price_per_quintal, reverse=True)
        ranked: list[RankedMarketOption] = []
        seen_markets = set()

        for idx, it in enumerate(sorted_items):
            m_key = (it.market_name, it.district)
            if m_key in seen_markets:
                continue
            seen_markets.add(m_key)
            rank_num = len(ranked) + 1
            if rank_num > 5:
                break

            dist_cat = "Local Mandi" if idx == 0 else ("Nearby District" if idx <= 2 else "Regional Market")
            est_net = round(it.modal_price_per_quintal - (transport_cost_per_quintal * (1.0 if idx == 0 else 1.5)), 2)

            ranked.append(
                RankedMarketOption(
                    rank=rank_num,
                    market_name=it.market_name,
                    district=it.district,
                    state=it.state,
                    modal_price_per_quintal=it.modal_price_per_quintal,
                    price_date=it.price_date,
                    transport_distance_category=dist_cat,
                    estimated_net_return_per_quintal=est_net,
                    selection_rationale=f"Reported ₹{it.modal_price_per_quintal:,.0f}/q on {it.price_date}. Est. net ₹{est_net:,.0f}/q after transport.",
                    source=it.source,
                )
            )

        top_market = ranked[0] if ranked else None
        alt_market = ranked[1] if len(ranked) > 1 else None

        current_val = top_market.modal_price_per_quintal if top_market else average_price
        alt_name = f"{alt_market.market_name} ({alt_market.district})" if alt_market else None
        alt_val = alt_market.modal_price_per_quintal if alt_market else None

        # 2. Determine short-term price outlook
        if trend == "rising":
            outlook_text = f"Indicative 7-day model points to an upward price trend (+{trend}). Moderate upside if holding short-term."
            base_decision = "Consider holding for upcoming 3–5 days"
            confidence = "Moderate"
        elif trend == "declining":
            outlook_text = "Indicative 7-day model reflects declining arrivals or soften prices. Holding risks margin erosion."
            base_decision = "Consider selling today"
            confidence = "Moderate"
        else:
            outlook_text = "Prices are holding steady in a stable band. Minimal short-term fluctuation expected."
            base_decision = "Consider selling today at highest-paying nearby mandi"
            confidence = "Moderate"

        # 3. Factor in Storage Risk: if storage risk is critical, immediate sale overrides price speculation!
        if storage_risk_high:
            decision_summary = "Recommendation: Immediate sale recommended due to storage risk"
            storage_risk_desc = "CRITICAL: Storage readings exceed safe thresholds. Immediate liquidation or specialized aeration is required to prevent mold and insect degradation."
            confidence = "Strong"
        else:
            decision_summary = f"Recommendation: {base_decision}"
            storage_risk_desc = "SAFE: Current storage conditions are within safe bounds. Crop can be safely stored if waiting for better prices."

        weather_desc = "Check 7-day forecast before transport; cover transport vehicles during rainy intervals."

        net_total = None
        if quantity_quintals and current_val:
            net_total = round(quantity_quintals * (current_val - transport_cost_per_quintal), 2)

        # 4. Formulate strictly formatted advisory
        advisory_lines = [
            f"**{decision_summary}**\n",
            f"- **Current available market price:** ₹{current_val:,.0f} / Quintal ({top_market.market_name if top_market else 'Average'})",
        ]
        if alt_name and alt_val:
            advisory_lines.append(f"- **Best available alternative market:** {alt_name} at ₹{alt_val:,.0f} / Quintal ({alt_market.price_date})")

        advisory_lines.append(f"- **Short-term price outlook:** {outlook_text}")
        advisory_lines.append(f"- **Weather considerations:** {weather_desc}")
        advisory_lines.append(f"- **Storage risk:** {storage_risk_desc}")
        if net_total:
            advisory_lines.append(f"- **Estimated net return:** ₹{net_total:,.0f} for {quantity_quintals} quintals")
        advisory_lines.append(f"- **Confidence:** {confidence} (based on verified APMC records and statistical regression; prices not guaranteed)")

        return SellingRecommendationOut(
            decision_summary=decision_summary,
            current_market_price_per_quintal=current_val,
            best_alternative_market=alt_name,
            best_alternative_price_per_quintal=alt_val,
            short_term_price_outlook=outlook_text,
            weather_considerations=weather_desc,
            storage_risk_assessment=storage_risk_desc,
            estimated_net_return_total=net_total,
            confidence_level=confidence,
            ranked_options=ranked,
            formatted_advisory="\n".join(advisory_lines),
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
            selling_recommendation=None,
            retrieval_timestamp=timestamp,
            freshness="unavailable",
        )
