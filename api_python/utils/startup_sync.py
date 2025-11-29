"""
Startup Data Synchronization Service
Automatically updates all database tables with current data on API startup.

This module handles:
- Stock prices: POST (add new records from last date to today)
- Financial metrics: PUT (update the one record per company)
- Market indices: POST (add new records from last date to today)
- Sector performance: POST (add new records from last date to today)
"""
import logging
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload
import pandas as pd
import numpy as np

from models.database_models import Company, StockPrice, FinancialMetrics, MarketIndex, SectorPerformance
from utils.live_stock_service import fetch_stock_data_sync, fetch_company_info_sync, YFINANCE_AVAILABLE, executor

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION: Toggle startup sync on/off
# ============================================================================
# Set to False to disable startup data synchronization
# Set to True to enable startup data synchronization
ENABLE_STARTUP_SYNC = True  # <-- Startup sync is ENABLED
# ============================================================================

# Global flag to ensure sync only runs once
_sync_has_run = False
_sync_lock = asyncio.Lock()

# Major market indices mapping
MAJOR_INDICES = {
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ Composite",
    "^DJI": "Dow Jones Industrial Average",
    "^RUT": "Russell 2000",
    "^VIX": "CBOE Volatility Index"
}

# Sector ETF mapping for sector performance
SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Consumer Cyclical": "XLY",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB"
}


def calculate_moving_averages(prices: pd.Series, periods: List[int] = [5, 20, 50, 200]) -> Dict[str, float]:
    """Calculate moving averages for given periods"""
    mas = {}
    for period in periods:
        if len(prices) >= period:
            mas[f'ma_{period}'] = float(prices.rolling(window=period).mean().iloc[-1])
        else:
            mas[f'ma_{period}'] = None
    return mas


def calculate_price_change_pct(current: float, previous: float) -> Optional[float]:
    """Calculate price change percentage"""
    if previous and previous != 0:
        return round(((current - previous) / previous) * 100, 2)
    return None


def calculate_volume_change_pct(current: int, previous: int) -> Optional[float]:
    """Calculate volume change percentage"""
    if previous and previous != 0:
        return round(((current - previous) / previous) * 100, 2)
    return None


async def get_latest_stock_price_date(session: AsyncSession, ticker: str) -> Optional[date]:
    """Get the latest date for a ticker's stock prices"""
    try:
        result = await session.execute(
            select(func.max(StockPrice.date))
            .where(StockPrice.ticker == ticker)
        )
        latest_date = result.scalar_one_or_none()
        return latest_date
    except Exception as e:
        logger.error(f"Error getting latest date for {ticker}: {e}")
        return None


