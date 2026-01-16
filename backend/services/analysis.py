from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
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

    def build_meta(
        self,
        profile: ProfileRecord | None,
        now_utc: datetime,
        cooldown_seconds: int,
        cached: bool,
    ) -> dict:
        last_at = None
        next_at = None
        remaining = 0

        if profile and profile.portfolio_analysis_at:
            last_at = profile.portfolio_analysis_at
            if last_at.tzinfo is None:
                last_at = last_at.replace(tzinfo=timezone.utc)
            next_at = last_at + timedelta(seconds=cooldown_seconds)
            remaining = max(0, int((next_at - now_utc).total_seconds()))

        return {
            "cached": cached,
            "last_analysis_at": last_at.isoformat() if last_at else None,
            "next_available_at": next_at.isoformat() if next_at else None,
            "cooldown_remaining_seconds": remaining
        }
