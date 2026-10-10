"""Import real market observations from the data.gov.in AGMARKNET resource.

The importer never creates synthetic prices. It normalizes provider records and uses
idempotent MongoDB upserts keyed by commodity, market, variety and arrival date.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import logging
import re
from typing import Any

import httpx
from pymongo import UpdateOne

from app.core.config import settings
from app.db.collection_names import MARKET_PRICES_COLLECTION
from app.db.mongo import get_db

logger = logging.getLogger(__name__)
SOURCE = "data.gov.in AGMARKNET"


def _first(record: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _numeric(record: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        raw = record.get(key)
        if raw is None or not str(raw).strip():
            continue
        try:
            value = float(str(raw).replace(",", "").replace("₹", "").strip())
            if value >= 0:
                return value
        except (TypeError, ValueError):
            continue
    return None


def _iso_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()[:10]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y"):
        try:
            return dt.datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def normalize_record(record: dict[str, Any]) -> dict[str, Any] | None:
    """Convert provider aliases to the exact schema read by MarketClient."""
    crop = _first(record, "commodity", "crop", "crop_name", "commodity_name")
    market = _first(record, "market", "market_name", "apmc")
    state = _first(record, "state")
    district = _first(record, "district")
    arrival_date = _iso_date(_first(record, "arrival_date", "arrivalDate", "price_date", "date"))
    modal = _numeric(record, "modal_price", "modal_price_per_quintal", "modalPrice", "modal")
    if not all((crop, market, state, district, arrival_date)) or modal is None or modal <= 0:
        return None

    minimum = _numeric(record, "min_price", "min_price_per_quintal", "minPrice", "minimum_price")
    maximum = _numeric(record, "max_price", "max_price_per_quintal", "maxPrice", "maximum_price")
    variety = _first(record, "variety", "variety_name") or "Not specified"
    identity = "|".join((crop.casefold(), market.casefold(), variety.casefold(), arrival_date, state.casefold(), district.casefold()))
    return {
        "crop_name": crop,
        "crop": crop,
        "commodity": crop,
        "commodity_name": crop,
        "market_name": market,
        "market": market,
        "variety": variety,
        "state": state,
        "district": district,
        "arrival_date": arrival_date,
        "price_date": arrival_date,
        "date": arrival_date,
        "modal_price_per_quintal": modal,
        "modal_price": modal,
        "min_price_per_quintal": minimum if minimum is not None else modal,
        "min_price": minimum if minimum is not None else modal,
        "max_price_per_quintal": maximum if maximum is not None else modal,
        "max_price": maximum if maximum is not None else modal,
        "source": SOURCE,
        "source_record_id": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


async def sync_market_prices(
    crop: str | None = None,
    state: str | None = None,
    district: str | None = None,
    max_pages: int = 10,
    page_size: int = 1000,
) -> dict[str, Any]:
    """Fetch provider pages and idempotently upsert validated observations."""
    api_key = settings.MARKET_API_KEY.strip()
    endpoint = settings.MARKET_API_BASE_URL.strip()
    if not api_key or api_key.startswith("your_"):
        raise RuntimeError("MARKET_API_KEY is not configured.")
    if not endpoint.startswith("https://"):
        raise RuntimeError("MARKET_API_BASE_URL must use HTTPS.")
    db = get_db()
    if db is None:
        raise RuntimeError("MongoDB is unavailable; market import cannot persist data.")

    collection = db[MARKET_PRICES_COLLECTION]
    imported = rejected = fetched = 0
    pages = 0
    params: dict[str, Any] = {"api-key": api_key, "format": "json", "limit": min(max(page_size, 1), 1000)}
    if crop:
        params["filters[commodity]"] = crop.strip()
    if state:
        params["filters[state]"] = state.strip()
    if district:
        params["filters[district]"] = district.strip()

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        for page in range(max(1, min(max_pages, 100))):
            params["offset"] = page * params["limit"]
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
                raise ValueError("Market provider response did not contain a records array.")
            records = payload["records"]
            pages += 1
            fetched += len(records)
            operations = []
            for raw in records:
                normalized = normalize_record(raw) if isinstance(raw, dict) else None
                if normalized is None:
                    rejected += 1
                    continue
                identity = normalized["source_record_id"]
                operations.append(UpdateOne(
                    {"source_record_id": identity},
                    {"$set": normalized, "$setOnInsert": {"created_at": dt.datetime.now(dt.timezone.utc).isoformat()}},
                    upsert=True,
                ))
            if operations:
                result = collection.bulk_write(operations, ordered=False)
                imported += result.upserted_count + result.modified_count
            if len(records) < params["limit"]:
                break

    return {
        "provider": SOURCE,
        "crop_filter": crop,
        "state_filter": state,
        "district_filter": district,
        "pages_fetched": pages,
        "records_fetched": fetched,
        "records_rejected": rejected,
        "records_inserted_or_updated": imported,
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "note": "Only validated provider observations were stored; no missing dates or prices were synthesized.",
    }
