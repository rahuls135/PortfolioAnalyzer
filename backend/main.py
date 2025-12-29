from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import List
import os
import requests

from database import get_db, engine, Base
import models

app = FastAPI()

# Allow frontend to make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Portfolio Analyzer API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/setup-db")
def setup_database():
    Base.metadata.create_all(bind=engine)
    return {"message": "Database tables created successfully"}

# Pydantic models
class HoldingCreate(BaseModel):
    ticker: str
    shares: float
    purchase_price: float
    purchase_date: datetime

class HoldingResponse(BaseModel):
    id: int
    ticker: str
    shares: float
    purchase_price: float
    purchase_date: datetime
    
    class Config:
        from_attributes = True

# Create a holding
@app.post("/api/users/{user_id}/holdings", response_model=HoldingResponse)
def add_holding(user_id: int, holding: HoldingCreate, db: Session = Depends(get_db)):
    # Check user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_holding = models.Holding(
        user_id=user_id,
        ticker=holding.ticker.upper(),
        shares=holding.shares,
        purchase_price=holding.purchase_price,
        purchase_date=holding.purchase_date
    )
    db.add(db_holding)
    db.commit()
    db.refresh(db_holding)
    return db_holding

# Get all holdings for a user
@app.get("/api/users/{user_id}/holdings", response_model=List[HoldingResponse])
def get_holdings(user_id: int, db: Session = Depends(get_db)):
    holdings = db.query(models.Holding).filter(models.Holding.user_id == user_id).all()
    return holdings

# Delete a holding
@app.delete("/api/users/{user_id}/holdings/{holding_id}")
def delete_holding(user_id: int, holding_id: int, db: Session = Depends(get_db)):
    holding = db.query(models.Holding).filter(
        models.Holding.id == holding_id,
        models.Holding.user_id == user_id
    ).first()
    
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    
    db.delete(holding)
    db.commit()
    return {"message": "Holding deleted"}

@app.get("/api/stocks/{ticker}")
def get_stock_data(ticker: str, db: Session = Depends(get_db)):
    ticker = ticker.upper()
    
    # Check if we have recent data (less than 1 day old)
    stock = db.query(models.StockData).filter(models.StockData.ticker == ticker).first()
    if stock and (datetime.now(timezone.utc) - stock.last_updated).seconds < 86400:
        return {
            "ticker": stock.ticker,
            "current_price": stock.current_price,
            "sector": stock.sector,
            "cached": True
        }
    
    # Fetch from Alpha Vantage
    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={api_key}"
    
    response = requests.get(url)
    data = response.json()
    
    if "Global Quote" not in data or not data["Global Quote"]:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    quote = data["Global Quote"]
    current_price = float(quote["05. price"])
    
    # Update or create stock data
    if stock:
        stock.current_price = current_price
        stock.last_updated = datetime.now(timezone.utc)
    else:
        stock = models.StockData(
            ticker=ticker,
            current_price=current_price,
            last_updated=datetime.now(timezone.utc)
        )
        db.add(stock)
    
    db.commit()
    db.refresh(stock)
    
    return {
        "ticker": stock.ticker,
        "current_price": stock.current_price,
        "cached": False
    }

@app.post("/api/users", response_model=UserResponse)
def create_user_profile(user: UserCreate, db: Session = Depends(get_db)):
    # Create user
    db_user = models.User(
        age=user.age,
        income=user.income,
        risk_tolerance=user.risk_tolerance,
        retirement_years=user.retirement_years
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Mock AI analysis (replace with real LLM later)
    ai_analysis = f"""Based on your profile (age {user.age}, {user.retirement_years} years to retirement, {user.risk_tolerance} risk tolerance):

Recommended Allocation:
- Equities: 80%
- Bonds: 15%
- Cash: 5%

Key Recommendations:
1. With {user.retirement_years} years until retirement, you have time to ride out market volatility
2. Your {user.risk_tolerance} risk tolerance aligns well with a growth-oriented portfolio
3. Consider diversifying across large-cap, mid-cap, and international stocks
4. Begin gradually increasing bond allocation as you approach retirement

Focus sectors: Technology, Healthcare, Consumer Discretionary, Financials"""
    
    # Create user profile
    db_profile = models.UserProfile(
        user_id=db_user.id,
        ai_analysis=ai_analysis
    )
    db.add(db_profile)
    db.commit()
    
    return {
        **user.dict(),
        "id": db_user.id,
        "ai_analysis": ai_analysis
    }

@app.get("/api/users/{user_id}/analysis")
def analyze_portfolio(user_id: int, db: Session = Depends(get_db)):
    # Get user and their profile
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
    
    # Get all holdings
    holdings = db.query(models.Holding).filter(models.Holding.user_id == user_id).all()
    
    if not holdings:
        return {"message": "No holdings to analyze"}
    
    # Calculate portfolio value and get current prices
    portfolio_summary = []
    total_value = 0
    
    for holding in holdings:
        # Get current stock price
        stock = db.query(models.StockData).filter(models.StockData.ticker == holding.ticker).first()
        
        if not stock:
            # Fetch it if not in cache
            try:
                get_stock_data(holding.ticker, db)
                stock = db.query(models.StockData).filter(models.StockData.ticker == holding.ticker).first()
            except:
                continue
        
        current_value = holding.shares * stock.current_price
        cost_basis = holding.shares * holding.purchase_price
        gain_loss = current_value - cost_basis
        gain_loss_pct = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0
        
        portfolio_summary.append({
            "ticker": holding.ticker,
            "shares": holding.shares,
            "purchase_price": holding.purchase_price,
            "current_price": stock.current_price,
            "current_value": current_value,
            "gain_loss": gain_loss,
            "gain_loss_pct": gain_loss_pct,
            "sector": stock.sector
        })
        
        total_value += current_value
    
    # Mock AI analysis (replace with real LLM later)
    tickers = [h['ticker'] for h in portfolio_summary]
    tech_stocks = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'META', 'AMZN']
    tech_count = sum(1 for t in tickers if t in tech_stocks)
    
    if tech_count / len(tickers) > 0.6:
        diversification_note = "Your portfolio is heavily concentrated in technology stocks. Consider diversifying into other sectors like healthcare, consumer staples, or utilities."
    else:
        diversification_note = "Your portfolio shows good sector diversification."
    
    ai_analysis = f"""Portfolio Analysis Summary:

Overall Assessment:
{diversification_note}

Holdings Breakdown:
{chr(10).join([f"• {h['ticker']}: ${h['current_value']:.2f} ({h['gain_loss_pct']:+.1f}%)" for h in portfolio_summary])}

Key Recommendations:
1. Review your positions regularly to maintain target allocation
2. Consider tax-loss harvesting opportunities on underperforming positions
3. Rebalance quarterly to maintain your desired risk profile
4. {"Keep your long-term perspective with " + str(user.retirement_years) + " years until retirement"}

Risk Assessment: Your {user.risk_tolerance} risk tolerance is {"well-suited" if user.retirement_years > 20 else "slightly aggressive"} for your timeline."""
    
    return {
        "total_value": total_value,
        "holdings": portfolio_summary,
        "ai_analysis": ai_analysis,
        "user_profile": {
            "age": user.age,
            "risk_tolerance": user.risk_tolerance,
            "retirement_years": user.retirement_years
        }
    }