async def sync_stock_prices_for_company(session: AsyncSession, ticker: str) -> Dict[str, int]:
    """
    Sync stock prices for a single company.
    Fetches data from last stored date to today and inserts new records.
    Returns: dict with counts of records inserted
    """
    if not YFINANCE_AVAILABLE:
        logger.warning(f"yfinance not available, skipping stock price sync for {ticker}")
        return {"inserted": 0, "errors": 0}

    try:
        # Get latest date in database
        latest_date = await get_latest_stock_price_date(session, ticker)
        
        # Determine start date
        if latest_date:
            # Start from day after latest date
            start_date = latest_date + timedelta(days=1)
        else:
            # No data exists, fetch from 1 year ago
            start_date = date.today() - timedelta(days=365)
        
        # Don't fetch if we're already up to date (check if latest_date is recent, within last 3 days)
        # This handles weekends/holidays where today might not have trading data
        if latest_date:
            days_since_latest = (date.today() - latest_date).days
            if days_since_latest <= 3:  # Allow up to 3 days (handles weekends)
                logger.info(f"{ticker}: Stock prices already up to date (latest: {latest_date}, {days_since_latest} days ago)")
                return {"inserted": 0, "errors": 0}
        
        logger.info(f"{ticker}: Fetching stock prices from {start_date} to today (latest in DB: {latest_date})")
        
        # Fetch data from yfinance
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            executor,
            fetch_stock_data_sync,
            ticker,
            "max",  # Fetch maximum available history
            "1d"
        )
        
        if df is None or df.empty:
            logger.warning(f"{ticker}: No data returned from yfinance")
            return {"inserted": 0, "errors": 1}
        
        logger.info(f"{ticker}: Received {len(df)} rows from yfinance")
        
        # Filter to only dates we need (from start_date onwards)
        if 'Date' in df.columns and not df.empty:
            # Convert Date column to date type if it's not already
            # Handle timezone-aware datetimes properly
            try:
                # Convert to datetime first
                df['Date'] = pd.to_datetime(df['Date'])
                # Check if timezone-aware and convert to naive datetime, then to date
                if df['Date'].dt.tz is not None:
                    # Timezone-aware: convert to naive datetime first, then to date
                    df['Date'] = df['Date'].dt.tz_convert('UTC').dt.tz_localize(None).dt.date
                else:
                    # Already naive: just convert to date
                    df['Date'] = df['Date'].dt.date
            except Exception as e:
                logger.error(f"{ticker}: Error converting Date column: {e}")
                # Fallback: try simple conversion
                try:
                    df['Date'] = pd.to_datetime(df['Date']).dt.date
                except:
                    logger.error(f"{ticker}: Failed to convert Date column, skipping date filtering")
                    pass
            
            # Log the date range before filtering
            min_date_before = df['Date'].min()
            max_date_before = df['Date'].max()
            logger.info(f"{ticker}: Data from yfinance: {min_date_before} to {max_date_before}")
            
            # Filter to dates >= start_date
            df = df[df['Date'] >= start_date]
            
            # Don't filter by today - get all available data up to the most recent date
            # This handles weekends/holidays where today might not have data
            if not df.empty:
                max_available_date = df['Date'].max()
                min_available_date = df['Date'].min()
                logger.info(f"{ticker}: After filtering (>= {start_date}): {min_available_date} to {max_available_date} ({len(df)} rows)")
            else:
                logger.warning(f"{ticker}: All data filtered out! start_date={start_date}, yfinance range={min_date_before} to {max_date_before}")
        
        if df.empty:
            logger.warning(f"{ticker}: No new data to insert after filtering (start_date: {start_date}, latest in DB: {latest_date})")
            return {"inserted": 0, "errors": 0}
        
        # Get previous close price for calculating price_change_pct
        if latest_date:
            prev_result = await session.execute(
                select(StockPrice.close_price)
                .where(StockPrice.ticker == ticker)
                .where(StockPrice.date == latest_date)
                .order_by(StockPrice.date.desc())
                .limit(1)
            )
            prev_close = prev_result.scalar_one_or_none()
            # Convert Decimal to float if it's a Decimal type (from database)
            # This is needed because calculate_price_change_pct expects float, not Decimal
            if prev_close is not None:
                prev_close = float(prev_close)
        else:
            prev_close = None
        
        # Insert new records
        inserted_count = 0
        prev_row_close = prev_close  # Initialize with previous close from DB (now as float)
        prev_row_volume = None
        
        # Sort by date to ensure chronological order
        df = df.sort_values('Date')
        
        # Log what we're about to insert
        if not df.empty:
            logger.info(f"{ticker}: Preparing to insert {len(df)} records, date range: {df['Date'].min()} to {df['Date'].max()}")
        
        for idx, row in df.iterrows():
            try:
                row_date = row['Date'] if isinstance(row['Date'], date) else pd.to_datetime(row['Date']).date()
                
                # Check if record already exists
                existing = await session.execute(
                    select(StockPrice)
                    .where(StockPrice.ticker == ticker)
                    .where(StockPrice.date == row_date)
                )
                existing_record = existing.scalar_one_or_none()
                if existing_record:
                    # Update prev_row_close for next iteration
                    prev_row_close = float(row['Close']) if pd.notna(row['Close']) else prev_row_close
                    prev_row_volume = int(row['Volume']) if pd.notna(row['Volume']) else prev_row_volume
                    logger.debug(f"{ticker}: Skipping {row_date} - already exists")
                    continue  # Skip if already exists
                
                # Calculate moving averages from historical data
                # For this, we'd need to fetch more historical data or calculate incrementally
                # For now, use the values from yfinance if available
                ma_5 = float(row.get('ma_5', 0)) if pd.notna(row.get('ma_5')) else None
                ma_20 = float(row.get('ma_20', 0)) if pd.notna(row.get('ma_20')) else None
                ma_50 = float(row.get('ma_50', 0)) if pd.notna(row.get('ma_50')) else None
                ma_200 = float(row.get('ma_200', 0)) if pd.notna(row.get('ma_200')) else None
                
                # Calculate price change percentage
                close_price = float(row['Close']) if pd.notna(row['Close']) else None
                price_change_pct = None
                if close_price and prev_row_close:
                    price_change_pct = calculate_price_change_pct(close_price, prev_row_close)
                
                # Calculate volume change percentage
                volume = int(row['Volume']) if pd.notna(row['Volume']) else None
                volume_change_pct = None
                if volume and prev_row_volume:
                    volume_change_pct = calculate_volume_change_pct(volume, prev_row_volume)
                
                # Create new stock price record
                stock_price = StockPrice(
                    ticker=ticker,
                    date=row_date,
                    open_price=float(row['Open']) if pd.notna(row['Open']) else None,
                    high_price=float(row['High']) if pd.notna(row['High']) else None,
                    low_price=float(row['Low']) if pd.notna(row['Low']) else None,
                    close_price=close_price,
                    volume=volume,
                    ma_5=ma_5,
                    ma_20=ma_20,
                    ma_50=ma_50,
                    ma_200=ma_200,
                    price_change_pct=price_change_pct,
                    volume_change_pct=volume_change_pct
                )
                
                session.add(stock_price)
                inserted_count += 1
                
                # Update for next iteration
                prev_row_close = close_price
                prev_row_volume = volume
                
            except Exception as e:
                logger.error(f"{ticker}: Error inserting stock price for {row.get('Date')}: {e}")
                continue
        
        await session.commit()
        if inserted_count > 0:
            # Get the latest date that was inserted
            latest_inserted = df['Date'].max() if not df.empty else None
            logger.info(f"{ticker}: Inserted {inserted_count} new stock price records (latest date: {latest_inserted})")
        else:
            logger.warning(f"{ticker}: No records were inserted despite having data")
        return {"inserted": inserted_count, "errors": 0}
        
    except Exception as e:
        logger.error(f"{ticker}: Error syncing stock prices: {e}")
        await session.rollback()
        return {"inserted": 0, "errors": 1}


