"""Agricultural Market Price Client for FarmShield using AGMARKNET.
Integrates commodity pricing from APMC mandis across India with strict data integrity:
- Never substitutes an unknown crop with Wheat.
- Returns explicit 'unavailable' state when price records do not exist.
- Clearly marks reference samples without stamping misleading live arrival dates.
"""

import datetime
import logging
from typing import Optional, List, Dict, Any
import httpx

from app.core.config import settings
from app.db.collection_names import MARKET_PRICES_COLLECTION
from app.db.mongo import get_db
from app.schemas.market import MarketPriceItem, MarketPriceReportOut

logger = logging.getLogger(__name__)

# Reference AGMARKNET APMC benchmark price dataset for verified storage crops
AGMARKNET_BENCHMARKS: Dict[str, List[Dict[str, Any]]] = {
    "Paddy (Rice)": [
        {"market": "Karnal APMC", "district": "Karnal", "state": "Haryana", "modal": 2350.0, "min": 2180.0, "max": 2450.0, "variety": "Common"},
        {"market": "Gondia APMC", "district": "Gondia", "state": "Maharashtra", "modal": 2220.0, "min": 2050.0, "max": 2300.0, "variety": "Fine"},
        {"market": "Burdwan APMC", "district": "Purba Bardhaman", "state": "West Bengal", "modal": 2280.0, "min": 2100.0, "max": 2360.0, "variety": "Ratna"},
    ],
    "Wheat": [
        {"market": "Khanna APMC", "district": "Ludhiana", "state": "Punjab", "modal": 2425.0, "min": 2320.0, "max": 2510.0, "variety": "Dara"},
        {"market": "Indore APMC", "district": "Indore", "state": "Madhya Pradesh", "modal": 2550.0, "min": 2400.0, "max": 2680.0, "variety": "Sharbati"},
        {"market": "Hapur APMC", "district": "Hapur", "state": "Uttar Pradesh", "modal": 2390.0, "min": 2280.0, "max": 2460.0, "variety": "Deshi"},
    ],
    "Maize (Corn)": [
        {"market": "Gulabbagh APMC", "district": "Purnea", "state": "Bihar", "modal": 2150.0, "min": 1980.0, "max": 2240.0, "variety": "Yellow"},
        {"market": "Davangere APMC", "district": "Davangere", "state": "Karnataka", "modal": 2200.0, "min": 2050.0, "max": 2290.0, "variety": "Local"},
        {"market": "Chhindwara APMC", "district": "Chhindwara", "state": "Madhya Pradesh", "modal": 2110.0, "min": 1950.0, "max": 2180.0, "variety": "Hybrid"},
    ],
    "Onion": [
        {"market": "Lasalgaon APMC", "district": "Nashik", "state": "Maharashtra", "modal": 2800.0, "min": 1600.0, "max": 3400.0, "variety": "Red"},
        {"market": "Pimpalgaon APMC", "district": "Nashik", "state": "Maharashtra", "modal": 2750.0, "min": 1550.0, "max": 3300.0, "variety": "Pol"},
        {"market": "Hubli APMC", "district": "Dharwad", "state": "Karnataka", "modal": 2650.0, "min": 1800.0, "max": 3100.0, "variety": "Bangalore Rose"},
    ],
    "Potato": [
        {"market": "Agra APMC", "district": "Agra", "state": "Uttar Pradesh", "modal": 1450.0, "min": 1200.0, "max": 1650.0, "variety": "Kufri Bahar"},
        {"market": "Jalandhar APMC", "district": "Jalandhar", "state": "Punjab", "modal": 1380.0, "min": 1150.0, "max": 1520.0, "variety": "Jyoti"},
        {"market": "Deesa APMC", "district": "Banaskantha", "state": "Gujarat", "modal": 1520.0, "min": 1280.0, "max": 1700.0, "variety": "Badshah"},
    ],
    "Chickpea (Gram / Chana)": [
        {"market": "Bikaner APMC", "district": "Bikaner", "state": "Rajasthan", "modal": 5850.0, "min": 5600.0, "max": 6100.0, "variety": "Desi"},
        {"market": "Latur APMC", "district": "Latur", "state": "Maharashtra", "modal": 5900.0, "min": 5650.0, "max": 6150.0, "variety": "Annagiri"},
        {"market": "Akola APMC", "district": "Akola", "state": "Maharashtra", "modal": 5820.0, "min": 5580.0, "max": 6050.0, "variety": "Chana"},
    ],
    "Soybean": [
        {"market": "Indore APMC", "district": "Indore", "state": "Madhya Pradesh", "modal": 4750.0, "min": 4500.0, "max": 4900.0, "variety": "Yellow"},
        {"market": "Ujjain APMC", "district": "Ujjain", "state": "Madhya Pradesh", "modal": 4700.0, "min": 4450.0, "max": 4860.0, "variety": "Local"},
        {"market": "Nagpur APMC", "district": "Nagpur", "state": "Maharashtra", "modal": 4680.0, "min": 4420.0, "max": 4820.0, "variety": "Yellow"},
    ],
    "Mustard": [
        {"market": "Bharatpur APMC", "district": "Bharatpur", "state": "Rajasthan", "modal": 5450.0, "min": 5200.0, "max": 5650.0, "variety": "Black"},
        {"market": "Alwar APMC", "district": "Alwar", "state": "Rajasthan", "modal": 5400.0, "min": 5150.0, "max": 5600.0, "variety": "Mustard"},
    ],
}


