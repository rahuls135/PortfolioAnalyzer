from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from .repositories import ProfileRepository, ProfileRecord


@dataclass
class MetricsPayload:
    sector_allocation: list[dict]
    top_holdings: list[dict]
    concentration_top3_pct: float
    diversification_score: float


class AnalysisService:
    def __init__(self, profile_repo: ProfileRepository) -> None:
        self.profile_repo = profile_repo

    def cache_metrics(self, user_id: int, metrics: MetricsPayload) -> None:
        profile = self.profile_repo.get(user_id) or ProfileRecord(user_id=user_id)
        profile.portfolio_metrics = {
            "sector_allocation": metrics.sector_allocation,
            "top_holdings": metrics.top_holdings,
            "concentration_top3_pct": metrics.concentration_top3_pct,
            "diversification_score": metrics.diversification_score
        }
        self.profile_repo.save(profile)

    def cache_analysis(self, user_id: int, ai_analysis: str, analyzed_at: datetime) -> None:
        profile = self.profile_repo.get(user_id) or ProfileRecord(user_id=user_id)
        profile.portfolio_analysis = ai_analysis
        profile.portfolio_analysis_at = analyzed_at
        self.profile_repo.save(profile)

    def get_cached(self, user_id: int) -> ProfileRecord | None:
        return self.profile_repo.get(user_id)

    def cache_transcripts(self, user_id: int, quarter: str, summaries: dict) -> None:
        profile = self.profile_repo.get(user_id) or ProfileRecord(user_id=user_id)
        profile.portfolio_transcripts = summaries
        profile.portfolio_transcripts_quarter = quarter
        self.profile_repo.save(profile)
