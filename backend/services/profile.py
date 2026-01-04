from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .repositories import UserRepository, UserRecord, ProfileRepository, ProfileRecord


@dataclass
class ProfileCreateInput:
    supabase_user_id: str
    age: int
    income: float
    risk_tolerance: str
    risk_assessment_mode: str
    retirement_years: int
    obligations_amount: Optional[float] = None


@dataclass
class ProfileUpdateInput:
    age: int
    income: float
    risk_tolerance: str
    risk_assessment_mode: str
    retirement_years: int
    obligations_amount: Optional[float] = None


class ProfileService:
    def __init__(self, users: UserRepository, profiles: ProfileRepository) -> None:
        self.users = users
        self.profiles = profiles

    def get_by_supabase_id(self, supabase_user_id: str) -> UserRecord | None:
        return self.users.get_by_supabase_id(supabase_user_id)

    def get_by_id(self, user_id: int) -> UserRecord | None:
        return self.users.get_by_id(user_id)

    def create_profile(self, data: ProfileCreateInput, ai_analysis: str) -> UserRecord:
        user = self.users.create(UserRecord(
            id=0,
            supabase_user_id=data.supabase_user_id,
            age=data.age,
            income=data.income,
            risk_tolerance=data.risk_tolerance,
            risk_assessment_mode=data.risk_assessment_mode,
            retirement_years=data.retirement_years,
            obligations_amount=data.obligations_amount
        ))
        profile = ProfileRecord(
            user_id=user.id,
            ai_analysis=ai_analysis
        )
        self.profiles.save(profile)
        return user

    def update_profile(self, user_id: int, data: ProfileUpdateInput) -> UserRecord:
        user = self.users.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        updated = UserRecord(
            id=user.id,
            supabase_user_id=user.supabase_user_id,
            age=data.age,
            income=data.income,
            risk_tolerance=data.risk_tolerance,
            risk_assessment_mode=data.risk_assessment_mode,
            retirement_years=data.retirement_years,
            obligations_amount=data.obligations_amount
        )
        return self.users.update(updated)

    def clear_analysis_cache(self, user_id: int) -> None:
        profile = self.profiles.get(user_id)
        if not profile:
            return
        profile.portfolio_analysis = None
        profile.portfolio_analysis_at = None
        self.profiles.save(profile)


def build_profile_ai_analysis(
    age: int,
    retirement_years: int,
    risk_tolerance: str,
    obligations_amount: float,
) -> str:
    obligations_text = (
        f"monthly obligations around ${obligations_amount:,.0f}"
        if obligations_amount
        else "no major obligations reported"
    )
    return f"""Based on your profile (age {age}, {retirement_years} years to retirement, {risk_tolerance} risk tolerance, {obligations_text}):

Recommended Allocation:
- Equities: 80%
- Bonds: 15%
- Cash: 5%

Key Recommendations:
1. With {retirement_years} years until retirement, you have time to ride out market volatility
2. Your {risk_tolerance} risk tolerance aligns with your timeline and obligations
3. Consider diversifying across large-cap, mid-cap, and international stocks
4. Begin gradually increasing bond allocation as you approach retirement

Focus sectors: Technology, Healthcare, Consumer Discretionary, Financials"""
