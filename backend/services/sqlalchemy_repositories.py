from __future__ import annotations

from sqlalchemy.orm import Session
from datetime import datetime, timezone

import models
from .repositories import TranscriptRepository, TranscriptRecord, StockDataRepository, StockDataRecord, HoldingsRepository, HoldingRecord


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


class SqlAlchemyHoldingsRepository(HoldingsRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: int) -> list[HoldingRecord]:
        holdings = (
            self.db.query(models.Holding)
            .filter(models.Holding.user_id == user_id)
            .all()
        )
        return [
            HoldingRecord(
                id=h.id,
                user_id=h.user_id,
                ticker=h.ticker,
                shares=h.shares,
                avg_price=h.avg_price,
                asset_type=h.asset_type
            )
            for h in holdings
        ]

    def get_by_ticker(self, user_id: int, ticker: str) -> HoldingRecord | None:
        holding = (
            self.db.query(models.Holding)
            .filter(models.Holding.user_id == user_id, models.Holding.ticker == ticker)
            .first()
        )
        if not holding:
            return None
        return HoldingRecord(
            id=holding.id,
            user_id=holding.user_id,
            ticker=holding.ticker,
            shares=holding.shares,
            avg_price=holding.avg_price,
            asset_type=holding.asset_type
        )

    def create(self, record: HoldingRecord) -> HoldingRecord:
        holding = models.Holding(
            user_id=record.user_id,
            ticker=record.ticker,
            shares=record.shares,
            avg_price=record.avg_price,
            asset_type=record.asset_type
        )
        self.db.add(holding)
        self.db.commit()
        self.db.refresh(holding)
        return HoldingRecord(
            id=holding.id,
            user_id=holding.user_id,
            ticker=holding.ticker,
            shares=holding.shares,
            avg_price=holding.avg_price,
            asset_type=holding.asset_type
        )

    def update(self, record: HoldingRecord) -> HoldingRecord:
        holding = (
            self.db.query(models.Holding)
            .filter(models.Holding.id == record.id, models.Holding.user_id == record.user_id)
            .first()
        )
        if not holding:
            raise ValueError("Holding not found")
        holding.ticker = record.ticker
        holding.shares = record.shares
        holding.avg_price = record.avg_price
        holding.asset_type = record.asset_type
        self.db.commit()
        self.db.refresh(holding)
        return HoldingRecord(
            id=holding.id,
            user_id=holding.user_id,
            ticker=holding.ticker,
            shares=holding.shares,
            avg_price=holding.avg_price,
            asset_type=holding.asset_type
        )

    def delete(self, holding_id: int, user_id: int) -> None:
        holding = (
            self.db.query(models.Holding)
            .filter(models.Holding.id == holding_id, models.Holding.user_id == user_id)
            .first()
        )
        if not holding:
            raise ValueError("Holding not found")
        self.db.delete(holding)
        self.db.commit()


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
