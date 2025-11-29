"""
Advanced Analytics API endpoints
Implements advanced SQL queries: Window Functions, CTEs, Recursive CTEs
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal

from config.database import get_read_session  # Task 36: Use read replica for analytics

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/analytics/window-functions", response_model=dict)
async def get_window_functions_analysis(
    ticker: Optional[str] = Query(None, description="Stock ticker symbol (optional, returns all if not provided)"),
    days: Optional[int] = Query(30, ge=1, le=365, description="Number of days for momentum calculation"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: AsyncSession = Depends(get_read_session)  # Task 36: Use read replica for analytics
):
    """
    Advanced SQL: Window Functions for Time-Series Analysis
    
    Calculate moving averages, momentum indicators, and price rankings using SQL window functions.
    
    Returns:
    - Moving averages (30-day)
    - 30-day momentum percentage
    - Price rankings by date
    - Price 30 days ago for comparison
    """
    try:
        # Build the SQL query with window functions
        if ticker:
            query = text("""
                SELECT 
                    ticker,
                    date,
                    close_price,
                    AVG(close_price) OVER (
                        PARTITION BY ticker 
                        ORDER BY date 
                        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                    ) AS ma_30,
                    LAG(close_price, :days) OVER (PARTITION BY ticker ORDER BY date) AS price_days_ago,
                    CASE 
                        WHEN LAG(close_price, :days) OVER (PARTITION BY ticker ORDER BY date) IS NOT NULL 
                            AND LAG(close_price, :days) OVER (PARTITION BY ticker ORDER BY date) > 0
                        THEN ((close_price - LAG(close_price, :days) OVER (PARTITION BY ticker ORDER BY date)) 
                             / LAG(close_price, :days) OVER (PARTITION BY ticker ORDER BY date) * 100)
                        ELSE NULL
                    END AS momentum_pct,
                    RANK() OVER (PARTITION BY date ORDER BY close_price DESC) AS price_rank_today
                FROM stock_prices
                WHERE ticker = :ticker
                ORDER BY ticker, date DESC
                LIMIT :limit
            """)
            params = {"ticker": ticker.upper(), "days": days, "limit": limit}
        else:
            query = text("""
                SELECT 
                    ticker,
                    date,
                    close_price,
                    AVG(close_price) OVER (
                        PARTITION BY ticker 
                        ORDER BY date 
                        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                    ) AS ma_30,
                    LAG(close_price, :days) OVER (PARTITION BY ticker ORDER BY date) AS price_days_ago,
                    CASE 
                        WHEN LAG(close_price, :days) OVER (PARTITION BY ticker ORDER BY date) IS NOT NULL 
                            AND LAG(close_price, :days) OVER (PARTITION BY ticker ORDER BY date) > 0
                        THEN ((close_price - LAG(close_price, :days) OVER (PARTITION BY ticker ORDER BY date)) 
                             / LAG(close_price, :days) OVER (PARTITION BY ticker ORDER BY date) * 100)
                        ELSE NULL
                    END AS momentum_pct,
                    RANK() OVER (PARTITION BY date ORDER BY close_price DESC) AS price_rank_today
                FROM stock_prices
                ORDER BY date DESC, ticker
                LIMIT :limit
            """)
            params = {"days": days, "limit": limit}
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        # Convert to response format
        data = []
        for row in rows:
            data.append({
                "ticker": row[0],
                "date": row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
                "close_price": float(row[2]) if row[2] is not None else None,
                "ma_30": float(row[3]) if row[3] is not None else None,
                "price_days_ago": float(row[4]) if row[4] is not None else None,
                "momentum_pct": float(row[5]) if row[5] is not None else None,
                "price_rank_today": int(row[6]) if row[6] is not None else None
            })
        
        return {
            "query_type": "window_functions",
            "ticker": ticker,
            "days": days,
            "count": len(data),
            "data": data,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error in window functions analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing window functions query: {str(e)}"
        )


@router.get("/analytics/sector-performance", response_model=dict)
async def get_sector_performance_analysis(
    days: Optional[int] = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_read_session)  # Task 36: Use read replica for analytics
):
    """
    Advanced SQL: CTEs for Sector Performance Analysis
    
    Analyze sector performance using Common Table Expressions (CTEs).
    Calculates average prices, volumes, volatility, and price ranges by sector.
    
    Returns:
    - Average price and volume per sector
    - Price volatility and range
    - Volatility percentage
    - Company count per sector
    """
    try:
        # Build the SQL query with CTEs
        query = text("""
            WITH sector_avg AS (
                SELECT 
                    c.sector,
                    AVG(sp.close_price) AS avg_price,
                    AVG(sp.volume) AS avg_volume,
                    COUNT(DISTINCT sp.ticker) AS company_count
                FROM stock_prices sp
                JOIN companies c ON sp.ticker = c.ticker
                WHERE sp.date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
                  AND c.deleted_at IS NULL
                GROUP BY c.sector
            ),
            sector_volatility AS (
                SELECT 
                    c.sector,
                    STDDEV(sp.close_price) AS price_volatility,
                    MAX(sp.close_price) - MIN(sp.close_price) AS price_range
                FROM stock_prices sp
                JOIN companies c ON sp.ticker = c.ticker
                WHERE sp.date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
                  AND c.deleted_at IS NULL
                GROUP BY c.sector
            )
            SELECT 
                sa.sector,
                sa.avg_price,
                sa.avg_volume,
                sa.company_count,
                sv.price_volatility,
                sv.price_range,
                CASE 
                    WHEN sa.avg_price > 0 
                    THEN (sv.price_volatility / sa.avg_price * 100)
                    ELSE NULL
                END AS volatility_pct
            FROM sector_avg sa
            JOIN sector_volatility sv ON sa.sector = sv.sector
            ORDER BY volatility_pct DESC
        """)
        
        result = await db.execute(query, {"days": days})
        rows = result.fetchall()
        
        # Convert to response format
        sectors = []
        for row in rows:
            sectors.append({
                "sector": row[0] if row[0] else "Unknown",
                "avg_price": float(row[1]) if row[1] is not None else None,
                "avg_volume": float(row[2]) if row[2] is not None else None,
                "company_count": int(row[3]) if row[3] is not None else 0,
                "price_volatility": float(row[4]) if row[4] is not None else None,
                "price_range": float(row[5]) if row[5] is not None else None,
                "volatility_pct": float(row[6]) if row[6] is not None else None
            })
        
        return {
            "query_type": "cte_sector_performance",
            "days": days,
            "count": len(sectors),
            "sectors": sectors,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error in sector performance analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing CTE query: {str(e)}"
        )


@router.get("/analytics/price-trends", response_model=dict)
async def get_price_trends_analysis(
    ticker: Optional[str] = Query(None, description="Stock ticker symbol (optional)"),
    min_consecutive_days: Optional[int] = Query(5, ge=1, le=30, description="Minimum consecutive days of price increase"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: AsyncSession = Depends(get_read_session)  # Task 36: Use read replica for analytics
):
    """
    Advanced SQL: Recursive CTEs for Trend Detection
    
    Identify consecutive days of price increases using recursive CTEs.
    Useful for momentum trading signals and pattern recognition.
    
    Returns:
    - Ticker and date
    - Close price
    - Number of consecutive days of price increase
    """
    try:
        # Note: MySQL 8.0+ supports recursive CTEs
        # For older MySQL versions, we'll use a simpler approach with window functions
        
        # Use window functions to calculate consecutive days (more compatible than recursive CTEs)
        if ticker:
            # For a specific ticker, calculate consecutive days using window functions
            # Note: Must wrap in subquery to use window function result in WHERE clause
            query = text("""
                WITH price_sequence AS (
                    SELECT 
                        ticker,
                        date,
                        close_price,
                        LAG(close_price) OVER (PARTITION BY ticker ORDER BY date) AS prev_price,
                        CASE 
                            WHEN close_price > LAG(close_price) OVER (PARTITION BY ticker ORDER BY date)
                            THEN 1
                            ELSE 0
                        END AS is_increase,
                        ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date) AS seq_num
                    FROM stock_prices
                    WHERE ticker = :ticker
                    ORDER BY ticker, date
                ),
                grouped_increases AS (
                    SELECT 
                        ticker,
                        date,
                        close_price,
                        is_increase,
                        seq_num,
                        SUM(CASE WHEN is_increase = 0 THEN 1 ELSE 0 END) 
                            OVER (PARTITION BY ticker ORDER BY seq_num) AS group_id
                    FROM price_sequence
                ),
                consecutive_calculated AS (
                    SELECT 
                        ticker,
                        date,
                        close_price,
                        COUNT(*) OVER (
                            PARTITION BY ticker, group_id 
                            ORDER BY date 
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) AS consecutive_days
                    FROM grouped_increases
                    WHERE is_increase = 1
                )
                SELECT 
                    ticker,
                    date,
                    close_price,
                    consecutive_days
                FROM consecutive_calculated
                WHERE consecutive_days >= :min_days
                ORDER BY consecutive_days DESC, date DESC
                LIMIT :limit
            """)
            params = {"ticker": ticker.upper(), "min_days": min_consecutive_days, "limit": limit}
        else:
            # For all tickers, show recent price increases (simplified)
            query = text("""
                SELECT 
                    ticker,
                    date,
                    close_price,
                    LAG(close_price) OVER (PARTITION BY ticker ORDER BY date) AS prev_price,
                    CASE 
                        WHEN close_price > LAG(close_price) OVER (PARTITION BY ticker ORDER BY date)
                        THEN 1
                        ELSE 0
                    END AS is_increase
                FROM stock_prices
                WHERE date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
                ORDER BY ticker, date DESC
                LIMIT :limit
            """)
            params = {"limit": limit}
            # Note: Full consecutive days calculation for all tickers requires recursive CTE
            # This simplified version shows recent price increases
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        # Convert to response format
        trends = []
        for row in rows:
            trend_item = {
                "ticker": row[0],
                "date": row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
                "close_price": float(row[2]) if row[2] is not None else None
            }
            if ticker and len(row) > 3:
                # Has consecutive_days
                trend_item["consecutive_days"] = int(row[3]) if row[3] is not None else None
            elif not ticker and len(row) > 3:
                # Has is_increase
                trend_item["is_increase"] = bool(row[3]) if row[3] is not None else None
                if len(row) > 4:
                    trend_item["prev_price"] = float(row[4]) if row[4] is not None else None
            trends.append(trend_item)
        
        return {
            "query_type": "recursive_cte_price_trends",
            "ticker": ticker,
            "min_consecutive_days": min_consecutive_days,
            "count": len(trends),
            "trends": trends,
            "status": "success",
            "note": "For all tickers, this shows price increases. For specific ticker, shows consecutive days."
        }
        
    except Exception as e:
        logger.error(f"Error in price trends analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing recursive CTE query: {str(e)}"
        )


@router.get("/analytics/rolling-aggregations", response_model=dict)
async def get_rolling_aggregations(
    ticker: Optional[str] = Query(None, description="Stock ticker symbol (optional, returns all if not provided)"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: AsyncSession = Depends(get_read_session)  # Task 36: Use read replica for analytics
):
    """
    Advanced SQL: Rolling Window Aggregations
    
    Calculate rolling window aggregations including:
    - 7-day volume sum
    - 20-day moving average
    - 20-day high/low
    - Stochastic Oscillator
    
    Returns technical indicators useful for trading signals.
    """
    try:
        # Build the SQL query with rolling window aggregations
        if ticker:
            query = text("""
                SELECT 
                    ticker,
                    date,
                    close_price,
                    high_price,
                    low_price,
                    volume,
                    SUM(volume) OVER (
                        PARTITION BY ticker 
                        ORDER BY date 
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS volume_7day_sum,
                    AVG(close_price) OVER (
                        PARTITION BY ticker 
                        ORDER BY date 
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS ma_20,
                    MAX(high_price) OVER (
                        PARTITION BY ticker 
                        ORDER BY date 
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS high_20d,
                    MIN(low_price) OVER (
                        PARTITION BY ticker 
                        ORDER BY date 
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS low_20d,
                    CASE 
                        WHEN (MAX(high_price) OVER (
                                PARTITION BY ticker 
                                ORDER BY date 
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                            ) - MIN(low_price) OVER (
                                PARTITION BY ticker 
                                ORDER BY date 
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                            )) > 0
                        THEN (close_price - MIN(low_price) OVER (
                                PARTITION BY ticker 
                                ORDER BY date 
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                            )) / (MAX(high_price) OVER (
                                PARTITION BY ticker 
                                ORDER BY date 
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                            ) - MIN(low_price) OVER (
                                PARTITION BY ticker 
                                ORDER BY date 
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                            )) * 100
                        ELSE NULL
                    END AS stoch_oscillator
                FROM stock_prices
                WHERE ticker = :ticker
                ORDER BY ticker, date DESC
                LIMIT :limit
            """)
            params = {"ticker": ticker.upper(), "limit": limit}
        else:
            query = text("""
                SELECT 
                    ticker,
                    date,
                    close_price,
                    high_price,
                    low_price,
                    volume,
                    SUM(volume) OVER (
                        PARTITION BY ticker 
                        ORDER BY date 
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS volume_7day_sum,
                    AVG(close_price) OVER (
                        PARTITION BY ticker 
                        ORDER BY date 
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS ma_20,
                    MAX(high_price) OVER (
                        PARTITION BY ticker 
                        ORDER BY date 
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS high_20d,
                    MIN(low_price) OVER (
                        PARTITION BY ticker 
                        ORDER BY date 
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS low_20d,
                    CASE 
                        WHEN (MAX(high_price) OVER (
                                PARTITION BY ticker 
                                ORDER BY date 
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                            ) - MIN(low_price) OVER (
                                PARTITION BY ticker 
                                ORDER BY date 
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                            )) > 0
                        THEN (close_price - MIN(low_price) OVER (
                                PARTITION BY ticker 
                                ORDER BY date 
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                            )) / (MAX(high_price) OVER (
                                PARTITION BY ticker 
                                ORDER BY date 
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                            ) - MIN(low_price) OVER (
                                PARTITION BY ticker 
                                ORDER BY date 
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                            )) * 100
                        ELSE NULL
                    END AS stoch_oscillator
                FROM stock_prices
                ORDER BY date DESC, ticker
                LIMIT :limit
            """)
            params = {"limit": limit}
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        # Convert to response format
        data = []
        for row in rows:
            data.append({
                "ticker": row[0],
                "date": row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
                "close_price": float(row[2]) if row[2] is not None else None,
                "high_price": float(row[3]) if row[3] is not None else None,
                "low_price": float(row[4]) if row[4] is not None else None,
                "volume": int(row[5]) if row[5] is not None else None,
                "volume_7day_sum": int(row[6]) if row[6] is not None else None,
                "ma_20": float(row[7]) if row[7] is not None else None,
                "high_20d": float(row[8]) if row[8] is not None else None,
                "low_20d": float(row[9]) if row[9] is not None else None,
                "stoch_oscillator": float(row[10]) if row[10] is not None else None
            })
        
        return {
            "query_type": "rolling_aggregations",
            "ticker": ticker,
            "count": len(data),
            "data": data,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error in rolling aggregations analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing rolling aggregations query: {str(e)}"
        )


@router.get("/analytics/price-sentiment-correlation", response_model=dict)
async def get_price_sentiment_correlation(
    ticker: Optional[str] = Query(None, description="Stock ticker symbol (optional)"),
    days: Optional[int] = Query(30, ge=1, le=365, description="Number of days to analyze"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: AsyncSession = Depends(get_read_session)  # Task 36: Use read replica for analytics
):
    """
    Advanced SQL: Cross-Table Analytics - Price vs Sentiment Correlation
    
    Analyze correlation between stock price changes and news sentiment.
    Note: This endpoint uses stock price data from MySQL and would ideally
    join with news data from Firestore. For now, it analyzes price changes
    and can be extended to include sentiment data.
    
    Returns:
    - Price change percentages
    - Trading volume
    - Price volatility indicators
    """
    try:
        # Since news data is in Firestore (not MySQL), we'll create a simplified version
        # that analyzes price patterns and can be extended with sentiment data later
        if ticker:
            query = text("""
                SELECT 
                    sp.ticker,
                    sp.date,
                    sp.close_price,
                    sp.price_change_pct,
                    sp.volume,
                    AVG(sp.price_change_pct) OVER (
                        PARTITION BY sp.ticker 
                        ORDER BY sp.date 
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS avg_price_change_7d,
                    STDDEV(sp.price_change_pct) OVER (
                        PARTITION BY sp.ticker 
                        ORDER BY sp.date 
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS volatility_7d,
                    COUNT(*) OVER (
                        PARTITION BY sp.ticker 
                        ORDER BY sp.date 
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS trading_days_7d
                FROM stock_prices sp
                JOIN companies c ON sp.ticker = c.ticker
                WHERE sp.date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
                  AND sp.ticker = :ticker
                  AND c.deleted_at IS NULL
                ORDER BY sp.ticker, sp.date DESC
                LIMIT :limit
            """)
            params = {"ticker": ticker.upper(), "days": days, "limit": limit}
        else:
            query = text("""
                SELECT 
                    sp.ticker,
                    sp.date,
                    sp.close_price,
                    sp.price_change_pct,
                    sp.volume,
                    AVG(sp.price_change_pct) OVER (
                        PARTITION BY sp.ticker 
                        ORDER BY sp.date 
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS avg_price_change_7d,
                    STDDEV(sp.price_change_pct) OVER (
                        PARTITION BY sp.ticker 
                        ORDER BY sp.date 
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS volatility_7d,
                    COUNT(*) OVER (
                        PARTITION BY sp.ticker 
                        ORDER BY sp.date 
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) AS trading_days_7d
                FROM stock_prices sp
                JOIN companies c ON sp.ticker = c.ticker
                WHERE sp.date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
                  AND c.deleted_at IS NULL
                ORDER BY sp.date DESC, sp.ticker
                LIMIT :limit
            """)
            params = {"days": days, "limit": limit}
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        # Convert to response format
        data = []
        for row in rows:
            data.append({
                "ticker": row[0],
                "date": row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
                "close_price": float(row[2]) if row[2] is not None else None,
                "price_change_pct": float(row[3]) if row[3] is not None else None,
                "volume": int(row[4]) if row[4] is not None else None,
                "avg_price_change_7d": float(row[5]) if row[5] is not None else None,
                "volatility_7d": float(row[6]) if row[6] is not None else None,
                "trading_days_7d": int(row[7]) if row[7] is not None else None
            })
        
        return {
            "query_type": "price_sentiment_correlation",
            "ticker": ticker,
            "days": days,
            "count": len(data),
            "data": data,
            "status": "success",
            "note": "This endpoint analyzes price patterns. Full sentiment correlation requires joining with Firestore news data, which can be added in a future enhancement."
        }
        
    except Exception as e:
        logger.error(f"Error in price-sentiment correlation analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing price-sentiment correlation query: {str(e)}"
        )

