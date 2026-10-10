"""Database-backed agricultural market prices.

The farmer-facing request reads actual imported AGMARKNET/mandi records from
MongoDB. It intentionally contains no benchmark prices or fabricated fallback
records. AGMARKNET ingestion is a separate sync/import responsibility.
"""

import datetime
import logging
import re
from typing import Any, Optional

from app.db.collection_names import MARKET_PRICES_COLLECTION
from app.db.mongo import get_db
from app.schemas.market import MarketPriceItem, MarketPriceReportOut

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
            if number >= 0:
                return number
        except (TypeError, ValueError):
            continue
    return None


def _normalised_date(record: dict) -> str:
    return _text(
        record,
        "price_date",
        "arrival_date",
        "arrivalDate",
        "date",
        "reported_date",
        default="Date not supplied",
    )


class MarketClient:
    """Read actual imported market-price records from MongoDB."""

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
            return cls._unavailable("", timestamp, "Select a crop to view market prices.")

        db = get_db()
        if db is None:
            return cls._unavailable(
                crop,
                timestamp,
                "Market-price storage is unavailable. Please try again later.",
            )

        # Support common names used by AGMARKNET imports and admin CSV uploads.
        crop_pattern = {"$regex": f"^{re.escape(crop)}$", "$options": "i"}
        query: dict[str, Any] = {
            "$or": [
                {"crop_name": crop_pattern},
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
            total = collection.count_documents(query)
            cursor = (
                collection.find(query, {"_id": 0})
                .sort([("price_date", -1), ("arrival_date", -1), ("date", -1)])
                .skip(max(0, skip))
                .limit(min(max(1, limit), 500))
            )
            records = list(cursor)
        except Exception:
            logger.exception("Failed querying stored market prices")
            return cls._unavailable(
                crop, timestamp, "Could not read market-price records from the database."
            )

        items: list[MarketPriceItem] = []
        for record in records:
            modal = _price(
                record,
                "modal_price_per_quintal",
                "modal_price",
                "modalPrice",
                "modal",
            )
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
            if modal is None or modal <= 0:
                continue

            items.append(
                MarketPriceItem(
                    crop_name=_text(
                        record, "crop_name", "commodity", "commodity_name", default=crop
                    ),
                    variety=_text(record, "variety", "variety_name", default="Not specified"),
                    market_name=_text(
                        record, "market_name", "market", "apmc", default="Market not specified"
                    ),
                    district=_text(record, "district", default=district or "Not specified"),
                    state=_text(record, "state", default=state or "Not specified"),
                    modal_price_per_quintal=modal,
                    min_price_per_quintal=minimum if minimum is not None else modal,
                    max_price_per_quintal=maximum if maximum is not None else modal,
                    price_date=_normalised_date(record),
                    source=_text(record, "source", default="Imported mandi dataset"),
                )
            )

        if not items:
            location = ", ".join(part for part in (district, state) if part)
            message = f"No stored market-price records found for {crop}"
            if location:
                message += f" in {location}"
            message += ". Import the latest mandi dataset and try again."
            return cls._unavailable(crop, timestamp, message)

        average = round(sum(item.modal_price_per_quintal for item in items) / len(items), 2)
        return MarketPriceReportOut(
            crop_name=crop,
            latest_prices=items,
            average_modal_price=average,
            price_trend="unknown",
            recommendation=(
                f"Showing {len(items)} stored mandi record(s) for {crop}. "
                "Check the reported market and date before making a selling decision."
            ),
            retrieval_timestamp=timestamp,
            freshness="cached" if skip else "live",
        )

    @staticmethod
    def _unavailable(
        crop_name: str,
        timestamp: str,
        message: str,
    ) -> MarketPriceReportOut:
        return MarketPriceReportOut(
            crop_name=crop_name,
            latest_prices=[],
            average_modal_price=None,
            price_trend="unknown",
            recommendation=message,
            retrieval_timestamp=timestamp,
            freshness="unavailable",
        )
