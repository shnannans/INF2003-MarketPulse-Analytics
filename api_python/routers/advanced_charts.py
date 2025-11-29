"""
Advanced Charts Endpoints (Task 64: Data Visualization Enhancements - Advanced Charts)
Provides data for advanced chart visualizations
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from config.database import get_read_session
from models.database_models import Company, StockPrice, SectorPerformance

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/charts/sector-heatmap", response_model=dict)
async def get_sector_heatmap_data(
    days: int = Query(30, ge=1, le=365, description="Number of days for analysis"),
    db: AsyncSession = Depends(get_read_session)
):
    """
    Get sector heatmap data (Task 64: Advanced Charts).
    Returns sector performance data for heatmap visualization.
    """
    try:
        db_session = db
        
        # Get sector performance data
        date_from = datetime.now().date() - timedelta(days=days)
        
        # Calculate sector metrics (simplified - avoid window functions in aggregates)
        sector_query = select(
            Company.sector,
            func.count(func.distinct(Company.ticker)).label("company_count"),
            func.avg(StockPrice.close_price).label("avg_price"),
            func.max(StockPrice.close_price).label("max_price"),
            func.min(StockPrice.close_price).label("min_price"),
            func.stddev(StockPrice.close_price).label("volatility")
        ).select_from(
            Company.__table__.join(
                StockPrice.__table__,
                Company.ticker == StockPrice.ticker
            )
        ).where(
            and_(
                Company.deleted_at.is_(None),
                StockPrice.date >= date_from
            )
        ).group_by(Company.sector)
        
        result = await db_session.execute(sector_query)
        rows = result.fetchall()
        
        sectors = []
        for row in rows:
            # Calculate price range percentage
            price_range_pct = 0
            if row.avg_price and row.avg_price > 0:
                price_range = (row.max_price - row.min_price) if (row.max_price and row.min_price) else 0
                price_range_pct = (price_range / row.avg_price * 100) if row.avg_price > 0 else 0
            
            sectors.append({
                "sector": row.sector,
                "company_count": row.company_count,
                "avg_price": float(row.avg_price) if row.avg_price else 0,
                "max_price": float(row.max_price) if row.max_price else 0,
                "min_price": float(row.min_price) if row.min_price else 0,
                "volatility": float(row.volatility) if row.volatility else 0,
                "price_range_pct": round(price_range_pct, 2)
            })
        
        return {
            "status": "success",
            "chart_type": "sector_heatmap",
            "days": days,
            "sectors": sectors,
            "count": len(sectors)
        }
        
    except Exception as e:
        logger.error(f"Error getting sector heatmap data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sector heatmap data: {str(e)}"
        )


@router.get("/charts/correlation-scatter", response_model=dict)
async def get_correlation_scatter_data(
    ticker: Optional[str] = Query(None, description="Stock ticker to filter by"),
    days: int = Query(30, ge=1, le=365, description="Number of days for analysis"),
    db: AsyncSession = Depends(get_read_session)
):
    """
    Get correlation scatter plot data (price vs sentiment) (Task 64: Advanced Charts).
    Returns price and sentiment data for scatter plot visualization.
    """
    try:
        db_session = db
        
        date_from = datetime.now().date() - timedelta(days=days)
        
        # Get price data
        price_query = select(
            StockPrice.ticker,
            StockPrice.date,
            StockPrice.close_price
        ).where(
            StockPrice.date >= date_from
        )
        
        if ticker:
            price_query = price_query.where(StockPrice.ticker == ticker.upper())
        
        price_result = await db_session.execute(price_query)
        price_rows = price_result.fetchall()
        
        # For sentiment, we would need to join with news/sentiment data
        # For now, we'll use a placeholder structure
        # In a real implementation, this would join with sentiment analysis data
        
        scatter_data = []
        for row in price_rows:
            scatter_data.append({
                "ticker": row.ticker,
                "date": row.date.isoformat() if row.date else None,
                "price": float(row.close_price) if row.close_price else 0,
                "sentiment": 0.0  # Placeholder - would come from sentiment analysis
            })
        
        return {
            "status": "success",
            "chart_type": "correlation_scatter",
            "ticker": ticker,
            "days": days,
            "data_points": scatter_data,
            "count": len(scatter_data)
        }
        
    except Exception as e:
        logger.error(f"Error getting correlation scatter data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting correlation scatter data: {str(e)}"
        )


@router.get("/charts/volatility-bands", response_model=dict)
async def get_volatility_bands_data(
    ticker: str = Query(..., description="Stock ticker"),
    days: int = Query(30, ge=1, le=365, description="Number of days for analysis"),
    period: int = Query(20, ge=5, le=50, description="Period for volatility calculation"),
    db: AsyncSession = Depends(get_read_session)
):
    """
    Get volatility bands data (Task 64: Advanced Charts).
    Returns price data with upper and lower volatility bands.
    """
    try:
        db_session = db
        
        date_from = datetime.now().date() - timedelta(days=days)
        
        # Get price data
        price_query = select(
            StockPrice.date,
            StockPrice.close_price,
            StockPrice.high_price,
            StockPrice.low_price
        ).where(
            and_(
                StockPrice.ticker == ticker.upper(),
                StockPrice.date >= date_from
            )
        ).order_by(StockPrice.date)
        
        result = await db_session.execute(price_query)
        rows = result.fetchall()
        
        prices = [float(row.close_price) if row.close_price else 0 for row in rows]
        dates = [row.date.isoformat() if row.date else None for row in rows]
        
        # Calculate volatility bands (Bollinger Bands style)
        volatility_bands = []
        for i in range(len(prices)):
            if i < period - 1:
                # Not enough data for volatility calculation
                volatility_bands.append({
                    "date": dates[i],
                    "price": prices[i],
                    "upper_band": prices[i],
                    "lower_band": prices[i],
                    "middle_band": prices[i]
                })
            else:
                # Calculate moving average and standard deviation
                window_prices = prices[i - period + 1:i + 1]
                ma = sum(window_prices) / len(window_prices)
                variance = sum((p - ma) ** 2 for p in window_prices) / len(window_prices)
                std_dev = variance ** 0.5
                
                # Bollinger Bands (2 standard deviations)
                upper_band = ma + (2 * std_dev)
                lower_band = ma - (2 * std_dev)
                
                volatility_bands.append({
                    "date": dates[i],
                    "price": prices[i],
                    "upper_band": round(upper_band, 2),
                    "lower_band": round(lower_band, 2),
                    "middle_band": round(ma, 2)
                })
        
        return {
            "status": "success",
            "chart_type": "volatility_bands",
            "ticker": ticker.upper(),
            "days": days,
            "period": period,
            "bands": volatility_bands,
            "count": len(volatility_bands)
        }
        
    except Exception as e:
        logger.error(f"Error getting volatility bands data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting volatility bands data: {str(e)}"
        )


@router.get("/charts/momentum-indicators", response_model=dict)
async def get_momentum_indicators_data(
    ticker: str = Query(..., description="Stock ticker"),
    days: int = Query(30, ge=1, le=365, description="Number of days for analysis"),
    db: AsyncSession = Depends(get_read_session)
):
    """
    Get momentum indicators data (Task 64: Advanced Charts).
    Returns momentum indicators like RSI, MACD, etc.
    """
    try:
        db_session = db
        
        date_from = datetime.now().date() - timedelta(days=days)
        
        # Get price data
        price_query = select(
            StockPrice.date,
            StockPrice.close_price,
            StockPrice.volume
        ).where(
            and_(
                StockPrice.ticker == ticker.upper(),
                StockPrice.date >= date_from
            )
        ).order_by(StockPrice.date)
        
        result = await db_session.execute(price_query)
        rows = result.fetchall()
        
        prices = [float(row.close_price) if row.close_price else 0 for row in rows]
        dates = [row.date.isoformat() if row.date else None for row in rows]
        volumes = [int(row.volume) if row.volume else 0 for row in rows]
        
        # Calculate RSI (Relative Strength Index)
        rsi_period = 14
        rsi_values = []
        for i in range(len(prices)):
            if i < rsi_period:
                rsi_values.append(None)
            else:
                # Calculate gains and losses
                changes = [prices[j] - prices[j - 1] for j in range(i - rsi_period + 1, i + 1)]
                gains = [c if c > 0 else 0 for c in changes]
                losses = [-c if c < 0 else 0 for c in changes]
                
                avg_gain = sum(gains) / rsi_period
                avg_loss = sum(losses) / rsi_period
                
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                
                rsi_values.append(round(rsi, 2))
        
        # Calculate MACD (Moving Average Convergence Divergence)
        macd_period_fast = 12
        macd_period_slow = 26
        macd_signal = 9
        
        ema_fast = []
        ema_slow = []
        macd_line = []
        signal_line = []
        
        for i in range(len(prices)):
            if i == 0:
                ema_fast.append(prices[i])
                ema_slow.append(prices[i])
            else:
                # EMA calculation
                k_fast = 2 / (macd_period_fast + 1)
                k_slow = 2 / (macd_period_slow + 1)
                ema_fast.append(prices[i] * k_fast + ema_fast[i - 1] * (1 - k_fast))
                ema_slow.append(prices[i] * k_slow + ema_slow[i - 1] * (1 - k_slow))
            
            # MACD line
            if i >= macd_period_slow - 1:
                macd_line.append(ema_fast[i] - ema_slow[i])
            else:
                macd_line.append(None)
        
        # Signal line (EMA of MACD line)
        for i in range(len(macd_line)):
            if macd_line[i] is None:
                signal_line.append(None)
            elif i == macd_period_slow - 1:
                signal_line.append(macd_line[i])
            else:
                k_signal = 2 / (macd_signal + 1)
                if signal_line[i - 1] is not None:
                    signal_line.append(macd_line[i] * k_signal + signal_line[i - 1] * (1 - k_signal))
                else:
                    signal_line.append(macd_line[i])
        
        momentum_data = []
        for i in range(len(prices)):
            momentum_data.append({
                "date": dates[i],
                "price": prices[i],
                "volume": volumes[i],
                "rsi": rsi_values[i],
                "macd": round(macd_line[i], 2) if macd_line[i] is not None else None,
                "signal": round(signal_line[i], 2) if signal_line[i] is not None else None,
                "histogram": round((macd_line[i] - signal_line[i]), 2) if (macd_line[i] is not None and signal_line[i] is not None) else None
            })
        
        return {
            "status": "success",
            "chart_type": "momentum_indicators",
            "ticker": ticker.upper(),
            "days": days,
            "indicators": momentum_data,
            "count": len(momentum_data)
        }
        
    except Exception as e:
        logger.error(f"Error getting momentum indicators data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting momentum indicators data: {str(e)}"
        )


@router.get("/charts/technical-analysis", response_model=dict)
async def get_technical_analysis_data(
    ticker: str = Query(..., description="Stock ticker"),
    days: int = Query(30, ge=1, le=365, description="Number of days for analysis"),
    indicators: Optional[str] = Query("RSI,MACD,BB", description="Comma-separated list of indicators: RSI, MACD, BB"),
    db: AsyncSession = Depends(get_read_session)
):
    """
    Get technical analysis data (Task 64: Advanced Charts).
    Returns comprehensive technical analysis indicators.
    """
    try:
        db_session = db
        
        # Parse indicators
        indicator_list = [ind.strip().upper() for ind in indicators.split(",")] if indicators else ["RSI", "MACD", "BB"]
        
        # Get base data (reuse momentum indicators for RSI and MACD)
        momentum_data = await get_momentum_indicators_data(ticker, days, db)
        
        # Get volatility bands for Bollinger Bands
        volatility_data = await get_volatility_bands_data(ticker, days, 20, db)
        
        # Combine data
        technical_data = {
            "status": "success",
            "chart_type": "technical_analysis",
            "ticker": ticker.upper(),
            "days": days,
            "indicators": indicator_list,
            "data": []
        }
        
        # Merge momentum and volatility data
        momentum_dict = {item["date"]: item for item in momentum_data.get("indicators", [])}
        volatility_dict = {item["date"]: item for item in volatility_data.get("bands", [])}
        
        all_dates = sorted(set(list(momentum_dict.keys()) + list(volatility_dict.keys())))
        
        for date in all_dates:
            tech_item = {
                "date": date,
                "price": momentum_dict.get(date, {}).get("price") or volatility_dict.get(date, {}).get("price", 0)
            }
            
            if "RSI" in indicator_list:
                tech_item["rsi"] = momentum_dict.get(date, {}).get("rsi")
            
            if "MACD" in indicator_list:
                tech_item["macd"] = momentum_dict.get(date, {}).get("macd")
                tech_item["signal"] = momentum_dict.get(date, {}).get("signal")
                tech_item["histogram"] = momentum_dict.get(date, {}).get("histogram")
            
            if "BB" in indicator_list:
                tech_item["upper_band"] = volatility_dict.get(date, {}).get("upper_band")
                tech_item["lower_band"] = volatility_dict.get(date, {}).get("lower_band")
                tech_item["middle_band"] = volatility_dict.get(date, {}).get("middle_band")
            
            technical_data["data"].append(tech_item)
        
        technical_data["count"] = len(technical_data["data"])
        
        return technical_data
        
    except Exception as e:
        logger.error(f"Error getting technical analysis data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting technical analysis data: {str(e)}"
        )

