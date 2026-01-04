from __future__ import annotations

from sqlalchemy.orm import Session
from datetime import datetime, timezone

import models
from .repositories import TranscriptRepository, TranscriptRecord, StockDataRepository, StockDataRecord


class SqlAlchemyTranscriptRepository(TranscriptRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, ticker: str, quarter: str) -> TranscriptRecord | None:
        existing = (
            self.db.query(models.EarningsTranscript)
            .filter(
                models.EarningsTranscript.ticker == ticker,
                models.EarningsTranscript.quarter == quarter
            )
            .first()
        )
        if not existing:
            return None
        return TranscriptRecord(
            ticker=existing.ticker,
            quarter=existing.quarter,
            transcript=existing.transcript or "",
            summary=existing.summary,
            fetched_at=existing.fetched_at
        )


class SqlAlchemyStockDataRepository(StockDataRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, ticker: str) -> StockDataRecord | None:
        stock = (
            self.db.query(models.StockData)
            .filter(models.StockData.ticker == ticker)
            .first()
        )
        if not stock:
            return None
        return StockDataRecord(
            ticker=stock.ticker,
            current_price=stock.current_price,
            sector=stock.sector,
            asset_type=stock.asset_type,
            last_updated=stock.last_updated
        )

    def save(self, record: StockDataRecord) -> StockDataRecord:
        stock = (
            self.db.query(models.StockData)
            .filter(models.StockData.ticker == record.ticker)
            .first()
        )
        if stock:
            if record.current_price is not None:
                stock.current_price = record.current_price
            if record.sector is not None:
                stock.sector = record.sector
            if record.asset_type is not None:
                stock.asset_type = record.asset_type
            if record.last_updated is not None:
                stock.last_updated = record.last_updated
        else:
            stock = models.StockData(
                ticker=record.ticker,
                current_price=record.current_price,
                sector=record.sector,
                asset_type=record.asset_type,
                last_updated=record.last_updated
            )
            self.db.add(stock)
        self.db.commit()
        self.db.refresh(stock)
        return StockDataRecord(
            ticker=stock.ticker,
            current_price=stock.current_price,
            sector=stock.sector,
            asset_type=stock.asset_type
        )

    def save(self, record: TranscriptRecord) -> TranscriptRecord:
        existing = (
            self.db.query(models.EarningsTranscript)
            .filter(
                models.EarningsTranscript.ticker == record.ticker,
                models.EarningsTranscript.quarter == record.quarter
            )
            .first()
        )
        if existing:
            existing.transcript = record.transcript
            existing.summary = record.summary
            existing.fetched_at = record.fetched_at
        else:
            existing = models.EarningsTranscript(
                ticker=record.ticker,
                quarter=record.quarter,
                transcript=record.transcript,
                summary=record.summary,
                fetched_at=record.fetched_at
            )
            self.db.add(existing)
        self.db.commit()
        self.db.refresh(existing)
        return TranscriptRecord(
            ticker=existing.ticker,
            quarter=existing.quarter,
            transcript=existing.transcript or "",
            summary=existing.summary,
            fetched_at=existing.fetched_at
        )
