from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from typing import Optional
import logging
import random

from config.database import get_mysql_session
from models.database_models import MarketIndex
from models.pydantic_models import IndicesQuery, IndicesResponse
from utils.error_handlers import handle_database_error
from utils.live_stock_service import get_market_indices as get_live_market_indices

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/indices", response_model=dict)
async def get_indices_rest_style(
    days: Optional[int] = Query(30, ge=1, le=365, description="Number of days to retrieve"),
    live: Optional[bool] = Query(True, description="Use live data (True) or fallback to database (False)"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get market indices data and trends (REST-style endpoint).
    Now supports real-time data fetching with yfinance integration.
    """
    return await get_indices_internal(days, live, db)

async def get_indices_internal(
    days: int,
    live: bool,
    db: AsyncSession
):
    """
    Internal function for market indices with live and database fallback.
    """
    try:
        if live:
            # Use live data service
            logger.info(f"Fetching live market indices for {days} days")
            result = await get_live_market_indices(days)

            if result and result.get("status") == "success" and result.get("indices"):
                logger.info(f"Live indices service returned {len(result.get('indices', []))} indices")
                return result
            else:
                logger.warning("Live indices service failed, falling back to database")

        # Fallback to database if live fails or is disabled
        logger.info("Using database fallback for indices data")

        # Get real market indices data
        indices_stmt = select(
            MarketIndex.symbol,
            MarketIndex.index_name,
            MarketIndex.date,
            MarketIndex.close_price,
            MarketIndex.change_pct
        ).where(
            MarketIndex.date >= text(f"DATE_SUB(CURDATE(), INTERVAL {days} DAY)")
        ).order_by(MarketIndex.symbol, MarketIndex.date.asc())

        result = await db.execute(indices_stmt)
        indices_data = result.fetchall()

        if not indices_data:
            if live:
                # If database also fails but live was attempted, return live service result
                return await get_live_market_indices(days)

            # Fallback to mock data if no real data available
            from datetime import datetime, timedelta

            dates = []
            for i in range(days - 1, -1, -1):
                date_obj = datetime.now() - timedelta(days=i)
                dates.append(date_obj.strftime('%Y-%m-%d'))

            trend = [{"date": date} for date in dates]

            indices = [
                {
                    "name": "S&P 500",
                    "values": [4300 + random.randint(-20, 20) for _ in dates]
                },
                {
                    "name": "NASDAQ",
                    "values": [15000 + random.randint(-50, 50) for _ in dates]
                }
            ]

            summary = [
                {
                    "name": "S&P 500",
                    "change_percent": round(random.uniform(-2.0, 2.0), 2)
                },
                {
                    "name": "NASDAQ",
                    "change_percent": round(random.uniform(-2.0, 2.0), 2)
                }
            ]

            return {
                "trend": trend,
                "indices": indices,
                "summary": summary,
                "data_source": "mock_fallback",
                "status": "success",
                "note": "Using mock data - run data collection to get real indices"
            }

        else:
            # Process real indices data
            grouped_data = {}
            for row in indices_data:
                index_name = row.index_name
                if index_name not in grouped_data:
                    grouped_data[index_name] = []
                grouped_data[index_name].append(row)

            # Extract unique dates and sort them
            all_dates = sorted(list(set(row.date.strftime('%Y-%m-%d') for row in indices_data)))
            trend = [{"date": date} for date in all_dates]

            # Build indices data
            indices = []
            summary = []

            for index_name, data in grouped_data.items():
                values = [float(row.close_price) for row in sorted(data, key=lambda x: x.date)]
                indices.append({
                    "name": index_name,
                    "values": values
                })

                # Get latest change percentage
                if data:
                    latest_change = sorted(data, key=lambda x: x.date, reverse=True)[0].change_pct
                    summary.append({
                        "name": index_name,
                        "change_percent": round(float(latest_change or 0), 2)
                    })

            return {
                "trend": trend,
                "indices": indices,
                "summary": summary,
                "data_source": "database_fallback",
                "status": "success"
            }

    except Exception as e:
        logger.error(f"Error fetching indices data: {str(e)}")
        handle_database_error(e)

# Keep the old function name for backward compatibility
get_indices = get_indices_internal