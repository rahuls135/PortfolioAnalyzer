from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from typing import Optional

from .providers import TranscriptProvider
from .repositories import TranscriptRepository, TranscriptRecord


def _previous_quarter(q: str) -> str:
    year = int(q[:4])
    quarter_num = int(q[-1])
    if quarter_num == 1:
        return f"{year - 1}Q4"
    return f"{year}Q{quarter_num - 1}"


def _normalize_transcript_text(text: str | list | dict) -> str:
    if not text:
        return ""
    if isinstance(text, dict):
        for key in ("content", "text", "transcript"):
            value = text.get(key)
            if value:
                return _normalize_transcript_text(value)
        return json.dumps(text)
    if isinstance(text, list):
        parts = []
        for item in text:
            if not item:
                continue
            if isinstance(item, dict):
                content = item.get("content") or item.get("text") or item.get("transcript")
                if content:
                    parts.append(str(content))
                else:
                    parts.append(json.dumps(item))
            else:
                parts.append(str(item))
        return " ".join(parts).strip()
    return str(text)


def _summarize_transcript(text: str | list | dict, max_sentences: int = 4, max_chars: int = 800) -> str:
    normalized = _normalize_transcript_text(text)
    if not normalized:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", normalized.strip())
    summary = " ".join(sentences[:max_sentences]).strip()
    if len(summary) > max_chars:
        summary = summary[:max_chars].rstrip() + "..."
    return summary


class TranscriptService:
    def __init__(self, repo: TranscriptRepository, provider: TranscriptProvider) -> None:
        self.repo = repo
        self.provider = provider

    def get_summary(self, ticker: str, quarter: str, fallback: Optional[int] = 0) -> TranscriptRecord:
        remaining = max(0, min(fallback or 0, 4))
        attempts = []
        current_quarter = quarter
        for _ in range(remaining + 1):
            attempts.append(current_quarter)
            current_quarter = _previous_quarter(current_quarter)

        for candidate in attempts:
            existing = self.repo.get(ticker, candidate)
            if existing and existing.summary:
                return existing

            transcript = self.provider.get_transcript(ticker, candidate)
            transcript_text = _normalize_transcript_text(transcript.transcript)
            if not transcript_text:
                continue

            summary = _summarize_transcript(transcript_text)
            fetched_at = datetime.now(timezone.utc)
            record = TranscriptRecord(
                ticker=ticker,
                quarter=candidate,
                transcript=transcript_text,
                summary=summary,
                fetched_at=fetched_at
            )
            return self.repo.save(record)

        raise LookupError("Transcript not found")
