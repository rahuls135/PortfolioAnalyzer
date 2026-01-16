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


@dataclass
class ProfileRecord:
    user_id: int
    ai_analysis: Optional[str] = None
    portfolio_analysis: Optional[str] = None
    portfolio_analysis_at: Optional[object] = None
    portfolio_metrics: Optional[dict] = None


class ProfileRepository(Protocol):
    def get(self, user_id: int) -> Optional[ProfileRecord]:
        ...

    def save(self, record: ProfileRecord) -> ProfileRecord:
        ...


@dataclass
class UserRecord:
    id: int
    supabase_user_id: str
    age: int
    income: float
    risk_tolerance: str
    risk_assessment_mode: str
    retirement_years: int
    obligations_amount: Optional[float] = None


class UserRepository(Protocol):
    def get_by_supabase_id(self, supabase_user_id: str) -> Optional[UserRecord]:
        ...

    def get_by_id(self, user_id: int) -> Optional[UserRecord]:
        ...

    def create(self, record: UserRecord) -> UserRecord:
        ...

    def update(self, record: UserRecord) -> UserRecord:
        ...
