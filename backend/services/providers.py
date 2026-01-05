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

        print(f"Alpha Vantage request: EARNINGS_CALL_TRANSCRIPT {ticker} {quarter}")
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


class AlphaVantageMarketDataProvider:
    def __init__(self, api_key: str, throttle) -> None:
        self.api_key = api_key
        self.throttle = throttle

    def get_quote(self, ticker: str) -> MarketQuote:
        import requests

        print(f"Alpha Vantage request: GLOBAL_QUOTE {ticker}")
        self.throttle()
        url = (
            "https://www.alphavantage.co/query"
            f"?function=GLOBAL_QUOTE&symbol={ticker}&apikey={self.api_key}"
        )
        res = requests.get(url).json()
        if res.get("Note") or res.get("Information"):
            message = res.get("Note") or res.get("Information")
            raise RuntimeError(f"Alpha Vantage response: {message}")
        quote = res.get("Global Quote") or {}
        price = quote.get("05. price")
        if not price:
            raise RuntimeError("Stock price not found")
        return MarketQuote(ticker=ticker, current_price=float(price))

    def get_overview(self, ticker: str) -> MarketQuote:
        import requests

        print(f"Alpha Vantage request: OVERVIEW {ticker}")
        self.throttle()
        url = (
            "https://www.alphavantage.co/query"
            f"?function=OVERVIEW&symbol={ticker}&apikey={self.api_key}"
        )
        res = requests.get(url).json()
        if res.get("Note") or res.get("Information"):
            message = res.get("Note") or res.get("Information")
            raise RuntimeError(f"Alpha Vantage response: {message}")
        return MarketQuote(
            ticker=ticker,
            current_price=0.0,
            sector=res.get("Sector", "Unknown"),
            asset_type=res.get("AssetType", "Unknown"),
        )


def get_market_data_provider(throttle) -> MarketDataProvider:
    import os

    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        raise RuntimeError("Alpha Vantage API key not configured")
    return AlphaVantageMarketDataProvider(api_key, throttle)
