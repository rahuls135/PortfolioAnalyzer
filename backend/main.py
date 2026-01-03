from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from datetime import datetime, timezone, timedelta, time
from typing import List, Optional, Set
import time as time_module
import threading
import os
import requests
import re
from zoneinfo import ZoneInfo
from database import get_db, engine, Base
import models
from auth import get_current_user, get_supabase_user_id

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

@app.get("/")
def read_root():
    return {"message": "Portfolio Analyzer API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

MARKET_TZ = ZoneInfo("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
ANALYSIS_COOLDOWN_SECONDS = 24 * 60 * 60

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

def _analysis_meta(profile: Optional[models.UserProfile], now_utc: datetime, cached: bool) -> dict:
    last_at = None
    next_at = None
    remaining = 0

    if profile and profile.portfolio_analysis_at:
        last_at = profile.portfolio_analysis_at
        if last_at.tzinfo is None:
            last_at = last_at.replace(tzinfo=timezone.utc)
        next_at = last_at + timedelta(seconds=ANALYSIS_COOLDOWN_SECONDS)
        remaining = max(0, int((next_at - now_utc).total_seconds()))

    return {
        "cached": cached,
        "last_analysis_at": last_at.isoformat() if last_at else None,
        "next_available_at": next_at.isoformat() if next_at else None,
        "cooldown_remaining_seconds": remaining
    }

def _compute_risk_tolerance(age: int, income: float, retirement_years: int, obligations_amount: float) -> str:
    high_obligations = obligations_amount >= 2500
    low_obligations = obligations_amount <= 1000
    if retirement_years <= 10 or age >= 55 or high_obligations:
        return "conservative"
    if retirement_years >= 25 and income >= 100000 and low_obligations:
        return "aggressive"
    return "moderate"

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

_TICKER_UNIVERSE: Set[str] | None = None
_TICKER_UNIVERSE_MTIME: float | None = None

def _load_ticker_universe() -> Set[str] | None:
    global _TICKER_UNIVERSE, _TICKER_UNIVERSE_MTIME
    path = os.getenv("TICKER_UNIVERSE_PATH")
    if not path:
        return None
    try:
        stat = os.stat(path)
    except FileNotFoundError:
        return None
    if _TICKER_UNIVERSE is not None and _TICKER_UNIVERSE_MTIME == stat.st_mtime:
        return _TICKER_UNIVERSE
    tickers: Set[str] = set()
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            cleaned = line.strip().upper()
            if not cleaned or cleaned.startswith("#"):
                continue
            tickers.add(cleaned)
    _TICKER_UNIVERSE = tickers
    _TICKER_UNIVERSE_MTIME = stat.st_mtime
    return _TICKER_UNIVERSE

def _ticker_universe_enforced() -> bool:
    return os.getenv("TICKER_UNIVERSE_ENFORCE", "false").lower() == "true"

def _validate_ticker(ticker: str, db: Session) -> bool:
    universe = _load_ticker_universe()
    if universe is not None:
        if ticker not in universe:
            return False
        return True
    stock = db.query(models.StockData).filter(models.StockData.ticker == ticker).first()
    if stock and stock.current_price is not None:
        return True

    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Alpha Vantage API key not configured")

    _av_throttle()
    price_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={api_key}"
    price_res = requests.get(price_url).json()
    print("B - Invoking AV")
    print(price_res)
    if price_res.get("Note") or price_res.get("Information"):
        print("B - IN Here 429 Error!")
        raise HTTPException(status_code=429, detail="Alpha Vantage rate limit reached")

    quote = price_res.get("Global Quote") or {}
    price = quote.get("05. price")
    if not price:
        return False
    try:
        float(price)
    except (TypeError, ValueError):
        return False
    return True

def _fetch_overview_fields(ticker: str) -> dict:
    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Alpha Vantage API key not configured")
    _av_throttle()
    overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
    overview_res = requests.get(overview_url).json()
    print("C - Invoking AV")
    if overview_res.get("Note") or overview_res.get("Information"):
        message = overview_res.get("Note") or overview_res.get("Information")
        raise HTTPException(status_code=429, detail=f"Alpha Vantage response: {message}")
    return {
        "sector": overview_res.get("Sector", "Unknown"),
        "asset_type": overview_res.get("AssetType", "Unknown")
    }

def _get_asset_type(ticker: str, db: Session) -> str:
    stock = db.query(models.StockData).filter(models.StockData.ticker == ticker).first()
    if stock and stock.asset_type and stock.asset_type != "Unknown":
        return stock.asset_type
    overview = _fetch_overview_fields(ticker)
    asset_type = overview.get("asset_type", "Unknown")
    sector = overview.get("sector", "Unknown")
    if stock:
        if asset_type != "Unknown":
            stock.asset_type = asset_type
        if sector != "Unknown" and (not stock.sector or stock.sector == "Unknown"):
            stock.sector = sector
        db.commit()
        db.refresh(stock)
    else:
        stock = models.StockData(
            ticker=ticker,
            sector=sector,
            asset_type=asset_type,
            last_updated=datetime.now(timezone.utc)
        )
        db.add(stock)
        db.commit()
    return asset_type

def _summarize_transcript(text: str | list, max_sentences: int = 4, max_chars: int = 800) -> str:
    if not text:
        return ""
    if isinstance(text, list):
        text = " ".join(str(item) for item in text if item)
    sentences = re.split(r'(?<=[.!?])\s+', str(text).strip())
    summary = " ".join(sentences[:max_sentences]).strip()
    if len(summary) > max_chars:
        summary = summary[:max_chars].rstrip() + "..."
    return summary

def _normalize_bulk_holdings(holdings: List[HoldingCreate]) -> List[HoldingCreate]:
    grouped: dict[str, HoldingCreate] = {}
    for item in holdings:
        ticker = item.ticker.upper()
        if ticker in grouped:
            existing = grouped[ticker]
            total_shares = existing.shares + item.shares
            weighted_avg = ((existing.shares * existing.avg_price) + (item.shares * item.avg_price)) / total_shares
            grouped[ticker] = HoldingCreate(ticker=ticker, shares=total_shares, avg_price=weighted_avg)
        else:
            grouped[ticker] = HoldingCreate(ticker=ticker, shares=item.shares, avg_price=item.avg_price)
    return list(grouped.values())

@app.post("/api/holdings", response_model=HoldingResponse)
def upsert_holding(
    holding_in: HoldingCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticker_upper = holding_in.ticker.upper()

    # 1. Check if the user already owns this stock
    existing_holding = db.query(models.Holding).filter(
        models.Holding.user_id == current_user.id,
        models.Holding.ticker == ticker_upper
    ).first()

    if existing_holding:
        # 2. Update Logic: Calculate new Average Price
        # Formula: (Old Total Cost + New Total Cost) / Total Shares
        total_shares = existing_holding.shares + holding_in.shares
        
        old_cost = existing_holding.shares * existing_holding.avg_price
        new_cost = holding_in.shares * holding_in.avg_price
        
        new_avg_price = (old_cost + new_cost) / total_shares

        existing_holding.shares = total_shares
        existing_holding.avg_price = new_avg_price
        
        db.commit()
        db.refresh(existing_holding)
        return existing_holding
    
    if not _validate_ticker(ticker_upper, db):
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker_upper}")

    # 3. Insert Logic: Create a brand new record
    new_holding = models.Holding(
        user_id=current_user.id,
        ticker=ticker_upper,
        shares=holding_in.shares,
        avg_price=holding_in.avg_price,
        asset_type=_get_asset_type(ticker_upper, db)
    )

    db.add(new_holding)
    db.commit()
    db.refresh(new_holding)
    return new_holding

@app.patch("/api/holdings/{holding_id}", response_model=HoldingResponse)
def update_holding(
    holding_id: int, 
    update: HoldingCreate,  # Reusing the class you already have
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find the holding by ID and ensure it belongs to the user
    holding = db.query(models.Holding).filter(
        models.Holding.id == holding_id,
        models.Holding.user_id == current_user.id
    ).first()
    
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    
    # Update the values using the HoldingCreate model
    holding.shares = update.shares
    holding.avg_price = update.avg_price
    # If you want to allow ticker changes (typo fix):
    holding.ticker = update.ticker.upper()
    
    db.commit()
    db.refresh(holding)
    return holding

@app.post("/api/holdings/bulk", response_model=List[HoldingResponse])
def bulk_upsert_holdings(
    payload: HoldingBulkRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mode = (payload.mode or "merge").lower()
    if mode not in {"merge", "replace"}:
        raise HTTPException(status_code=400, detail="Mode must be 'merge' or 'replace'")

    normalized = _normalize_bulk_holdings(payload.holdings)
    asset_types: dict[str, str] = {}
    for item in normalized:
        ticker = item.ticker.upper()
        if not _validate_ticker(ticker, db):
            raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker}")
        asset_types[ticker] = _get_asset_type(ticker, db)

    if mode == "replace":
        db.query(models.Holding).filter(models.Holding.user_id == current_user.id).delete(synchronize_session=False)
        for item in normalized:
            db.add(models.Holding(
                user_id=current_user.id,
                ticker=item.ticker.upper(),
                shares=item.shares,
                avg_price=item.avg_price,
                asset_type=asset_types.get(item.ticker.upper())
            ))
        db.commit()
        return db.query(models.Holding).filter(models.Holding.user_id == current_user.id).all()

    existing = db.query(models.Holding).filter(models.Holding.user_id == current_user.id).all()
    existing_map = {h.ticker.upper(): h for h in existing}
    for item in normalized:
        ticker = item.ticker.upper()
        if ticker in existing_map:
            holding = existing_map[ticker]
            total_shares = holding.shares + item.shares
            holding.avg_price = ((holding.shares * holding.avg_price) + (item.shares * item.avg_price)) / total_shares
            holding.shares = total_shares
        else:
            db.add(models.Holding(
                user_id=current_user.id,
                ticker=ticker,
                shares=item.shares,
                avg_price=item.avg_price,
                asset_type=asset_types.get(ticker)
            ))
    db.commit()
    return db.query(models.Holding).filter(models.Holding.user_id == current_user.id).all()

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
    return db.query(models.Holding).filter(models.Holding.user_id == current_user.id).all()

# Delete a holding
@app.delete("/api/holdings/{holding_id}")
def delete_holding(
    holding_id: int, 
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Delete a specific holding if owned by the user."""
    holding = db.query(models.Holding).filter(
        models.Holding.id == holding_id,
        models.Holding.user_id == current_user.id
    ).first()
    
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    
    db.delete(holding)
    db.commit()
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
    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Alpha Vantage API key not configured")
    
    # 1. Check cache (24-hour rule)
    stock = db.query(models.StockData).filter(models.StockData.ticker == ticker).first()
    if stock and stock.last_updated and stock.current_price is not None:
        # Normalize timezone for comparison
        last_updated = stock.last_updated.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        if (now_utc - last_updated).total_seconds() < 86400 or _market_closed_cache_valid(last_updated, now_utc):
            return {
                "ticker": stock.ticker,
                "current_price": stock.current_price,
                "sector": stock.sector or "Unknown",
                "cached": True
            }
    
    # 2. Cache expired or missing: Fetch Price
    print(f"Alpha Vantage price fetch for {ticker}")
    _av_throttle()
    price_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={api_key}"
    price_res = requests.get(price_url).json()
    print("A - Invoking AV")
    
    if price_res.get("Note") or price_res.get("Information"):
        message = price_res.get("Note") or price_res.get("Information")
        print("A - IN Here 429 Error!")
        raise HTTPException(status_code=429, detail=f"Alpha Vantage response: {message}")
    if "Global Quote" not in price_res or not price_res["Global Quote"]:
        raise HTTPException(status_code=404, detail="Stock price not found")
    
    current_price = float(price_res["Global Quote"]["05. price"])

    # 3. Fetch Sector/Metadata (Alpha Vantage OVERVIEW)
    # Note: Free tier has rate limits, so we only do this if sector is missing
    sector = "Unknown"
    asset_type = "Unknown"
    if not stock or not stock.sector or stock.sector == "Unknown" or not stock.asset_type or stock.asset_type == "Unknown":
        print(f"Alpha Vantage overview fetch for {ticker}")
        overview = _fetch_overview_fields(ticker)
        sector = overview.get("sector", "Unknown")
        asset_type = overview.get("asset_type", "Unknown")

    # 4. Update Database
    if stock:
        stock.current_price = current_price
        if sector != "Unknown":
            stock.sector = sector
        if asset_type != "Unknown":
            stock.asset_type = asset_type
        stock.last_updated = datetime.now(timezone.utc)
    else:
        stock = models.StockData(
            ticker=ticker,
            current_price=current_price,
            sector=sector,
            asset_type=asset_type,
            last_updated=datetime.now(timezone.utc)
        )
        db.add(stock)
    
    db.commit()
    db.refresh(stock)
    
    return {
        "ticker": stock.ticker,
        "current_price": stock.current_price,
        "sector": stock.sector,
        "asset_type": stock.asset_type,
        "cached": False
    }

@app.post("/api/users", response_model=UserResponse)
def create_user_profile(
    user: UserCreate,
    supabase_user_id: str = Depends(get_supabase_user_id),
    db: Session = Depends(get_db),
):
    # Check if user already exists
    existing_user = db.query(models.User).filter(
        models.User.supabase_user_id == supabase_user_id
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="User profile already exists")
    
    obligations_amount = float(user.obligations_amount or 0)
    if obligations_amount < 0:
        raise HTTPException(status_code=400, detail="Obligations amount must be a positive number")
    risk_mode = user.risk_assessment_mode or "manual"
    if risk_mode not in {"manual", "ai"}:
        raise HTTPException(status_code=400, detail="Invalid risk assessment mode")

    if risk_mode == "ai":
        risk_tolerance = _compute_risk_tolerance(
            age=user.age,
            income=user.income,
            retirement_years=user.retirement_years,
            obligations_amount=obligations_amount
        )
    else:
        if not user.risk_tolerance:
            raise HTTPException(status_code=400, detail="Risk tolerance is required for manual mode")
        risk_tolerance = user.risk_tolerance

    # Create user
    db_user = models.User(
        supabase_user_id=supabase_user_id,
        age=user.age,
        income=user.income,
        risk_tolerance=risk_tolerance,
        risk_assessment_mode=risk_mode,
        retirement_years=user.retirement_years,
        obligations_amount=obligations_amount
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Mock AI analysis
    obligations_text = f"monthly obligations around ${obligations_amount:,.0f}" if obligations_amount else "no major obligations reported"
    ai_analysis = f"""Based on your profile (age {user.age}, {user.retirement_years} years to retirement, {risk_tolerance} risk tolerance, {obligations_text}):

Recommended Allocation:
- Equities: 80%
- Bonds: 15%
- Cash: 5%

Key Recommendations:
1. With {user.retirement_years} years until retirement, you have time to ride out market volatility
2. Your {risk_tolerance} risk tolerance aligns with your timeline and obligations
3. Consider diversifying across large-cap, mid-cap, and international stocks
4. Begin gradually increasing bond allocation as you approach retirement

Focus sectors: Technology, Healthcare, Consumer Discretionary, Financials"""
    
    db_profile = models.UserProfile(
        user_id=db_user.id,
        ai_analysis=ai_analysis
    )
    db.add(db_profile)
    db.commit()
    
    return {
        "id": db_user.id,
        "supabase_user_id": db_user.supabase_user_id,
        "age": db_user.age,
        "income": db_user.income,
        "risk_tolerance": db_user.risk_tolerance,
        "risk_assessment_mode": db_user.risk_assessment_mode,
        "retirement_years": db_user.retirement_years,
        "obligations_amount": db_user.obligations_amount,
        "ai_analysis": ai_analysis
    }

@app.get("/api/analysis")
def analyze_portfolio(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Perform portfolio math and AI analysis for the logged-in user."""
    now_utc = datetime.now(timezone.utc)
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    risk_mode = current_user.risk_assessment_mode or "manual"

    # 1. Fetch holdings for the user identified by JWT
    holdings = db.query(models.Holding).filter(models.Holding.user_id == current_user.id).all()
    
    if not holdings:
        return {
            "total_value": 0,
            "holdings": [],
            "ai_analysis": "Add some holdings to see your portfolio analysis!",
            "metrics": {
                "sector_allocation": [],
                "top_holdings": [],
                "concentration_top3_pct": 0,
                "diversification_score": 0
            },
            "user_profile": {
                "age": current_user.age,
                "risk_tolerance": current_user.risk_tolerance,
                "risk_assessment_mode": risk_mode,
                "retirement_years": current_user.retirement_years,
                "obligations_amount": current_user.obligations_amount
            },
            "analysis_meta": _analysis_meta(profile, now_utc, cached=False)
        }

    portfolio_summary = []
    total_value = 0
    
    for holding in holdings:
        # 2. Get stock price (Check cache first)
        stock = db.query(models.StockData).filter(models.StockData.ticker == holding.ticker).first()
        
        if not stock:
            try:
                # This triggers the Alpha Vantage fetch logic
                get_stock_data(holding.ticker, db)
                stock = db.query(models.StockData).filter(models.StockData.ticker == holding.ticker).first()
            except Exception as e:
                print(f"Could not fetch data for {holding.ticker}: {e}")
                continue
        
        if not stock:
            continue

        # 3. Math calculations
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
            "sector": getattr(stock, 'sector', 'Unknown') # Safely handle missing sector
        })
        
        total_value += current_value
    
    # 4. Analysis Logic (using current_user)
    tickers = [h['ticker'] for h in portfolio_summary]
    tech_stocks = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'META', 'AMZN']
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
        if (now_utc - last_at).total_seconds() < ANALYSIS_COOLDOWN_SECONDS:
            cached = True

    if cached:
        ai_analysis = profile.portfolio_analysis
    else:
        obligations_amount = current_user.obligations_amount or 0
        obligations_text = f"monthly obligations around ${obligations_amount:,.0f}" if obligations_amount else "no major obligations reported"
        ai_analysis = f"""Portfolio Analysis Summary:

Overall Assessment:
{diversification_note}

Holdings Breakdown:
{chr(10).join([f"• {h['ticker']}: ${h['current_value']:.2f} ({h['gain_loss_pct']:+.1f}%)" for h in portfolio_summary])}

Key Recommendations:
1. Review your positions regularly to maintain target allocation.
2. Consider tax-loss harvesting on underperforming positions.
3. Keep your long-term perspective with {current_user.retirement_years} years until retirement and {obligations_text}.

Risk Assessment: Your {current_user.risk_tolerance} risk tolerance ({risk_mode} assessment) is {"well-suited" if current_user.retirement_years > 20 else "slightly aggressive"} for your timeline."""
        if not profile:
            profile = models.UserProfile(user_id=current_user.id)
            db.add(profile)
        profile.portfolio_analysis = ai_analysis
        profile.portfolio_analysis_at = now_utc
        db.commit()

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

    return {
        "total_value": total_value,
        "holdings": portfolio_summary,
        "ai_analysis": ai_analysis,
        "metrics": {
            "sector_allocation": sector_allocation,
            "top_holdings": top_holdings,
            "concentration_top3_pct": concentration_top3,
            "diversification_score": diversification_score
        },
        "user_profile": {
            "age": current_user.age,
            "risk_tolerance": current_user.risk_tolerance,
            "risk_assessment_mode": risk_mode,
            "retirement_years": current_user.retirement_years,
            "obligations_amount": current_user.obligations_amount
        },
        "analysis_meta": _analysis_meta(profile, now_utc, cached=cached)
    }

@app.get("/api/users/me", response_model=UserResponse)
def get_my_profile(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Fetch the logged-in user's profile and AI analysis."""
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    
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

    if "obligations_amount" in updates and updates["obligations_amount"] is not None:
        if updates["obligations_amount"] < 0:
            raise HTTPException(status_code=400, detail="Obligations amount must be a positive number")

    if "risk_assessment_mode" in updates:
        if updates["risk_assessment_mode"] not in {"manual", "ai"}:
            raise HTTPException(status_code=400, detail="Invalid risk assessment mode")

    for field, value in updates.items():
        setattr(current_user, field, value)

    if current_user.risk_assessment_mode == "ai":
        current_user.risk_tolerance = _compute_risk_tolerance(
            age=current_user.age,
            income=current_user.income,
            retirement_years=current_user.retirement_years,
            obligations_amount=float(current_user.obligations_amount or 0)
        )

    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if profile:
        profile.portfolio_analysis = None
        profile.portfolio_analysis_at = None

    db.commit()
    db.refresh(current_user)

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

    for candidate in attempts:
        existing = db.query(models.EarningsTranscript).filter(
            models.EarningsTranscript.ticker == cleaned,
            models.EarningsTranscript.quarter == candidate
        ).first()
        if existing and existing.summary:
            return {
                "ticker": existing.ticker,
                "quarter": existing.quarter,
                "summary": existing.summary,
                "fetched_at": existing.fetched_at
            }

        api_key = os.getenv("ALPHA_VANTAGE_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Alpha Vantage API key not configured")

        _av_throttle()
        url = f"https://www.alphavantage.co/query?function=EARNINGS_CALL_TRANSCRIPT&symbol={cleaned}&quarter={candidate}&apikey={api_key}"
        print("transcript url:", url)
        res = requests.get(url).json()
        print("D - Invoking AV")

        if res.get("Note") or res.get("Information"):
            message = res.get("Note") or res.get("Information")
            raise HTTPException(status_code=429, detail=f"Alpha Vantage response: {message}")

        transcript_text = res.get("transcript", "")
        if not transcript_text:
            continue

        summary = _summarize_transcript(transcript_text)
        fetched_at = datetime.now(timezone.utc)
        if existing:
            existing.transcript = transcript_text
            existing.summary = summary
            existing.fetched_at = fetched_at
        else:
            existing = models.EarningsTranscript(
                ticker=cleaned,
                quarter=candidate,
                transcript=transcript_text,
                summary=summary,
                fetched_at=fetched_at
            )
            db.add(existing)
        db.commit()

        return {
            "ticker": existing.ticker,
            "quarter": existing.quarter,
            "summary": existing.summary,
            "fetched_at": existing.fetched_at
        }

    raise HTTPException(status_code=404, detail="Transcript not found")
