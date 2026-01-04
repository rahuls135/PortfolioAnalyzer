from __future__ import annotations

from typing import Protocol, Optional, Iterable
from dataclasses import dataclass


@dataclass
class HoldingRecord:
    id: int
    user_id: int
    ticker: str
    shares: float
    avg_price: float
    asset_type: Optional[str] = None


@dataclass
class StockDataRecord:
    ticker: str
    current_price: Optional[float] = None
    sector: Optional[str] = None
    asset_type: Optional[str] = None
    last_updated: Optional[object] = None


class HoldingsRepository(Protocol):
    def list_by_user(self, user_id: int) -> Iterable[HoldingRecord]:
        ...

    def get_by_ticker(self, user_id: int, ticker: str) -> HoldingRecord | None:
        ...

    def create(self, record: HoldingRecord) -> HoldingRecord:
        ...

    def update(self, record: HoldingRecord) -> HoldingRecord:
        ...

    def delete(self, holding_id: int, user_id: int) -> None:
        ...


class StockDataRepository(Protocol):
    def get(self, ticker: str) -> Optional[StockDataRecord]:
        ...

    def save(self, record: StockDataRecord) -> StockDataRecord:
        ...


@dataclass
class TranscriptRecord:
    ticker: str
    quarter: str
    transcript: str
    summary: Optional[str] = None
    fetched_at: Optional[object] = None


class TranscriptRepository(Protocol):
    def get(self, ticker: str, quarter: str) -> Optional[TranscriptRecord]:
        ...

    def save(self, record: TranscriptRecord) -> TranscriptRecord:
        ...
