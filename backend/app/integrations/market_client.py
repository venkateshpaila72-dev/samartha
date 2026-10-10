
"""AGMARKNET 2.0 client for FarmShield market prices."""

import datetime
import json
import logging
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
        )
