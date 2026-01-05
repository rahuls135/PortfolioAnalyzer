from __future__ import annotations

from sqlalchemy.orm import Session
import os

from .providers import get_market_data_provider, get_transcript_provider
from .profile import ProfileService
from .market_data import MarketDataService
from .transcripts import TranscriptService
from .holdings import HoldingsService
from .analysis import AnalysisService
from .portfolio_analysis import PortfolioAnalysisService
from .tickers import TickerValidationService, load_ticker_universe, TickerUniverseCache
from .sqlalchemy_repositories import (
    SqlAlchemyUserRepository,
    SqlAlchemyProfileRepository,
    SqlAlchemyStockDataRepository,
    SqlAlchemyTranscriptRepository,
    SqlAlchemyHoldingsRepository,
)


def get_profile_service(db: Session) -> ProfileService:
    return ProfileService(SqlAlchemyUserRepository(db), SqlAlchemyProfileRepository(db))


def get_profile_repository(db: Session) -> SqlAlchemyProfileRepository:
    return SqlAlchemyProfileRepository(db)


def get_market_data_service(db: Session, throttle) -> MarketDataService:
    provider = get_market_data_provider(throttle)
    return MarketDataService(provider, SqlAlchemyStockDataRepository(db))


def get_transcript_service(db: Session, throttle) -> TranscriptService:
    provider = get_transcript_provider(throttle)
    return TranscriptService(SqlAlchemyTranscriptRepository(db), provider)


def get_holdings_service(db: Session) -> HoldingsService:
    return HoldingsService(SqlAlchemyHoldingsRepository(db))


def get_analysis_service(db: Session) -> AnalysisService:
    return AnalysisService(SqlAlchemyProfileRepository(db))


def get_portfolio_analysis_service(db: Session, throttle) -> PortfolioAnalysisService:
    return PortfolioAnalysisService(
        SqlAlchemyHoldingsRepository(db),
        SqlAlchemyStockDataRepository(db),
        get_market_data_service(db, throttle),
        get_analysis_service(db)
    )


def get_ticker_validation_service(
    db: Session,
    throttle,
    cache: dict[str, TickerUniverseCache],
) -> TickerValidationService:
    path = os.getenv("TICKER_UNIVERSE_PATH")

    def load_cached(path_value: str) -> TickerUniverseCache | None:
        cached = cache.get(path_value)
        if cached:
            try:
                stat = os.stat(path_value)
                if cached.mtime == stat.st_mtime:
                    return cached
            except FileNotFoundError:
                return None
        refreshed = load_ticker_universe(path_value)
        if refreshed:
            cache[path_value] = refreshed
        return refreshed

    return TickerValidationService(
        get_market_data_service(db, throttle),
        path,
        load_cached
    )
