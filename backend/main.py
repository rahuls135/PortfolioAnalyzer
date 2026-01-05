from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from datetime import datetime, timezone, timedelta, time
from typing import List, Optional
import time as time_module
import threading
import os
import re
from zoneinfo import ZoneInfo
from database import get_db, engine, Base
import models
from auth import get_current_user, get_supabase_user_id
from services import (
    HoldingInput,
    normalize_bulk_holdings,
    ProfileCreateInput,
    ProfileUpdateInput,
    build_profile_ai_analysis,
    compute_risk_tolerance,
    get_profile_service,
    get_profile_repository,
    get_market_data_service,
    get_transcript_service,
    get_holdings_service,
    get_analysis_service,
    get_portfolio_analysis_service,
    get_ticker_validation_service,
    AnalysisUser,
    TickerUniverseCache,
)

app = FastAPI()

# Allow frontend to make requests
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "")
ALLOW_ORIGINS = [o.strip() for o in FRONTEND_ORIGINS.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class UserCreate(BaseModel):
    age: int
    income: float
    risk_tolerance: Optional[str] = None
    risk_assessment_mode: str = "manual"
    retirement_years: int
    obligations_amount: Optional[float] = None

class UserUpdate(BaseModel):
    age: Optional[int] = None
    income: Optional[float] = None
    risk_tolerance: Optional[str] = None
    risk_assessment_mode: Optional[str] = None
    retirement_years: Optional[int] = None
    obligations_amount: Optional[float] = None

class UserResponse(BaseModel):
    id: int
    supabase_user_id: str
    age: int
    income: float
    risk_tolerance: str
    risk_assessment_mode: str
    retirement_years: int
    obligations_amount: Optional[float] = None
    ai_analysis: Optional[str] = None
    
    class Config:
        from_attributes = True

class HoldingBase(BaseModel):
    ticker: str
    shares: float
    avg_price: float

    @validator("ticker")
    def validate_ticker(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned or not cleaned.isalnum() or len(cleaned) > 10:
            raise ValueError("Ticker must be alphanumeric and up to 10 characters")
        return cleaned

    @validator("shares", "avg_price")
    def validate_positive_numbers(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Shares and avg price must be positive numbers")
        return value

class HoldingCreate(HoldingBase):
    pass

class HoldingBulkRequest(BaseModel):
    mode: str = "merge"  # merge or replace
    holdings: List[HoldingCreate]

class HoldingResponse(HoldingBase):
    id: int
    asset_type: Optional[str] = None
    class Config:
        from_attributes = True

class EarningsTranscriptResponse(BaseModel):
    ticker: str
    quarter: str
    summary: str
    fetched_at: Optional[datetime] = None

class AnalysisCacheResponse(BaseModel):
    ai_analysis: str
    analysis_meta: dict
    metrics: Optional[dict] = None
    transcripts: Optional[dict] = None
    transcripts_quarter: Optional[str] = None

class AnalysisTranscriptCache(BaseModel):
    quarter: str
    summaries: dict

@app.get("/")
def read_root():
    return {"message": "Portfolio Analyzer API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

MARKET_TZ = ZoneInfo("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
ANALYSIS_COOLDOWN_SECONDS = int(os.getenv("ANALYSIS_COOLDOWN_SECONDS", str(24 * 60 * 60)))

def _last_market_close(now_et: datetime) -> datetime:
    if now_et.weekday() >= 5:
        d = now_et.date()
        while d.weekday() >= 5:
            d -= timedelta(days=1)
        return datetime.combine(d, MARKET_CLOSE, tzinfo=MARKET_TZ)
    if now_et.time() >= MARKET_CLOSE:
        return datetime.combine(now_et.date(), MARKET_CLOSE, tzinfo=MARKET_TZ)
    d = now_et.date() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return datetime.combine(d, MARKET_CLOSE, tzinfo=MARKET_TZ)

def _next_market_open(now_et: datetime) -> datetime:
    if now_et.weekday() >= 5:
        d = now_et.date()
        while d.weekday() >= 5:
            d += timedelta(days=1)
        return datetime.combine(d, MARKET_OPEN, tzinfo=MARKET_TZ)
    if now_et.time() < MARKET_OPEN:
        return datetime.combine(now_et.date(), MARKET_OPEN, tzinfo=MARKET_TZ)
    d = now_et.date() + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return datetime.combine(d, MARKET_OPEN, tzinfo=MARKET_TZ)

def _market_closed_cache_valid(last_updated_utc: datetime, now_utc: datetime) -> bool:
    now_et = now_utc.astimezone(MARKET_TZ)
    if now_et.weekday() < 5 and MARKET_OPEN <= now_et.time() < MARKET_CLOSE:
        return False
    last_close = _last_market_close(now_et)
    next_open = _next_market_open(now_et)
    last_et = last_updated_utc.astimezone(MARKET_TZ)
    return last_et >= last_close and now_et < next_open

_AV_LOCK = threading.Lock()
_AV_LAST_CALL = 0.0

def _av_throttle(min_interval_seconds: float = 1.1) -> None:
    global _AV_LAST_CALL
    with _AV_LOCK:
        now = time_module.monotonic()
        wait_for = (_AV_LAST_CALL + min_interval_seconds) - now
        if wait_for > 0:
            time_module.sleep(wait_for)
        _AV_LAST_CALL = time_module.monotonic()

_TICKER_UNIVERSE_CACHE: dict[str, TickerUniverseCache] = {}

def _validate_ticker(ticker: str, db: Session) -> bool:
    try:
        service = get_ticker_validation_service(db, _av_throttle, _TICKER_UNIVERSE_CACHE)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    try:
        return service.validate(ticker)
    except RuntimeError as exc:
        message = str(exc)
        if "Stock price not found" in message:
            return False
        raise HTTPException(status_code=429, detail=message)

@app.post("/api/holdings", response_model=HoldingResponse)
def upsert_holding(
    holding_in: HoldingCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticker_upper = holding_in.ticker.upper()

    if not _validate_ticker(ticker_upper, db):
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker_upper}")

    try:
        market_data = get_market_data_service(db, _av_throttle)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    service = get_holdings_service(db)
    try:
        asset_type = market_data.get_asset_type(ticker_upper)
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    record = service.add_or_merge(
        current_user.id,
        HoldingInput(
            ticker=ticker_upper,
            shares=holding_in.shares,
            avg_price=holding_in.avg_price,
            asset_type=asset_type
        )
    )
    return record

@app.patch("/api/holdings/{holding_id}", response_model=HoldingResponse)
def update_holding(
    holding_id: int, 
    update: HoldingCreate,  # Reusing the class you already have
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print("updating holding...")
    service = get_holdings_service(db)
    print("got service")
    try:
        record = service.update_holding(
            current_user.id,
            holding_id,
            HoldingInput(
                ticker=update.ticker.upper(),
                shares=update.shares,
                avg_price=update.avg_price
            )
        )
        print("service updated holding")
    except ValueError:
        raise HTTPException(status_code=404, detail="Holding not found")
    return record

@app.post("/api/holdings/bulk", response_model=List[HoldingResponse])
def bulk_upsert_holdings(
    payload: HoldingBulkRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mode = (payload.mode or "merge").lower()
    if mode not in {"merge", "replace"}:
        raise HTTPException(status_code=400, detail="Mode must be 'merge' or 'replace'")

    normalized_inputs = normalize_bulk_holdings([
        HoldingInput(
            ticker=item.ticker.upper(),
            shares=item.shares,
            avg_price=item.avg_price
        )
        for item in payload.holdings
    ])
    try:
        market_data = get_market_data_service(db, _av_throttle)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    asset_types: dict[str, str] = {}
    for item in normalized_inputs:
        ticker = item.ticker.upper()
        if not _validate_ticker(ticker, db):
            raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker}")
        try:
            asset_types[ticker] = market_data.get_asset_type(ticker)
        except RuntimeError as exc:
            raise HTTPException(status_code=429, detail=str(exc))

    service = get_holdings_service(db)
    inputs = [
        HoldingInput(
            ticker=item.ticker.upper(),
            shares=item.shares,
            avg_price=item.avg_price,
            asset_type=asset_types.get(item.ticker.upper())
        )
        for item in normalized_inputs
    ]

    if mode == "replace":
        db.query(models.Holding).filter(models.Holding.user_id == current_user.id).delete(synchronize_session=False)
        service.replace_holdings(current_user.id, inputs)
        return service.list_holdings(current_user.id)

    for item in inputs:
        service.add_or_merge(current_user.id, item)
    return service.list_holdings(current_user.id)

@app.get("/api/tickers/validate/{ticker}")
def validate_ticker(
    ticker: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cleaned = ticker.strip().upper()
    if not cleaned or not cleaned.isalnum() or len(cleaned) > 10:
        return {"ticker": cleaned, "valid": False}
    is_valid = _validate_ticker(cleaned, db)
    return {"ticker": cleaned, "valid": is_valid}

# Get all holdings for a user
@app.get("/api/holdings", response_model=List[HoldingResponse])
def get_holdings(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    service = get_holdings_service(db)
    return service.list_holdings(current_user.id)

# Delete a holding
@app.delete("/api/holdings/{holding_id}")
def delete_holding(
    holding_id: int, 
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Delete a specific holding if owned by the user."""
    service = get_holdings_service(db)
    try:
        service.delete_holding(current_user.id, holding_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Holding not found")
    return {"message": "Holding deleted"}

@app.get("/api/stocks/{ticker}")
def get_stock_data(
    ticker: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticker = ticker.strip().upper()
    if not ticker or not ticker.isalnum() or len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    try:
        service = get_market_data_service(db, _av_throttle)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    now_utc = datetime.now(timezone.utc)

    def _cache_valid(last_updated: datetime, now_time: datetime) -> bool:
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        return (now_time - last_updated).total_seconds() < 86400 or _market_closed_cache_valid(last_updated, now_time)

    try:
        quote, cached = service.get_quote(ticker, now_utc, _cache_valid)
    except RuntimeError as exc:
        message = str(exc)
        if "Stock price not found" in message:
            raise HTTPException(status_code=404, detail="Stock price not found")
        raise HTTPException(status_code=429, detail=message)

    return {
        "ticker": quote.ticker,
        "current_price": quote.current_price,
        "sector": quote.sector or "Unknown",
        "asset_type": quote.asset_type,
        "cached": cached
    }

@app.post("/api/users", response_model=UserResponse)
def create_user_profile(
    user: UserCreate,
    supabase_user_id: str = Depends(get_supabase_user_id),
    db: Session = Depends(get_db),
):
    profile_service = get_profile_service(db)
    if profile_service.get_by_supabase_id(supabase_user_id):
        raise HTTPException(status_code=400, detail="User profile already exists")
    
    obligations_amount = float(user.obligations_amount or 0)
    if obligations_amount < 0:
        raise HTTPException(status_code=400, detail="Obligations amount must be a positive number")
    risk_mode = user.risk_assessment_mode or "manual"
    if risk_mode not in {"manual", "ai"}:
        raise HTTPException(status_code=400, detail="Invalid risk assessment mode")

    if risk_mode == "ai":
        risk_tolerance = compute_risk_tolerance(
            age=user.age,
            income=user.income,
            retirement_years=user.retirement_years,
            obligations_amount=obligations_amount
        )
    else:
        if not user.risk_tolerance:
            raise HTTPException(status_code=400, detail="Risk tolerance is required for manual mode")
        risk_tolerance = user.risk_tolerance

    ai_analysis = build_profile_ai_analysis(
        age=user.age,
        retirement_years=user.retirement_years,
        risk_tolerance=risk_tolerance,
        obligations_amount=obligations_amount
    )

    created = profile_service.create_profile(ProfileCreateInput(
        supabase_user_id=supabase_user_id,
        age=user.age,
        income=user.income,
        risk_tolerance=risk_tolerance,
        risk_assessment_mode=risk_mode,
        retirement_years=user.retirement_years,
        obligations_amount=obligations_amount
    ), ai_analysis)

    return {
        "id": created.id,
        "supabase_user_id": created.supabase_user_id,
        "age": created.age,
        "income": created.income,
        "risk_tolerance": created.risk_tolerance,
        "risk_assessment_mode": created.risk_assessment_mode,
        "retirement_years": created.retirement_years,
        "obligations_amount": created.obligations_amount,
        "ai_analysis": ai_analysis
    }

@app.get("/api/analysis")
def analyze_portfolio(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Perform portfolio math and AI analysis for the logged-in user."""
    now_utc = datetime.now(timezone.utc)
    analysis_pipeline = get_portfolio_analysis_service(db, _av_throttle)
    result = analysis_pipeline.analyze(
        AnalysisUser(
            id=current_user.id,
            age=current_user.age,
            risk_tolerance=current_user.risk_tolerance,
            risk_assessment_mode=current_user.risk_assessment_mode or "manual",
            retirement_years=current_user.retirement_years,
            obligations_amount=current_user.obligations_amount
        ),
        now_utc,
        ANALYSIS_COOLDOWN_SECONDS
    )
    analysis_service = get_analysis_service(db)

    return {
        "total_value": result.total_value,
        "holdings": result.holdings,
        "ai_analysis": result.ai_analysis,
        "metrics": result.metrics,
        "user_profile": result.user_profile,
        "analysis_meta": analysis_service.build_meta(
            result.profile,
            now_utc,
            ANALYSIS_COOLDOWN_SECONDS,
            cached=result.cached
        )
    }

@app.get("/api/analysis/cached", response_model=AnalysisCacheResponse)
def get_cached_analysis(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis_service = get_analysis_service(db)
    profile = analysis_service.get_cached(current_user.id)
    if not profile or not profile.portfolio_analysis:
        raise HTTPException(status_code=404, detail="No cached analysis available")
    now_utc = datetime.now(timezone.utc)
    return {
        "ai_analysis": profile.portfolio_analysis,
        "analysis_meta": analysis_service.build_meta(
            profile,
            now_utc,
            ANALYSIS_COOLDOWN_SECONDS,
            cached=True
        ),
        "metrics": profile.portfolio_metrics,
        "transcripts": profile.portfolio_transcripts,
        "transcripts_quarter": profile.portfolio_transcripts_quarter
    }

@app.post("/api/analysis/cached/transcripts")
def cache_transcripts(
    payload: AnalysisTranscriptCache,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis_service = get_analysis_service(db)
    analysis_service.cache_transcripts(current_user.id, payload.quarter, payload.summaries)
    return {"status": "ok"}

@app.get("/api/users/me", response_model=UserResponse)
def get_my_profile(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Fetch the logged-in user's profile and AI analysis."""
    profile_repo = get_profile_repository(db)
    profile = profile_repo.get(current_user.id)
    
    return {
        "id": current_user.id,
        "supabase_user_id": current_user.supabase_user_id,
        "age": current_user.age,
        "income": current_user.income,
        "risk_tolerance": current_user.risk_tolerance,
        "risk_assessment_mode": current_user.risk_assessment_mode or "manual",
        "retirement_years": current_user.retirement_years,
        "obligations_amount": current_user.obligations_amount,
        "ai_analysis": profile.ai_analysis if profile else None
    }

@app.patch("/api/users/me", response_model=UserResponse)
def update_my_profile(
    update: UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    updates = update.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No profile fields provided")

    obligations_amount = updates.get("obligations_amount", current_user.obligations_amount)
    if obligations_amount is not None and obligations_amount < 0:
        raise HTTPException(status_code=400, detail="Obligations amount must be a positive number")

    risk_mode = updates.get("risk_assessment_mode", current_user.risk_assessment_mode or "manual")
    if risk_mode not in {"manual", "ai"}:
        raise HTTPException(status_code=400, detail="Invalid risk assessment mode")

    age = updates.get("age", current_user.age)
    income = updates.get("income", current_user.income)
    retirement_years = updates.get("retirement_years", current_user.retirement_years)

    if risk_mode == "ai":
        risk_tolerance = compute_risk_tolerance(
            age=age,
            income=income,
            retirement_years=retirement_years,
            obligations_amount=float(obligations_amount or 0)
        )
    else:
        risk_tolerance = updates.get("risk_tolerance", current_user.risk_tolerance)
        if not risk_tolerance:
            raise HTTPException(status_code=400, detail="Risk tolerance is required for manual mode")

    profile_service = get_profile_service(db)
    updated = profile_service.update_profile(current_user.id, ProfileUpdateInput(
        age=age,
        income=income,
        risk_tolerance=risk_tolerance,
        risk_assessment_mode=risk_mode,
        retirement_years=retirement_years,
        obligations_amount=obligations_amount
    ))
    profile_service.clear_analysis_cache(current_user.id)
    profile = get_profile_repository(db).get(current_user.id)

    return {
        "id": updated.id,
        "supabase_user_id": updated.supabase_user_id,
        "age": updated.age,
        "income": updated.income,
        "risk_tolerance": updated.risk_tolerance,
        "risk_assessment_mode": updated.risk_assessment_mode or "manual",
        "retirement_years": updated.retirement_years,
        "obligations_amount": updated.obligations_amount,
        "ai_analysis": profile.ai_analysis if profile else None
    }

@app.get("/api/earnings/transcripts/{ticker}", response_model=EarningsTranscriptResponse)
def get_earnings_transcript(
    ticker: str,
    quarter: str,
    fallback: Optional[int] = 0,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cleaned = ticker.strip().upper()
    if not cleaned or not cleaned.isalnum() or len(cleaned) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker format")
    if not quarter or not re.match(r"^\d{4}Q[1-4]$", quarter):
        raise HTTPException(status_code=400, detail="Quarter must be like 2024Q1")

    def previous_quarter(q: str) -> str:
        year = int(q[:4])
        quarter_num = int(q[-1])
        if quarter_num == 1:
            return f"{year - 1}Q4"
        return f"{year}Q{quarter_num - 1}"

    remaining = max(0, min(fallback or 0, 4))
    attempts = []
    current_quarter = quarter
    for _ in range(remaining + 1):
        attempts.append(current_quarter)
        current_quarter = previous_quarter(current_quarter)

    try:
        service = get_transcript_service(db, _av_throttle)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        record = service.get_summary(cleaned, quarter, fallback)
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except LookupError:
        raise HTTPException(status_code=404, detail="Transcript not found")

    return {
        "ticker": record.ticker,
        "quarter": record.quarter,
        "summary": record.summary or "",
        "fetched_at": record.fetched_at
    }
