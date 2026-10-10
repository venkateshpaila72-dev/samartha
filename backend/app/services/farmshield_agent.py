"""FarmShield agent coordinating crop-market analysis and farmer-language output."""
import asyncio
from app.integrations.market_client import MarketClient
from app.integrations.azure_translator_client import AzureTranslatorClient
from app.schemas.market import MarketPriceReportOut

SUPPORTED_LANGUAGES = {"en", "hi", "te", "ta", "kn", "mr", "pa", "bn"}


class FarmShieldAgent:
    """Orchestrates market lookup, trend/forecast calculation and localization.

    It never fabricates historical records. MarketClient returns forecasts only
    when enough dated observations exist; the agent localizes explanatory text.
    """

    @classmethod
    async def market_advisory(
        cls, crop_name: str, language: str = "en",
        state: str | None = None, district: str | None = None,
        limit: int = 50, skip: int = 0,
    ) -> MarketPriceReportOut:
        report = await MarketClient.get_market_prices(
            crop_name=crop_name, state=state, district=district, limit=limit, skip=skip
        )
        target = (language or "en").lower().split("-")[0]
        if target not in SUPPORTED_LANGUAGES or target == "en":
            return report

        async def tr(value: str) -> str:
            if not value:
                return value
            try:
                return await AzureTranslatorClient.translate_text(
                    text=value, target_lang=target, source_lang="en"
                )
            except Exception:
                # Keep the original safe text if the translation provider is unavailable.
                return value

        report.recommendation, report.forecast_note = await asyncio.gather(
            tr(report.recommendation), tr(report.forecast_note)
        )
        # Translate user-visible market labels while preserving numeric values and dates.
        for item in report.latest_prices:
            fields = ["crop_name", "variety", "market_name", "district", "state", "source"]
            translated = await asyncio.gather(*(tr(getattr(item, field) or "") for field in fields))
            for field, value in zip(fields, translated):
                setattr(item, field, value)
        return report