async def sync_financial_metrics_for_company(session: AsyncSession, ticker: str) -> Dict[str, bool]:
    """
    Sync financial metrics for a single company.
    Updates the existing record (PUT behavior - one record per company).
    Returns: dict with success status
    """
    if not YFINANCE_AVAILABLE:
        logger.warning(f"yfinance not available, skipping financial metrics sync for {ticker}")
        return {"updated": False, "error": True}

    try:
        logger.info(f"{ticker}: Fetching financial metrics from yfinance")
        
        # Fetch company info from yfinance
        loop = asyncio.get_event_loop()
        company_info = await loop.run_in_executor(
            executor,
            fetch_company_info_sync,
            ticker
        )
        
        if not company_info:
            logger.warning(f"{ticker}: No company info returned from yfinance")
            return {"updated": False, "error": True}
        
        # Get financial metrics from yfinance
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info
            
            pe_ratio = info.get('trailingPE') if info.get('trailingPE') else None
            dividend_yield = info.get('dividendYield') if info.get('dividendYield') else None
            market_cap = info.get('marketCap') if info.get('marketCap') else None
            beta = info.get('beta') if info.get('beta') else None
            
            logger.info(f"{ticker}: Fetched metrics - PE: {pe_ratio}, Dividend Yield: {dividend_yield}, Market Cap: {market_cap}, Beta: {beta}")
            
        except Exception as e:
            logger.error(f"{ticker}: Error fetching financial metrics from yfinance: {e}")
            return {"updated": False, "error": True}
        
        # Check if metrics record exists
        result = await session.execute(
            select(FinancialMetrics)
            .where(FinancialMetrics.ticker == ticker)
        )
        metrics = result.scalar_one_or_none()
        
        if metrics:
            # Update existing record (PUT behavior)
            old_values = {
                "pe_ratio": metrics.pe_ratio,
                "dividend_yield": metrics.dividend_yield,
                "market_cap": metrics.market_cap,
                "beta": metrics.beta
            }
            metrics.pe_ratio = pe_ratio
            metrics.dividend_yield = dividend_yield
            metrics.market_cap = market_cap
            metrics.beta = beta
            metrics.last_updated = datetime.now()
            logger.info(f"{ticker}: Updated existing financial metrics record (old: {old_values})")
        else:
            # Create new record
            metrics = FinancialMetrics(
                ticker=ticker,
                pe_ratio=pe_ratio,
                dividend_yield=dividend_yield,
                market_cap=market_cap,
                beta=beta,
                last_updated=datetime.now()
            )
            session.add(metrics)
            logger.info(f"{ticker}: Created new financial metrics record")
        
        await session.commit()
        logger.info(f"{ticker}: Successfully saved financial metrics (last_updated: {metrics.last_updated})")
        return {"updated": True, "error": False}
        
    except Exception as e:
        logger.error(f"{ticker}: Error syncing financial metrics: {e}")
        await session.rollback()
        return {"updated": False, "error": True}


