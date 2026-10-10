from app.integrations.market_ingestion_client import normalize_record, _iso_date


def test_normalize_real_provider_record_to_market_client_schema():
    normalized = normalize_record({
        "state": "Andhra Pradesh",
        "district": "Guntur",
        "market": "Guntur",
        "commodity": "Chilli",
        "variety": "Red",
        "arrival_date": "09/10/2026",
        "min_price": "12000",
        "max_price": "15000",
        "modal_price": "13500",
    })
    assert normalized is not None
    assert normalized["crop_name"] == "Chilli"
    assert normalized["crop"] == "Chilli"
    assert normalized["price_date"] == "2026-10-09"
    assert normalized["modal_price_per_quintal"] == 13500
    assert normalized["source"] == "data.gov.in AGMARKNET"
    assert normalized["source_record_id"]


def test_reject_incomplete_or_invalid_provider_record():
    assert normalize_record({"commodity": "Rice", "modal_price": "not-a-price"}) is None


def test_provider_date_parsing_is_explicit():
    assert _iso_date("2026-10-09") == "2026-10-09"
    assert _iso_date("09/10/2026") == "2026-10-09"
    assert _iso_date("not a date") is None
