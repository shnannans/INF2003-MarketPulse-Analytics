from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from typing import Optional
import logging
from datetime import datetime, timedelta

from config.database import get_mysql_session
from models.database_models import StockPrice, Company
from utils.error_handlers import handle_database_error
from utils.live_stock_service import get_stock_timeline as get_live_stock_timeline

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/timeline", response_model=dict)
async def get_timeline_rest_style(
    days: Optional[int] = Query(30, ge=1, le=365, description="Number of days to retrieve"),
    threshold: Optional[float] = Query(4.0, ge=0.1, le=50.0, description="Minimum price change percentage for events"),
    ticker: Optional[str] = Query(None, description="Optional stock ticker symbol"),
    live: Optional[bool] = Query(True, description="Use live data (True) or fallback to database (False)"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get timeline data for stock prices and market events (REST-style endpoint).
    Now supports dynamic timeline generation with real-time market events.
    """
    return await get_timeline_internal(days, threshold, ticker, live, db)

async def get_timeline_internal(
    days: int,
    threshold: float,
    ticker: Optional[str],
    live: bool,
    db: AsyncSession
):
    """
    Internal function for timeline with live and database fallback.
    """
    try:
        if live:
            # Use live timeline service for market events
            logger.info(f"Generating live timeline for {days} days"
                        + (f" with ticker {ticker}" if ticker else""))
            result = await get_live_stock_timeline(days)

            if result and result.get("status") == "success" and result.get("events"):
                # If we have a specific ticker, try to get stock-specific events too
                if ticker:
                    # Add stock-specific information to the timeline
                    from utils.live_stock_service import get_stock_analysis
                    try:
                        stock_data = await get_stock_analysis(ticker, min(days, 30))
                        if stock_data.get("analysis"):
                            # Add significant price movements as events
                            for data_point in stock_data["analysis"][:5]:  # Last 5 data points
                                change_pct = data_point.get("price_change_pct")
                                if change_pct and abs(change_pct) > 3.0:
                                    event_type = "gain" if change_pct > 0 else "decline"
                                    result["events"].insert(0, {
                                        "date": data_point.get("date"),
                                        "title": f"{ticker} {event_type.title()}: {change_pct:+.2f}%",
                                        "description": f"Significant price movement for {ticker}",
                                        "type": "stock_movement",
                                        "ticker": ticker,
                                        "price": data_point.get("close_price"),
                                        "impact": "high" if abs(change_pct) > 5.0 else "medium"
                                    })
                    except Exception as e:
                        logger.warning(f"Could not add stock-specific timeline events for {ticker}: {e}")

                logger.info(f"Live timeline service returned {len(result.get('events', []))} events")
                return {
                    **result,
                    "filters": {
                        "ticker": ticker,
                        "days": days,
                        "live_mode": True
                    }
                }
            else:
                logger.warning("Live timeline service failed, falling back to database")

        # Fallback to database if live fails or is disabled
        logger.info("Using database fallback for timeline data")

        # Build query with companies table join
        timeline_stmt = select(
            StockPrice.date,
            StockPrice.ticker,
            Company.company_name,
            StockPrice.price_change_pct
        ).select_from(
            StockPrice.__table__.join(Company, StockPrice.ticker == Company.ticker)
        ).where(
            and_(
                StockPrice.date >= text(f"DATE_SUB(CURDATE(), INTERVAL {days} DAY)"),
                func.abs(StockPrice.price_change_pct) > threshold
            )
        ).order_by(
            StockPrice.date.desc(),
            func.abs(StockPrice.price_change_pct).desc()
        ).limit(10)

        result = await db.execute(timeline_stmt)
        timeline_data = result.fetchall()

        if live:
            # If database also fails but live was attempted, return live service result
            result = await get_live_stock_timeline(days, ticker=ticker)
            return {
            **result,
            "filters": {
                "ticker": ticker if ticker else None,
                "days": days,
                "live_mode": True
            }
        }
            
        # Format the timeline data as events - matching PHP structure
        events = []
        for row in timeline_data:
            change_pct = float(row.price_change_pct) if row.price_change_pct else 0
            direction = 'increased' if change_pct > 0 else 'decreased'

            events.append({
                "date": row.date.strftime('%Y-%m-%d'),
                "title": f"{row.company_name} ({row.ticker}) {direction} by {abs(change_pct):.1f}%",
                "ticker": row.ticker,
                "company_name": row.company_name,
                "price_change_pct": change_pct,
                "type": "price_movement"
            })

        return {
            "events": events,
            "count": len(events),
            "status": "success",
            "filters": {
                "ticker": ticker,
                "days": days,
                "live_mode": live
            }
        }

    except Exception as e:
        logger.error(f"Error fetching timeline data: {str(e)}")
        handle_database_error(e)

# Keep the old function name for backward compatibility
get_timeline = get_timeline_internal