async def create_company_with_full_data(session: AsyncSession, ticker: str) -> Dict[str, Any]:
    """
    Create a new company with complete data fetched from yfinance.
    This function:
    1. Fetches company information
    2. Fetches financial metrics
    3. Fetches COMPLETE historical stock prices (from earliest available date)
    4. Inserts all data into database
    
    Returns: dict with company data and summary of inserted records
    """
    if not YFINANCE_AVAILABLE:
        raise ValueError("yfinance is not available")
    
    ticker = ticker.upper()
    
    try:
        # Step 1: Fetch company information from yfinance
        logger.info(f"{ticker}: Fetching company information from yfinance")
        loop = asyncio.get_event_loop()
        company_info = await loop.run_in_executor(
            executor,
            fetch_company_info_sync,
            ticker
        )
        
        if not company_info:
            raise ValueError(f"Company {ticker} not found in yfinance")
        
        # Step 2: Fetch financial metrics
        logger.info(f"{ticker}: Fetching financial metrics from yfinance")
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        
        pe_ratio = info.get('trailingPE') if info.get('trailingPE') else None
        dividend_yield = info.get('dividendYield') if info.get('dividendYield') else None
        market_cap = info.get('marketCap') if info.get('marketCap') else None
        beta = info.get('beta') if info.get('beta') else None
        
        # Step 3: Fetch COMPLETE historical stock prices (from earliest available date)
        logger.info(f"{ticker}: Fetching complete historical stock prices from yfinance")
        df = await loop.run_in_executor(
            executor,
            fetch_stock_data_sync,
            ticker,
            "max",  # Fetch maximum available history
            "1d"
        )
        
        if df is None or df.empty:
            raise ValueError(f"No stock price data available for {ticker}")
        
        logger.info(f"{ticker}: Received {len(df)} rows of historical data from yfinance")
        
        # Convert Date column to date type
        if 'Date' in df.columns and not df.empty:
            try:
                df['Date'] = pd.to_datetime(df['Date'])
                if df['Date'].dt.tz is not None:
                    df['Date'] = df['Date'].dt.tz_convert('UTC').dt.tz_localize(None).dt.date
                else:
                    df['Date'] = df['Date'].dt.date
            except Exception as e:
                logger.error(f"{ticker}: Error converting Date column: {e}")
                df['Date'] = pd.to_datetime(df['Date']).dt.date
        
        # Sort by date to ensure chronological order
        df = df.sort_values('Date')
        
        # Step 4: Insert company into database
        logger.info(f"{ticker}: Inserting company information into database")
        company = Company(
            ticker=ticker,
            company_name=company_info.get('company_name', ticker),
            sector=company_info.get('sector'),
            market_cap=int(market_cap) if market_cap else None,
            created_at=datetime.now()
        )
        session.add(company)
        
        # Step 5: Insert financial metrics
        logger.info(f"{ticker}: Inserting financial metrics into database")
        metrics = FinancialMetrics(
            ticker=ticker,
            pe_ratio=pe_ratio,
            dividend_yield=dividend_yield,
            market_cap=market_cap,
            beta=beta,
            last_updated=datetime.now()
        )
        session.add(metrics)
        
        # Step 6: Insert all historical stock prices
        logger.info(f"{ticker}: Inserting {len(df)} historical stock price records into database")
        inserted_count = 0
        prev_row_close = None
        prev_row_volume = None
        
        for idx, row in df.iterrows():
            try:
                row_date = row['Date'] if isinstance(row['Date'], date) else pd.to_datetime(row['Date']).date()
                
                # Calculate moving averages (they should be in the dataframe from fetch_stock_data_sync)
                ma_5 = float(row.get('ma_5', 0)) if pd.notna(row.get('ma_5')) else None
                ma_20 = float(row.get('ma_20', 0)) if pd.notna(row.get('ma_20')) else None
                ma_50 = float(row.get('ma_50', 0)) if pd.notna(row.get('ma_50')) else None
                ma_200 = float(row.get('ma_200', 0)) if pd.notna(row.get('ma_200')) else None
                
                # Calculate price change percentage
                close_price = float(row['Close']) if pd.notna(row['Close']) else None
                price_change_pct = None
                if close_price and prev_row_close:
                    price_change_pct = calculate_price_change_pct(close_price, prev_row_close)
                
                # Calculate volume change percentage
                volume = int(row['Volume']) if pd.notna(row['Volume']) else None
                volume_change_pct = None
                if volume and prev_row_volume:
                    volume_change_pct = calculate_volume_change_pct(volume, prev_row_volume)
                
                # Create stock price record
                stock_price = StockPrice(
                    ticker=ticker,
                    date=row_date,
                    open_price=float(row['Open']) if pd.notna(row['Open']) else None,
                    high_price=float(row['High']) if pd.notna(row['High']) else None,
                    low_price=float(row['Low']) if pd.notna(row['Low']) else None,
                    close_price=close_price,
                    volume=volume,
                    ma_5=ma_5,
                    ma_20=ma_20,
                    ma_50=ma_50,
                    ma_200=ma_200,
                    price_change_pct=price_change_pct,
                    volume_change_pct=volume_change_pct
                )
                
                session.add(stock_price)
                inserted_count += 1
                
                # Update for next iteration
                prev_row_close = close_price
                prev_row_volume = volume
                
            except Exception as e:
                logger.error(f"{ticker}: Error inserting stock price for {row.get('Date')}: {e}")
                continue
        
        # Commit all inserts
        await session.commit()
        
        logger.info(f"{ticker}: Successfully created company with {inserted_count} stock price records")
        
        # Get date range
        min_date = df['Date'].min() if not df.empty else None
        max_date = df['Date'].max() if not df.empty else None
        
        return {
            "company": {
                "ticker": ticker,
                "company_name": company_info.get('company_name', ticker),
                "sector": company_info.get('sector'),
                "market_cap": market_cap
            },
            "financial_metrics": {
                "pe_ratio": pe_ratio,
                "dividend_yield": dividend_yield,
                "beta": beta
            },
            "stock_prices": {
                "records_inserted": inserted_count,
                "date_range": {
                    "earliest": str(min_date) if min_date else None,
                    "latest": str(max_date) if max_date else None
                }
            },
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"{ticker}: Error creating company with full data: {e}")
        await session.rollback()
        raise


async def get_latest_index_date(session: AsyncSession, symbol: str) -> Optional[date]:
    """Get the latest date for a market index"""
    try:
        result = await session.execute(
            select(func.max(MarketIndex.date))
            .where(MarketIndex.symbol == symbol)
        )
        latest_date = result.scalar_one_or_none()
        return latest_date
    except Exception as e:
        logger.error(f"Error getting latest index date for {symbol}: {e}")
        return None


