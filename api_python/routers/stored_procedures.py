"""
Stored Procedures and Functions Endpoints (Tasks 44-45)
Provides endpoints to call stored procedures and user-defined functions
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from config.database import get_mysql_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/procedures/update-company-with-prices", response_model=dict)
async def call_update_company_with_prices(
    ticker: str = Query(..., description="Stock ticker symbol"),
    company_name: str = Query(None, description="Company name"),
    sector: str = Query(None, description="Company sector"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Call stored procedure to update company and recalculate metrics (Task 44: Stored Procedures).
    
    This procedure:
    - Updates company information
    - Recalculates moving averages for recent prices
    - Performs atomic operation
    """
    try:
        result = await db.execute(
            text("CALL sp_update_company_with_prices(:ticker, :company_name, :sector)"),
            {
                "ticker": ticker.upper(),
                "company_name": company_name,
                "sector": sector
            }
        )
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Company {ticker} updated and metrics recalculated",
            "procedure": "sp_update_company_with_prices"
        }
        
    except Exception as e:
        logger.error(f"Error calling stored procedure: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calling stored procedure: {str(e)}"
        )


@router.post("/procedures/recalculate-moving-averages", response_model=dict)
async def call_recalculate_moving_averages(
    ticker: str = Query(..., description="Stock ticker symbol"),
    days: int = Query(30, ge=1, le=365, description="Number of days to recalculate"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Call stored procedure to recalculate moving averages (Task 44: Stored Procedures).
    
    Recalculates MA_5, MA_20, MA_50, and MA_200 for the specified ticker.
    """
    try:
        result = await db.execute(
            text("CALL sp_recalculate_moving_averages(:ticker, :days)"),
            {
                "ticker": ticker.upper(),
                "days": days
            }
        )
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Moving averages recalculated for {ticker} (last {days} days)",
            "procedure": "sp_recalculate_moving_averages"
        }
        
    except Exception as e:
        logger.error(f"Error calling stored procedure: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calling stored procedure: {str(e)}"
        )


@router.get("/functions/rsi", response_model=dict)
async def get_rsi_calculation(
    ticker: str = Query(..., description="Stock ticker symbol"),
    date: str = Query(None, description="Date for RSI calculation (YYYY-MM-DD), defaults to latest"),
    period: int = Query(14, ge=1, le=30, description="RSI period (default 14)"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Calculate RSI using user-defined function (Task 45: User-Defined Functions).
    
    Returns Relative Strength Index for the specified ticker and date.
    """
    try:
        from datetime import datetime
        
        # If no date provided, use latest date
        if not date:
            result = await db.execute(
                text("SELECT MAX(date) FROM stock_prices WHERE ticker = :ticker"),
                {"ticker": ticker.upper()}
            )
            latest_date = result.scalar()
            if not latest_date:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No price data found for {ticker}"
                )
            date = latest_date
        
        result = await db.execute(
            text("SELECT fn_calculate_rsi(:ticker, :date, :period) AS rsi"),
            {
                "ticker": ticker.upper(),
                "date": date,
                "period": period
            }
        )
        rsi = result.scalar()
        
        return {
            "status": "success",
            "ticker": ticker.upper(),
            "date": str(date),
            "period": period,
            "rsi": float(rsi) if rsi else None,
            "message": "RSI calculated using user-defined function"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating RSI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating RSI: {str(e)}"
        )


@router.get("/functions/price-change-pct", response_model=dict)
async def get_price_change_pct(
    current_price: float = Query(..., description="Current price"),
    previous_price: float = Query(..., description="Previous price"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Calculate price change percentage using user-defined function (Task 45: User-Defined Functions).
    """
    try:
        result = await db.execute(
            text("SELECT fn_calculate_price_change_pct(:current, :previous) AS change_pct"),
            {
                "current": current_price,
                "previous": previous_price
            }
        )
        change_pct = result.scalar()
        
        return {
            "status": "success",
            "current_price": current_price,
            "previous_price": previous_price,
            "change_pct": float(change_pct) if change_pct else None,
            "message": "Price change percentage calculated using user-defined function"
        }
        
    except Exception as e:
        logger.error(f"Error calculating price change: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating price change: {str(e)}"
        )


@router.get("/functions/volatility", response_model=dict)
async def get_volatility(
    ticker: str = Query(..., description="Stock ticker symbol"),
    date: str = Query(None, description="Date for volatility calculation (YYYY-MM-DD), defaults to latest"),
    period: int = Query(30, ge=1, le=365, description="Volatility period in days (default 30)"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Calculate volatility using user-defined function (Task 45: User-Defined Functions).
    """
    try:
        from datetime import datetime
        
        # If no date provided, use latest date
        if not date:
            result = await db.execute(
                text("SELECT MAX(date) FROM stock_prices WHERE ticker = :ticker"),
                {"ticker": ticker.upper()}
            )
            latest_date = result.scalar()
            if not latest_date:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No price data found for {ticker}"
                )
            date = latest_date
        
        result = await db.execute(
            text("SELECT fn_calculate_volatility(:ticker, :date, :period) AS volatility"),
            {
                "ticker": ticker.upper(),
                "date": date,
                "period": period
            }
        )
        volatility = result.scalar()
        
        return {
            "status": "success",
            "ticker": ticker.upper(),
            "date": str(date),
            "period": period,
            "volatility": float(volatility) if volatility else None,
            "message": "Volatility calculated using user-defined function"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating volatility: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating volatility: {str(e)}"
        )


@router.get("/functions/stock-prices-with-rsi", response_model=dict)
async def get_stock_prices_with_rsi(
    ticker: str = Query(..., description="Stock ticker symbol"),
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    period: int = Query(14, ge=1, le=30, description="RSI period (default 14)"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get stock prices with RSI calculated using user-defined function (Task 45: User-Defined Functions).
    """
    try:
        result = await db.execute(
            text("""
                SELECT 
                    ticker,
                    date,
                    close_price,
                    fn_calculate_rsi(ticker, date, :period) AS rsi
                FROM stock_prices
                WHERE ticker = :ticker
                  AND date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
                ORDER BY date DESC
            """),
            {
                "ticker": ticker.upper(),
                "days": days,
                "period": period
            }
        )
        rows = result.fetchall()
        
        data = []
        for row in rows:
            data.append({
                "ticker": row[0],
                "date": str(row[1]),
                "close_price": float(row[2]) if row[2] else None,
                "rsi": float(row[3]) if row[3] else None
            })
        
        return {
            "status": "success",
            "data": data,
            "count": len(data),
            "ticker": ticker.upper(),
            "period": period,
            "message": "Stock prices with RSI calculated using user-defined function"
        }
        
    except Exception as e:
        logger.error(f"Error getting stock prices with RSI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stock prices with RSI: {str(e)}"
        )

