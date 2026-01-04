from __future__ import annotations

from sqlalchemy.orm import Session

import models
from .repositories import TranscriptRepository, TranscriptRecord


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
