from sqlalchemy import Column, Integer, String, Float, Date, Text, DECIMAL, DateTime, BigInteger
from sqlalchemy.sql import func
from config.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10))
    company_name = Column(String(255))
    sector = Column(String(100))
    market_cap = Column(BigInteger)
    created_at = Column(DateTime)

class StockPrice(Base):
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)
    date = Column(Date, nullable=False)
    open_price = Column(DECIMAL(10, 2))
    high_price = Column(DECIMAL(10, 2))
    low_price = Column(DECIMAL(10, 2))
    close_price = Column(DECIMAL(10, 2))
    volume = Column(BigInteger)
    ma_5 = Column(DECIMAL(10, 2))
    ma_20 = Column(DECIMAL(10, 2))
    ma_50 = Column(DECIMAL(10, 2))
    ma_200 = Column(DECIMAL(10, 2))
    price_change_pct = Column(DECIMAL(5, 2))
    volume_change_pct = Column(DECIMAL(5, 2))

class FinancialMetrics(Base):
    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10))
    pe_ratio = Column(DECIMAL(8, 2))
    dividend_yield = Column(DECIMAL(5, 4))
    market_cap = Column(BigInteger)
    beta = Column(DECIMAL(5, 3))
    updated_at = Column(DateTime)

class MarketIndex(Base):
    __tablename__ = "market_indices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)  # Changed from 10 to 20
    index_name = Column(String(100))
    date = Column(Date, nullable=False)
    open_price = Column(DECIMAL(12, 4))  # Added open_price column
    close_price = Column(DECIMAL(12, 4))  # Changed precision
    change_pct = Column(Float)

# Add missing tables from actual schema
class SectorPerformance(Base):
    __tablename__ = "sector_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sector_name = Column(String(100))
    sector_etf = Column(String(10))
    date = Column(Date)
    close_price = Column(DECIMAL(12, 4))

class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10))
    shares = Column(DECIMAL(15, 6))
    avg_cost = Column(DECIMAL(12, 4))
    current_price = Column(DECIMAL(12, 4))