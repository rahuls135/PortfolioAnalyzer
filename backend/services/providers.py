from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass(frozen=True)
class MarketQuote:
    ticker: str
    current_price: float
    sector: Optional[str] = None
    asset_type: Optional[str] = None


@dataclass(frozen=True)
class EarningsTranscript:
    ticker: str
    quarter: str
    transcript: str


class MarketDataProvider(Protocol):
    def get_quote(self, ticker: str) -> MarketQuote:
        ...

    def get_overview(self, ticker: str) -> MarketQuote:
        ...


class TranscriptProvider(Protocol):
    def get_transcript(self, ticker: str, quarter: str) -> EarningsTranscript:
        ...


class AlphaVantageTranscriptProvider:
    def __init__(self, api_key: str, throttle) -> None:
        self.api_key = api_key
        self.throttle = throttle

    def get_transcript(self, ticker: str, quarter: str) -> EarningsTranscript:
        import requests

        self.throttle()
        url = (
            "https://www.alphavantage.co/query"
            f"?function=EARNINGS_CALL_TRANSCRIPT&symbol={ticker}&quarter={quarter}&apikey={self.api_key}"
        )
        res = requests.get(url).json()
        if res.get("Note") or res.get("Information"):
            message = res.get("Note") or res.get("Information")
            raise RuntimeError(f"Alpha Vantage response: {message}")
        return EarningsTranscript(
            ticker=ticker,
            quarter=quarter,
            transcript=res.get("transcript", "")
        )


def get_transcript_provider(throttle) -> TranscriptProvider:
    import os

    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        raise RuntimeError("Alpha Vantage API key not configured")
    return AlphaVantageTranscriptProvider(api_key, throttle)
