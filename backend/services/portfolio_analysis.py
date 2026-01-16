from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .analysis import AnalysisService, MetricsPayload
from .market_data import MarketDataService
from .repositories import HoldingsRepository, StockDataRepository, ProfileRecord


@dataclass
class AnalysisUser:
    id: int
    age: int
    risk_tolerance: str
    risk_assessment_mode: str
    retirement_years: int
    obligations_amount: Optional[float] = None


@dataclass
class PortfolioAnalysisResult:
    total_value: float
    holdings: list[dict]
    ai_analysis: str
    metrics: dict
    user_profile: dict
    cached: bool
    profile: ProfileRecord | None


class PortfolioAnalysisService:
    def __init__(
        self,
        holdings_repo: HoldingsRepository,
        stock_repo: StockDataRepository,
        market_data: MarketDataService,
        analysis: AnalysisService,
    ) -> None:
        self.holdings_repo = holdings_repo
        self.stock_repo = stock_repo
        self.market_data = market_data
        self.analysis = analysis

    def analyze(
        self,
        user: AnalysisUser,
        now_utc: datetime,
        cooldown_seconds: int,
    ) -> PortfolioAnalysisResult:
        profile = self.analysis.get_cached(user.id)
        risk_mode = user.risk_assessment_mode or "manual"

        holdings = list(self.holdings_repo.list_by_user(user.id))
        if not holdings:
            return PortfolioAnalysisResult(
                total_value=0,
                holdings=[],
                ai_analysis="Add some holdings to see your portfolio analysis!",
                metrics={
                    "sector_allocation": [],
                    "top_holdings": [],
                    "concentration_top3_pct": 0,
                    "diversification_score": 0
                },
                user_profile={
                    "age": user.age,
                    "risk_tolerance": user.risk_tolerance,
                    "risk_assessment_mode": risk_mode,
                    "retirement_years": user.retirement_years,
                    "obligations_amount": user.obligations_amount
                },
                cached=False,
                profile=profile
            )

        portfolio_summary: list[dict] = []
        total_value = 0.0

        for holding in holdings:
            stock = self.stock_repo.get(holding.ticker)
            if not stock:
                try:
                    self.market_data.get_quote(
                        holding.ticker,
                        now_utc,
                        lambda *_: False
                    )
                    stock = self.stock_repo.get(holding.ticker)
                except Exception as exc:
                    print(f"Could not fetch data for {holding.ticker}: {exc}")
                    continue

            if not stock:
                continue

            current_value = holding.shares * stock.current_price
            cost_basis = holding.shares * holding.avg_price
            gain_loss = current_value - cost_basis
            gain_loss_pct = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0

            portfolio_summary.append({
                "ticker": holding.ticker,
                "shares": holding.shares,
                "avg_price": holding.avg_price,
                "current_price": stock.current_price,
                "current_value": current_value,
                "gain_loss": gain_loss,
                "gain_loss_pct": gain_loss_pct,
                "sector": stock.sector or "Unknown"
            })

            total_value += current_value

        tickers = [h["ticker"] for h in portfolio_summary]
        tech_stocks = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "META", "AMZN"]
        tech_count = sum(1 for t in tickers if t in tech_stocks)

        concentration = tech_count / len(tickers) if tickers else 0
        if concentration > 0.6:
            diversification_note = "Your portfolio is heavily concentrated in technology. Consider diversifying into healthcare or utilities."
        else:
            diversification_note = "Your portfolio shows good sector diversification."

        cached = False
        if profile and profile.portfolio_analysis and profile.portfolio_analysis_at:
            last_at = profile.portfolio_analysis_at
            if last_at.tzinfo is None:
                last_at = last_at.replace(tzinfo=timezone.utc)
            if (now_utc - last_at).total_seconds() < cooldown_seconds:
                cached = True

        if cached:
            ai_analysis = profile.portfolio_analysis or ""
        else:
            obligations_amount = user.obligations_amount or 0
            obligations_text = (
                f"monthly obligations around ${obligations_amount:,.0f}"
                if obligations_amount
                else "no major obligations reported"
            )
            ai_analysis = f"""Portfolio Analysis Summary:

Overall Assessment:
{diversification_note}

Holdings Breakdown:
{chr(10).join([f"• {h['ticker']}: ${h['current_value']:.2f} ({h['gain_loss_pct']:+.1f}%)" for h in portfolio_summary])}

Key Recommendations:
1. Review your positions regularly to maintain target allocation.
2. Consider tax-loss harvesting on underperforming positions.
3. Keep your long-term perspective with {user.retirement_years} years until retirement and {obligations_text}.

Risk Assessment: Your {user.risk_tolerance} risk tolerance ({risk_mode} assessment) is {"well-suited" if user.retirement_years > 20 else "slightly aggressive"} for your timeline."""
            self.analysis.cache_analysis(user.id, ai_analysis, now_utc)

        sector_totals: dict[str, float] = {}
        for holding in portfolio_summary:
            sector = holding.get("sector") or "Unknown"
            sector_totals[sector] = sector_totals.get(sector, 0) + holding["current_value"]
        sector_allocation = [
            {"sector": sector, "value": value, "pct": (value / total_value * 100) if total_value else 0}
            for sector, value in sorted(sector_totals.items(), key=lambda item: item[1], reverse=True)
        ]

        sorted_holdings = sorted(portfolio_summary, key=lambda h: h["current_value"], reverse=True)
        top_holdings = [
            {
                "ticker": h["ticker"],
                "value": h["current_value"],
                "pct": (h["current_value"] / total_value * 100) if total_value else 0
            }
            for h in sorted_holdings[:5]
        ]
        concentration_top3 = sum(h["current_value"] for h in sorted_holdings[:3]) / total_value * 100 if total_value else 0
        diversification_score = max(0, min(100, 100 - concentration_top3))

        metrics = MetricsPayload(
            sector_allocation=sector_allocation,
            top_holdings=top_holdings,
            concentration_top3_pct=concentration_top3,
            diversification_score=diversification_score
        )
        self.analysis.cache_metrics(user.id, metrics)

        return PortfolioAnalysisResult(
            total_value=total_value,
            holdings=portfolio_summary,
            ai_analysis=ai_analysis,
            metrics={
                "sector_allocation": sector_allocation,
                "top_holdings": top_holdings,
                "concentration_top3_pct": concentration_top3,
                "diversification_score": diversification_score
            },
            user_profile={
                "age": user.age,
                "risk_tolerance": user.risk_tolerance,
                "risk_assessment_mode": risk_mode,
                "retirement_years": user.retirement_years,
                "obligations_amount": user.obligations_amount
            },
            cached=cached,
            profile=profile
        )

    def compute_metrics_only(self, user: AnalysisUser) -> dict:
        holdings = list(self.holdings_repo.list_by_user(user.id))
        if not holdings:
            metrics = {
                "sector_allocation": [],
                "top_holdings": [],
                "concentration_top3_pct": 0,
                "diversification_score": 0
            }
            self.analysis.cache_metrics(user.id, MetricsPayload(**metrics))
            return metrics

        portfolio_summary: list[dict] = []
        total_value = 0.0

        for holding in holdings:
            stock = self.stock_repo.get(holding.ticker)
            if not stock or stock.current_price is None:
                continue

            current_value = holding.shares * stock.current_price
            portfolio_summary.append({
                "ticker": holding.ticker,
                "current_value": current_value,
                "sector": stock.sector or "Unknown"
            })
            total_value += current_value

        sector_totals: dict[str, float] = {}
        for holding in portfolio_summary:
            sector = holding.get("sector") or "Unknown"
            sector_totals[sector] = sector_totals.get(sector, 0) + holding["current_value"]
        sector_allocation = [
            {"sector": sector, "value": value, "pct": (value / total_value * 100) if total_value else 0}
            for sector, value in sorted(sector_totals.items(), key=lambda item: item[1], reverse=True)
        ]

        sorted_holdings = sorted(portfolio_summary, key=lambda h: h["current_value"], reverse=True)
        top_holdings = [
            {
                "ticker": h["ticker"],
                "value": h["current_value"],
                "pct": (h["current_value"] / total_value * 100) if total_value else 0
            }
            for h in sorted_holdings[:5]
        ]
        concentration_top3 = sum(h["current_value"] for h in sorted_holdings[:3]) / total_value * 100 if total_value else 0
        diversification_score = max(0, min(100, 100 - concentration_top3))

        metrics = {
            "sector_allocation": sector_allocation,
            "top_holdings": top_holdings,
            "concentration_top3_pct": concentration_top3,
            "diversification_score": diversification_score
        }
        self.analysis.cache_metrics(user.id, MetricsPayload(**metrics))
        return metrics

    def build_snapshot(self, user: AnalysisUser, now_utc: datetime) -> dict:
        holdings = list(self.holdings_repo.list_by_user(user.id))
        holdings_snapshot = []
        for holding in holdings:
            stock = self.stock_repo.get(holding.ticker)
            current_price = stock.current_price if stock else None
            current_value = None
            if current_price is not None:
                current_value = holding.shares * current_price
            holdings_snapshot.append({
                "ticker": holding.ticker,
                "shares": holding.shares,
                "avg_price": holding.avg_price,
                "current_price": current_price,
                "current_value": current_value,
                "sector": stock.sector if stock and stock.sector else "Unknown",
                "asset_type": holding.asset_type,
            })

        metrics = self.compute_metrics_only(user)
        profile = self.analysis.get_cached(user.id)

        return {
            "generated_at": now_utc,
            "profile": {
                "age": user.age,
                "risk_tolerance": user.risk_tolerance,
                "risk_assessment_mode": user.risk_assessment_mode or "manual",
                "retirement_years": user.retirement_years,
                "obligations_amount": user.obligations_amount,
            },
            "holdings": holdings_snapshot,
            "metrics": metrics,
            "transcripts": profile.portfolio_transcripts if profile else None,
            "transcripts_quarter": profile.portfolio_transcripts_quarter if profile else None,
        }
