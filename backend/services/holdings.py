from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .repositories import HoldingsRepository, HoldingRecord


@dataclass
class HoldingInput:
    ticker: str
    shares: float
    avg_price: float
    asset_type: str | None = None


class HoldingsService:
    def __init__(self, repo: HoldingsRepository) -> None:
        self.repo = repo

    def list_holdings(self, user_id: int) -> List[HoldingRecord]:
        return list(self.repo.list_by_user(user_id))

    def add_or_merge(self, user_id: int, holding: HoldingInput) -> HoldingRecord:
        existing = self.repo.get_by_ticker(user_id, holding.ticker)
        if existing:
            total_shares = existing.shares + holding.shares
            new_avg = ((existing.shares * existing.avg_price) + (holding.shares * holding.avg_price)) / total_shares
            updated = HoldingRecord(
                id=existing.id,
                user_id=user_id,
                ticker=existing.ticker,
                shares=total_shares,
                avg_price=new_avg,
                asset_type=existing.asset_type
            )
            return self.repo.update(updated)

        return self.repo.create(HoldingRecord(
            id=0,
            user_id=user_id,
            ticker=holding.ticker,
            shares=holding.shares,
            avg_price=holding.avg_price,
            asset_type=holding.asset_type
        ))

    def replace_holdings(self, user_id: int, holdings: Iterable[HoldingInput]) -> List[HoldingRecord]:
        # Repository doesn't expose delete-all, so caller should handle if needed.
        created = []
        for holding in holdings:
            created.append(self.repo.create(HoldingRecord(
                id=0,
                user_id=user_id,
                ticker=holding.ticker,
                shares=holding.shares,
                avg_price=holding.avg_price,
                asset_type=holding.asset_type
            )))
        return created

    def update_holding(self, user_id: int, holding_id: int, holding: HoldingInput) -> HoldingRecord:
        return self.repo.update(HoldingRecord(
            id=holding_id,
            user_id=user_id,
            ticker=holding.ticker,
            shares=holding.shares,
            avg_price=holding.avg_price,
            asset_type=holding.asset_type
        ))

    def delete_holding(self, user_id: int, holding_id: int) -> None:
        self.repo.delete(holding_id, user_id)


def normalize_bulk_holdings(holdings: Iterable[HoldingInput]) -> List[HoldingInput]:
    grouped: dict[str, HoldingInput] = {}
    for item in holdings:
        ticker = item.ticker.upper()
        if ticker in grouped:
            existing = grouped[ticker]
            total_shares = existing.shares + item.shares
            weighted_avg = ((existing.shares * existing.avg_price) + (item.shares * item.avg_price)) / total_shares
            grouped[ticker] = HoldingInput(
                ticker=ticker,
                shares=total_shares,
                avg_price=weighted_avg,
                asset_type=existing.asset_type
            )
        else:
            grouped[ticker] = HoldingInput(
                ticker=ticker,
                shares=item.shares,
                avg_price=item.avg_price,
                asset_type=item.asset_type
            )
    return list(grouped.values())
