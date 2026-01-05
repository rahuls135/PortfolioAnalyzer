from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Set, Optional, Callable

from .market_data import MarketDataService


@dataclass
class TickerUniverseCache:
    tickers: Set[str]
    mtime: float


class TickerValidationService:
    def __init__(
        self,
        market_data: MarketDataService,
        universe_path: Optional[str],
        cache_loader: Callable[[str], Optional[TickerUniverseCache]],
    ) -> None:
        self.market_data = market_data
        self.universe_path = universe_path
        self.cache_loader = cache_loader

    def validate(self, ticker: str) -> bool:
        universe = self._load_universe()
        if universe is not None:
            return ticker in universe
        self.market_data.validate_ticker(ticker)
        return True

    def _load_universe(self) -> Optional[Set[str]]:
        if not self.universe_path:
            return None
        cache = self.cache_loader(self.universe_path)
        if not cache:
            return None
        return cache.tickers


def load_ticker_universe(path: str) -> Optional[TickerUniverseCache]:
    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return None
    tickers: Set[str] = set()
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            cleaned = line.strip().upper()
            if not cleaned:
                continue
            if not cleaned.isalnum() or len(cleaned) > 10:
                continue
            tickers.add(cleaned)
    return TickerUniverseCache(tickers=tickers, mtime=stat.st_mtime)
