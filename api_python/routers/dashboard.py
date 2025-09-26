from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import Optional
import logging
from datetime import datetime, timedelta

from config.database import get_mysql_session, get_mongo_collection
from models.database_models import Company, StockPrice
from models.pydantic_models import DashboardSummaryResponse
from utils.error_handlers import handle_database_error

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/dashboard", response_model=dict)
async def get_dashboard(
    days: Optional[int] = Query(7, ge=1, le=365, description="Number of days for analysis"),
    db: AsyncSession = Depends(get_mysql_session),
    collection: AsyncIOMotorCollection = Depends(get_mongo_collection)
):
    """
    Get dashboard summary statistics.
    """
    try:
        # Initialize default values
        company_count = 0
        price_records = 0
        latest_date = 'N/A'
        total_articles = 0
        recent_articles = 0
        avg_sentiment = 0.0

        # Get MySQL statistics
        try:
            # Company count
            company_stmt = select(func.count(Company.ticker))
            company_result = await db.execute(company_stmt)
            company_count = company_result.scalar() or 0

            # Price records count
            price_stmt = select(func.count(StockPrice.id))
            price_result = await db.execute(price_stmt)
            price_records = price_result.scalar() or 0

            # Latest price date
            latest_stmt = select(func.max(StockPrice.date))
            latest_result = await db.execute(latest_stmt)
            latest_date_raw = latest_result.scalar()
            latest_date = latest_date_raw.strftime('%Y-%m-%d') if latest_date_raw else 'N/A'

        except Exception as e:
            logger.error(f"MySQL queries failed: {str(e)}")

        # Get MongoDB statistics
        try:
            if collection:
                # Total articles
                total_articles = await collection.count_documents({})

                # Recent articles (last 24 hours)
                recent_cutoff = datetime.now() - timedelta(days=1)
                recent_articles = await collection.count_documents({
                    'published_date': {'$gte': recent_cutoff}
                })

                # Average sentiment
                sentiment_pipeline = [
                    {
                        '$group': {
                            '_id': None,
                            'avg_sentiment': {'$avg': '$sentiment_analysis.overall_score'}
                        }
                    }
                ]

                async for result in collection.aggregate(sentiment_pipeline):
                    avg_sentiment = result.get('avg_sentiment', 0.0) or 0.0
                    break

        except Exception as e:
            logger.error(f"MongoDB queries failed: {str(e)}")

        return {
            "total_companies": company_count,
            "total_articles": total_articles,
            "recent_articles": recent_articles,
            "total_price_records": price_records,
            "latest_price_date": latest_date,
            "avg_sentiment": round(avg_sentiment, 3),
            "portfolio_value": "$1,234,567",  # Mock value
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        handle_database_error(e)

@router.get("/sector_heatmap")
async def get_sector_heatmap(
    days: Optional[int] = Query(7, ge=1, le=365, description="Number of days for analysis"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Sector performance heatmap data.
    """
    try:
        # This is a simplified implementation. In production, you would:
        # 1. Query stock_prices table grouped by sector
        # 2. Calculate performance metrics per sector
        # 3. Get sentiment data by sector from MongoDB

        # For now, returning realistic mock data that matches frontend expectations
        sectors_data = [
            {"sector": "Technology", "change_percent": 2.4, "sentiment": 0.23},
            {"sector": "Healthcare", "change_percent": 1.8, "sentiment": 0.15},
            {"sector": "Finance", "change_percent": -0.7, "sentiment": -0.08},
            {"sector": "Energy", "change_percent": -1.2, "sentiment": -0.18},
            {"sector": "Consumer", "change_percent": 0.9, "sentiment": 0.05},
            {"sector": "Industrial", "change_percent": 1.3, "sentiment": 0.12}
        ]

        return {
            "sectors": sectors_data,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error getting sector heatmap: {str(e)}")
        handle_database_error(e)

