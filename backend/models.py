from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    supabase_user_id = Column(String, unique=True, index=True)
    age = Column(Integer)
    income = Column(Float)
    risk_tolerance = Column(String)
    risk_assessment_mode = Column(String, default="manual")
    retirement_years = Column(Integer)
    obligations_amount = Column(Float)
    obligations = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    holdings = relationship("Holding", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    recommended_equity_pct = Column(Float)
    recommended_allocation = Column(JSON)  # Store sector recommendations
    ai_analysis = Column(String)  # LLM-generated profile analysis
    portfolio_analysis = Column(String)
    portfolio_analysis_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="profile")

class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_holdings_user_ticker"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ticker = Column(String, index=True)
    shares = Column(Float)
    avg_price = Column(Float)
    asset_type = Column(String)
    
    user = relationship("User", back_populates="holdings")

class StockData(Base):
    __tablename__ = "stock_data"
    
    ticker = Column(String, primary_key=True, index=True)
    current_price = Column(Float)
    pe_ratio = Column(Float, nullable=True)
    sector = Column(String, nullable=True)
    asset_type = Column(String, nullable=True)
    market_cap = Column(Float, nullable=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class NewsItem(Base):
    __tablename__ = "news_items"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    headline = Column(String)
    url = Column(String)
    published_date = Column(DateTime)
    ai_summary = Column(String)
    sentiment = Column(String)  # "positive", "negative", "neutral"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class EarningsTranscript(Base):
    __tablename__ = "earnings_transcripts"
    __table_args__ = (
        UniqueConstraint("ticker", "quarter", name="uq_earnings_ticker_quarter"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    quarter = Column(String, index=True)
    transcript = Column(String)
    summary = Column(String)
    fetched_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