async def sync_market_indices(session: AsyncSession) -> Dict[str, int]:
    """
    Sync market indices data.
    Queries database for all existing indices and updates each to current day.
    Fetches data from last stored date to today and inserts new records (POST behavior).
    Returns: dict with counts of records inserted
    """
    if not YFINANCE_AVAILABLE:
        logger.warning("yfinance not available, skipping market indices sync")
        return {"inserted": 0, "errors": 0}

    try:
        import yfinance as yf
        
        # Query database for all existing market indices
        result = await session.execute(
            select(MarketIndex.symbol, MarketIndex.index_name)
            .distinct()
        )
        existing_indices = result.fetchall()
        
        if not existing_indices:
            logger.warning("No market indices found in database. Skipping market indices sync.")
            return {"inserted": 0, "errors": 0}
        
        # Create a mapping of symbol to index_name from database
        # Use index_name from database if available, otherwise fall back to MAJOR_INDICES mapping
        indices_map = {}
        for row in existing_indices:
            symbol = row[0]
            index_name = row[1]
            if symbol:
                # Use index_name from database if available, otherwise try to get from MAJOR_INDICES mapping
                if not index_name and symbol in MAJOR_INDICES:
                    index_name = MAJOR_INDICES[symbol]
                    logger.info(f"{symbol}: Using fallback index name '{index_name}' from mapping")
                # If still no name, use symbol as name
                if not index_name:
                    index_name = symbol
                indices_map[symbol] = index_name
        
        if not indices_map:
            logger.warning("No market indices with valid symbols found. Skipping market indices sync.")
            return {"inserted": 0, "errors": 0}
        
        logger.info(f"Found {len(indices_map)} market indices in database to sync: {list(indices_map.keys())}")
        
        total_inserted = 0
        total_errors = 0
        
        for symbol, index_name in indices_map.items():
            try:
                # Get latest date
                latest_date = await get_latest_index_date(session, symbol)
                
                # Don't fetch if we're already up to date (check if latest_date is recent, within last 3 days)
                # This handles weekends/holidays where today might not have trading data
                if latest_date:
                    days_since_latest = (date.today() - latest_date).days
                    if days_since_latest <= 3:  # Allow up to 3 days (handles weekends)
                        logger.info(f"{symbol}: Market index already up to date (latest: {latest_date}, {days_since_latest} days ago)")
                        continue
                
                start_date = (latest_date + timedelta(days=1)) if latest_date else (date.today() - timedelta(days=365))
                
                logger.info(f"{symbol}: Fetching market index data from {start_date} to today (latest in DB: {latest_date})")
                
                # Fetch data
                loop = asyncio.get_event_loop()
                ticker = yf.Ticker(symbol)
                hist = await loop.run_in_executor(
                    executor,
                    lambda: ticker.history(period="max", interval="1d")
                )
                
                if hist.empty:
                    logger.warning(f"{symbol}: No data returned from yfinance")
                    total_errors += 1
                    continue
                
                logger.info(f"{symbol}: Received {len(hist)} rows from yfinance")
                
                # Filter to dates we need
                hist = hist.reset_index()
                
                # Convert Date column to date type if it's not already
                if 'Date' in hist.columns and not hist.empty:
                    # Handle timezone-aware datetimes properly
                    try:
                        # Convert to datetime first
                        hist['Date'] = pd.to_datetime(hist['Date'])
                        # Check if timezone-aware and convert to naive datetime, then to date
                        if hist['Date'].dt.tz is not None:
                            # Timezone-aware: convert to naive datetime first, then to date
                            hist['Date'] = hist['Date'].dt.tz_convert('UTC').dt.tz_localize(None).dt.date
                        else:
                            # Already naive: just convert to date
                            hist['Date'] = hist['Date'].dt.date
                    except Exception as e:
                        logger.error(f"{symbol}: Error converting Date column: {e}")
                        # Fallback: try simple conversion
                        try:
                            hist['Date'] = pd.to_datetime(hist['Date']).dt.date
                        except:
                            logger.error(f"{symbol}: Failed to convert Date column, skipping date filtering")
                            pass
                    
                    # Log the date range before filtering
                    min_date_before = hist['Date'].min()
                    max_date_before = hist['Date'].max()
                    logger.info(f"{symbol}: Data from yfinance: {min_date_before} to {max_date_before}")
                    
                    # Filter to dates >= start_date (don't filter by today - handles weekends/holidays)
                    hist = hist[hist['Date'] >= start_date]
                    
                    if not hist.empty:
                        max_available_date = hist['Date'].max()
                        min_available_date = hist['Date'].min()
                        logger.info(f"{symbol}: After filtering (>= {start_date}): {min_available_date} to {max_available_date} ({len(hist)} rows)")
                    else:
                        logger.warning(f"{symbol}: All data filtered out! start_date={start_date}, yfinance range={min_date_before} to {max_date_before}")
                
                if hist.empty:
                    logger.warning(f"{symbol}: No new data to insert after filtering (start_date: {start_date}, latest in DB: {latest_date})")
                    continue
                
                # Insert new records
                inserted_count = 0
                
                # Log what we're about to insert
                if not hist.empty:
                    logger.info(f"{symbol}: Preparing to insert {len(hist)} records, date range: {hist['Date'].min()} to {hist['Date'].max()}")
                
                for idx, row in hist.iterrows():
                    try:
                        row_date = row['Date'] if isinstance(row['Date'], date) else pd.to_datetime(row['Date']).date()
                        
                        # Check if record already exists
                        existing = await session.execute(
                            select(MarketIndex)
                            .where(MarketIndex.symbol == symbol)
                            .where(MarketIndex.date == row_date)
                        )
                        if existing.scalar_one_or_none():
                            logger.debug(f"{symbol}: Skipping {row_date} - already exists")
                            continue
                        
                        # Calculate change percentage
                        close_price = float(row['Close']) if pd.notna(row['Close']) else None
                        open_price = float(row['Open']) if pd.notna(row['Open']) else None
                        change_pct = None
                        if close_price and open_price and open_price != 0:
                            change_pct = ((close_price - open_price) / open_price) * 100
                        
                        index_record = MarketIndex(
                            symbol=symbol,
                            index_name=index_name,
                            date=row_date,
                            open_price=open_price,
                            close_price=close_price,
                            change_pct=change_pct
                        )
                        
                        session.add(index_record)
                        inserted_count += 1
                        
                    except Exception as e:
                        logger.error(f"{symbol}: Error inserting index data for {row.get('Date')}: {e}")
                        continue
                
                await session.commit()
                if inserted_count > 0:
                    # Get the latest date that was inserted
                    latest_inserted = hist['Date'].max() if not hist.empty else None
                    logger.info(f"{symbol}: Inserted {inserted_count} new index records (latest date: {latest_inserted})")
                else:
                    logger.warning(f"{symbol}: No records were inserted despite having data")
                total_inserted += inserted_count
                
            except Exception as e:
                logger.error(f"{symbol}: Error syncing market index: {e}")
                total_errors += 1
                continue
        
        return {"inserted": total_inserted, "errors": total_errors}
        
    except Exception as e:
        logger.error(f"Error syncing market indices: {e}")
        return {"inserted": 0, "errors": len(existing_indices) if 'existing_indices' in locals() else 0}


