from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .providers import MarketDataProvider, MarketQuote
from .repositories import StockDataRepository, StockDataRecord


class MarketDataService:
    def __init__(self, provider: MarketDataProvider, repo: StockDataRepository) -> None:
        self.provider = provider
        self.repo = repo

    def validate_ticker(self, ticker: str) -> bool:
        record = self.repo.get(ticker)
        if record and record.current_price is not None:
            return True
        self.provider.get_quote(ticker)
        return True

    def get_quote(
        self,
        ticker: str,
        now_utc: datetime,
        cache_valid: Callable[[datetime, datetime], bool],
    ) -> tuple[MarketQuote, bool]:
        record = self.repo.get(ticker)
        if record and record.last_updated and record.current_price is not None:
            if cache_valid(record.last_updated, now_utc):
                return (
                    MarketQuote(
                        ticker=ticker,
                        current_price=record.current_price,
                        sector=record.sector,
                        asset_type=record.asset_type
                    ),
                    True,
                )

        quote = self.provider.get_quote(ticker)
        sector = record.sector if record else None
        asset_type = record.asset_type if record else None

        if not sector or sector == "Unknown" or not asset_type or asset_type == "Unknown":
            overview = self.provider.get_overview(ticker)
            sector = overview.sector or sector
            asset_type = overview.asset_type or asset_type

        self.repo.save(StockDataRecord(
            ticker=ticker,
            current_price=quote.current_price,
            sector=sector,
            asset_type=asset_type,
            last_updated=now_utc
        ))
        return (
            MarketQuote(
                ticker=ticker,
                current_price=quote.current_price,
                sector=sector,
                asset_type=asset_type
            ),
            False,
        )

    def get_asset_type(self, ticker: str) -> str:
        record = self.repo.get(ticker)
        if record and record.asset_type and record.asset_type != "Unknown":
            return record.asset_type
        overview = self.provider.get_overview(ticker)
        asset_type = overview.asset_type or "Unknown"
        sector = overview.sector or record.sector if record else None
        self.repo.save(StockDataRecord(
            ticker=ticker,
            current_price=record.current_price if record else None,
            sector=sector,
            asset_type=asset_type,
            last_updated=record.last_updated if record else None
        ))
        return asset_type
