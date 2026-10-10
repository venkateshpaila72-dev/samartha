from app.integrations.market_client import _forecast
from app.schemas.market import MarketPricePoint


def test_forecast_requires_seven_distinct_dates():
    points = [
        MarketPricePoint(date=f"2026-10-0{day}", average_modal_price_per_quintal=100 + day, observations=1)
        for day in range(1, 7)
    ]
    forecasts, trend, note = _forecast(points)
    assert forecasts == []
    assert trend == "unknown"
    assert "at least 7" in note


def test_forecast_returns_seven_estimates_with_uncertainty_band():
    points = [
        MarketPricePoint(date=f"2026-10-{day:02d}", average_modal_price_per_quintal=100 + day * 2, observations=2)
        for day in range(1, 8)
    ]
    forecasts, trend, note = _forecast(points)
    assert len(forecasts) == 7
    assert trend == "rising"
    assert forecasts[0].lower_estimate <= forecasts[0].predicted_modal_price_per_quintal
    assert forecasts[0].predicted_modal_price_per_quintal <= forecasts[0].upper_estimate
    assert "not a statistical guarantee" in note