async def get_latest_sector_date(session: AsyncSession, sector_name: str) -> Optional[date]:
    """Get the latest date for a sector performance"""
    try:
        result = await session.execute(
            select(func.max(SectorPerformance.date))
            .where(SectorPerformance.sector_name == sector_name)
        )
        latest_date = result.scalar_one_or_none()
        return latest_date
    except Exception as e:
        logger.error(f"Error getting latest sector date for {sector_name}: {e}")
        return None


async def sync_sector_performance(session: AsyncSession) -> Dict[str, int]:
    """
    Sync sector performance data.
    Queries database for all existing sectors and updates each to current day.
    Fetches data from last stored date to today and inserts new records (POST behavior).
    Returns: dict with counts of records inserted
    """
    if not YFINANCE_AVAILABLE:
        logger.warning("yfinance not available, skipping sector performance sync")
        return {"inserted": 0, "errors": 0}

    try:
        import yfinance as yf
        
        # Query database for all existing sector performance records
        result = await session.execute(
            select(SectorPerformance.sector_name, SectorPerformance.sector_etf)
            .distinct()
        )
        existing_sectors = result.fetchall()
        
        if not existing_sectors:
            logger.warning("No sector performance records found in database. Skipping sector performance sync.")
            return {"inserted": 0, "errors": 0}
        
        # Create a mapping of sector_name to sector_etf from database
        # Use ETF from database if available, otherwise fall back to SECTOR_ETFS mapping
        sectors_map = {}
        for row in existing_sectors:
            sector_name = row[0]
            etf_symbol = row[1]
            if sector_name:
                # Use ETF from database if available, otherwise try to get from SECTOR_ETFS mapping
                if not etf_symbol and sector_name in SECTOR_ETFS:
                    etf_symbol = SECTOR_ETFS[sector_name]
                    logger.info(f"{sector_name}: Using fallback ETF symbol {etf_symbol} from mapping")
                if etf_symbol:
                    sectors_map[sector_name] = etf_symbol
                else:
                    logger.warning(f"{sector_name}: No ETF symbol found in database or mapping, skipping")
        
        if not sectors_map:
            logger.warning("No sectors with valid ETF symbols found. Skipping sector performance sync.")
            return {"inserted": 0, "errors": 0}
        
        logger.info(f"Found {len(sectors_map)} sectors in database to sync: {list(sectors_map.keys())}")
        
        total_inserted = 0
        total_errors = 0
        
        for sector_name, etf_symbol in sectors_map.items():
            try:
                # Get latest date
                latest_date = await get_latest_sector_date(session, sector_name)
                
                # Don't fetch if we're already up to date (check if latest_date is recent, within last 3 days)
                # This handles weekends/holidays where today might not have trading data
                if latest_date:
                    days_since_latest = (date.today() - latest_date).days
                    if days_since_latest <= 3:  # Allow up to 3 days (handles weekends)
                        logger.info(f"{sector_name}: Sector performance already up to date (latest: {latest_date}, {days_since_latest} days ago)")
                        continue
                
                start_date = (latest_date + timedelta(days=1)) if latest_date else (date.today() - timedelta(days=365))
                
                logger.info(f"{sector_name}: Fetching sector performance data from {start_date} to today (latest in DB: {latest_date}, ETF: {etf_symbol})")
                
                # Fetch ETF data
                loop = asyncio.get_event_loop()
                ticker = yf.Ticker(etf_symbol)
                hist = await loop.run_in_executor(
                    executor,
                    lambda: ticker.history(period="max", interval="1d")
                )
                
                if hist.empty:
                    logger.warning(f"{sector_name} ({etf_symbol}): No data returned from yfinance")
                    total_errors += 1
                    continue
                
                logger.info(f"{sector_name}: Received {len(hist)} rows from yfinance")
                
                # Filter to dates we need
                hist = hist.reset_index()
                
                # Convert Date column to date type if it's not already
                if 'Date' in hist.columns and not hist.empty:
                    # Handle timezone-aware datetimes properly
                    try:
                        # Convert to datetime first
                        hist['Date'] = pd.to_datetime(hist['Date'])
                        # Check if timezone-aware and convert to naive datetime, then to date
                        if hist['Date'].dt.tz is not None:
                            # Timezone-aware: convert to naive datetime first, then to date
                            hist['Date'] = hist['Date'].dt.tz_convert('UTC').dt.tz_localize(None).dt.date
                        else:
                            # Already naive: just convert to date
                            hist['Date'] = hist['Date'].dt.date
                    except Exception as e:
                        logger.error(f"{sector_name}: Error converting Date column: {e}")
                        # Fallback: try simple conversion
                        try:
                            hist['Date'] = pd.to_datetime(hist['Date']).dt.date
                        except:
                            logger.error(f"{sector_name}: Failed to convert Date column, skipping date filtering")
                            pass
                    
                    # Log the date range before filtering
                    min_date_before = hist['Date'].min()
                    max_date_before = hist['Date'].max()
                    logger.info(f"{sector_name}: Data from yfinance: {min_date_before} to {max_date_before}")
                    
                    # Filter to dates >= start_date (don't filter by today - handles weekends/holidays)
                    hist = hist[hist['Date'] >= start_date]
                    
                    if not hist.empty:
                        max_available_date = hist['Date'].max()
                        min_available_date = hist['Date'].min()
                        logger.info(f"{sector_name}: After filtering (>= {start_date}): {min_available_date} to {max_available_date} ({len(hist)} rows)")
                    else:
                        logger.warning(f"{sector_name}: All data filtered out! start_date={start_date}, yfinance range={min_date_before} to {max_date_before}")
                
                if hist.empty:
                    logger.warning(f"{sector_name}: No new data to insert after filtering (start_date: {start_date}, latest in DB: {latest_date})")
                    continue
                
                # Insert new records
                inserted_count = 0
                
                # Log what we're about to insert
                if not hist.empty:
                    logger.info(f"{sector_name}: Preparing to insert {len(hist)} records, date range: {hist['Date'].min()} to {hist['Date'].max()}")
                
                for idx, row in hist.iterrows():
                    try:
                        row_date = row['Date'] if isinstance(row['Date'], date) else pd.to_datetime(row['Date']).date()
                        
                        # Check if record already exists
                        existing = await session.execute(
                            select(SectorPerformance)
                            .where(SectorPerformance.sector_name == sector_name)
                            .where(SectorPerformance.date == row_date)
                        )
                        if existing.scalar_one_or_none():
                            logger.debug(f"{sector_name}: Skipping {row_date} - already exists")
                            continue
                        
                        close_price = float(row['Close']) if pd.notna(row['Close']) else None
                        
                        sector_record = SectorPerformance(
                            sector_name=sector_name,
                            sector_etf=etf_symbol,
                            date=row_date,
                            close_price=close_price
                        )
                        
                        session.add(sector_record)
                        inserted_count += 1
                        
                    except Exception as e:
                        logger.error(f"{sector_name}: Error inserting sector data for {row.get('Date')}: {e}")
                        continue
                
                await session.commit()
                if inserted_count > 0:
                    # Get the latest date that was inserted
                    latest_inserted = hist['Date'].max() if not hist.empty else None
                    logger.info(f"{sector_name}: Inserted {inserted_count} new sector performance records (latest date: {latest_inserted})")
                else:
                    logger.warning(f"{sector_name}: No records were inserted despite having data")
                total_inserted += inserted_count
                
            except Exception as e:
                logger.error(f"{sector_name}: Error syncing sector performance: {e}")
                total_errors += 1
                continue
        
        return {"inserted": total_inserted, "errors": total_errors}
        
    except Exception as e:
        logger.error(f"Error syncing sector performance: {e}")
        return {"inserted": 0, "errors": len(existing_sectors) if 'existing_sectors' in locals() else 0}