class MarketClient:
    """AGMARKNET Agricultural Market Client."""

    @classmethod
    async def get_market_prices(cls, crop_name: str) -> MarketPriceReportOut:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        clean_crop = crop_name.strip()

        # Find matching crop key in benchmarks if any
        matched_crop = None
        for key in AGMARKNET_BENCHMARKS.keys():
            if key.lower() in clean_crop.lower() or clean_crop.lower() in key.lower():
                matched_crop = key
                break

        # 1. Try querying data.gov.in / AGMARKNET API if configured
        api_key = settings.MARKET_API_KEY.strip()
        base_url = settings.MARKET_API_BASE_URL.strip() or "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        parsed_items: List[MarketPriceItem] = []
        is_live = False

        if api_key and not api_key.startswith("your_"):
            try:
                params = {
                    "api-key": api_key,
                    "format": "json",
                    "filters[commodity]": matched_crop or clean_crop,
                    "limit": 10,
                }
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(base_url, params=params)
                    if resp.status_code == 200:
                        records = resp.json().get("records", [])
                        for r in records:
                            parsed_items.append(
                                MarketPriceItem(
                                    crop_name=clean_crop,
                                    variety=r.get("variety", "Standard"),
                                    market_name=r.get("market", "APMC Mandi"),
                                    district=r.get("district", "N/A"),
                                    state=r.get("state", "India"),
                                    modal_price_per_quintal=float(r.get("modal_price", 0.0)),
                                    min_price_per_quintal=float(r.get("min_price", 0.0)),
                                    max_price_per_quintal=float(r.get("max_price", 0.0)),
                                    price_date=r.get("arrival_date", "Live"),
                                    source="data.gov.in / AGMARKNET API",
                                )
                            )
                        if parsed_items:
                            is_live = True
            except Exception as e:
                logger.debug(f"data.gov.in AGMARKNET query error: {e}")

        # 2. If live query succeeded, build live report
        if is_live and parsed_items:
            total_modal = sum(item.modal_price_per_quintal for item in parsed_items)
            avg_modal = round(total_modal / len(parsed_items), 2)
            report = MarketPriceReportOut(
                crop_name=clean_crop,
                latest_prices=parsed_items,
                average_modal_price=avg_modal,
                price_trend="stable",
                recommendation=f"Live APMC modal rates for {clean_crop} average ₹{avg_modal:,.0f}/quintal.",
                retrieval_timestamp=now_iso,
                freshness="live",
            )
            return report

        # 3. Check if we have verified static benchmark for this specific crop
        if matched_crop and matched_crop in AGMARKNET_BENCHMARKS:
            benchmarks = AGMARKNET_BENCHMARKS[matched_crop]
            items = []
            for b in benchmarks:
                items.append(
                    MarketPriceItem(
                        crop_name=matched_crop,
                        variety=b.get("variety", "Common"),
                        market_name=b["market"],
                        district=b["district"],
                        state=b["state"],
                        modal_price_per_quintal=b["modal"],
                        min_price_per_quintal=b["min"],
                        max_price_per_quintal=b["max"],
                        price_date="Reference Benchmark",
                        source="AGMARKNET / Directorate of Marketing & Inspection",
                    )
                )
            total_modal = sum(item.modal_price_per_quintal for item in items)
            avg_modal = round(total_modal / len(items), 2)
            return MarketPriceReportOut(
                crop_name=clean_crop,
                latest_prices=items,
                average_modal_price=avg_modal,
                price_trend="stable",
                recommendation="Static reference sample for agricultural planning. Consult local APMC mandis for live day-of trading rates.",
                retrieval_timestamp=now_iso,
                freshness="reference_sample",
            )

        # 4. No data for this crop — DO NOT substitute Wheat or another crop!
        return MarketPriceReportOut(
            crop_name=clean_crop,
            latest_prices=[],
            average_modal_price=None,
            price_trend="unknown",
            recommendation=f"Mandi price data is currently unavailable for '{clean_crop}'. Please check your regional APMC mandi board.",
            retrieval_timestamp=now_iso,
            freshness="unavailable",
        )