# Global sync status for Task 59
_sync_status_global = {
    "is_running": False,
    "last_sync": None,
    "last_sync_summary": None
}

async def sync_all_data(session: AsyncSession) -> Dict[str, Any]:
    """
    Main synchronization function that updates all data.
    This is called on API startup.
    Ensures it only runs once, even if called multiple times.
    Returns: Summary of synchronization results
    """
    global _sync_has_run
    
    # Check if startup sync is enabled
    if not ENABLE_STARTUP_SYNC:
        logger.info("Startup sync is DISABLED (ENABLE_STARTUP_SYNC = False). Skipping data synchronization.")
        return {
            "companies_processed": 0,
            "stock_prices_inserted": 0,
            "financial_metrics_updated": 0,
            "indices_inserted": 0,
            "sector_performance_inserted": 0,
            "errors": 0,
            "skipped": True,
            "disabled": True,
            "message": "Startup sync is disabled. Set ENABLE_STARTUP_SYNC = True to enable."
        }
    
    # Use lock to prevent concurrent execution
    async with _sync_lock:
        # Check if sync has already run
        if _sync_has_run:
            logger.warning("Startup sync has already been executed. Skipping to prevent duplicate execution.")
            return {
                "companies_processed": 0,
                "stock_prices_inserted": 0,
                "financial_metrics_updated": 0,
                "indices_inserted": 0,
                "sector_performance_inserted": 0,
                "errors": 0,
                "skipped": True,
                "message": "Sync already executed once"
            }
        
        # Mark as running
        _sync_has_run = True
    
    # Update global sync status (Task 59)
    _sync_status_global["is_running"] = True
    _sync_status_global["last_sync"] = datetime.now()
    
    logger.info("=" * 60)
    logger.info("Starting data synchronization on API startup...")
    logger.info("=" * 60)
    
    summary = {
        "companies_processed": 0,
        "stock_prices_inserted": 0,
        "financial_metrics_updated": 0,
        "indices_inserted": 0,
        "sector_performance_inserted": 0,
        "errors": 0,
        "start_time": datetime.now(),
        "end_time": None,
        "duration_seconds": None
    }
    
    try:
        # Get all companies from database
        result = await session.execute(
            select(Company.ticker)
        )
        tickers = [row[0] for row in result.fetchall()]
        
        if not tickers:
            logger.warning("No companies found in database. Skipping company data sync.")
        else:
            logger.info(f"Found {len(tickers)} companies to sync")
            
            # Sync each company
            for ticker in tickers:
                try:
                    logger.info(f"Processing {ticker}...")
                    
                    # Sync stock prices (POST - add new records)
                    stock_result = await sync_stock_prices_for_company(session, ticker)
                    summary["stock_prices_inserted"] += stock_result.get("inserted", 0)
                    summary["errors"] += stock_result.get("errors", 0)
                    
                    # Sync financial metrics (PUT - update existing record)
                    metrics_result = await sync_financial_metrics_for_company(session, ticker)
                    if metrics_result.get("updated"):
                        summary["financial_metrics_updated"] += 1
                    if metrics_result.get("error"):
                        summary["errors"] += 1
                    
                    summary["companies_processed"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing {ticker}: {e}")
                    summary["errors"] += 1
                    continue
        
        # Sync market indices (POST - add new records)
        logger.info("Syncing market indices...")
        indices_result = await sync_market_indices(session)
        summary["indices_inserted"] = indices_result.get("inserted", 0)
        summary["errors"] += indices_result.get("errors", 0)
        
        # Sync sector performance (POST - add new records)
        logger.info("Syncing sector performance...")
        sector_result = await sync_sector_performance(session)
        summary["sector_performance_inserted"] = sector_result.get("inserted", 0)
        summary["errors"] += sector_result.get("errors", 0)
        
        summary["end_time"] = datetime.now()
        summary["duration_seconds"] = (summary["end_time"] - summary["start_time"]).total_seconds()
        
        # Update global sync status (Task 59)
        _sync_status_global["is_running"] = False
        _sync_status_global["last_sync_summary"] = summary
        
        logger.info("=" * 60)
        logger.info("Data synchronization completed!")
        logger.info(f"Companies processed: {summary['companies_processed']}")
        logger.info(f"Stock prices inserted: {summary['stock_prices_inserted']}")
        logger.info(f"Financial metrics updated: {summary['financial_metrics_updated']}")
        logger.info(f"Indices inserted: {summary['indices_inserted']}")
        logger.info(f"Sector performance inserted: {summary['sector_performance_inserted']}")
        logger.info(f"Errors: {summary['errors']}")
        logger.info(f"Duration: {summary['duration_seconds']:.2f} seconds")
        logger.info("=" * 60)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error during data synchronization: {e}")
        summary["errors"] += 1
        summary["end_time"] = datetime.now()
        if summary["start_time"]:
            summary["duration_seconds"] = (summary["end_time"] - summary["start_time"]).total_seconds()
        
        # Update global sync status (Task 59)
        _sync_status_global["is_running"] = False
        _sync_status_global["last_sync_summary"] = summary
        
        return summary

