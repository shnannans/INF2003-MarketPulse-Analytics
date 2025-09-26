from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import Optional
import logging
from datetime import datetime, timedelta
import statistics

from config.database import get_mysql_session, get_mongo_collection
from models.database_models import StockPrice
from models.pydantic_models import CorrelationQuery, CorrelationResponse
from utils.error_handlers import handle_database_error

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/correlation", response_model=dict)
async def get_correlation(
    ticker: str = Query(..., description="Stock ticker symbol"),
    date: Optional[str] = Query(None, description="Specific date for correlation analysis (YYYY-MM-DD)"),
    days_window: Optional[int] = Query(7, ge=3, le=30, description="Days window around the date for analysis"),
    db: AsyncSession = Depends(get_mysql_session),
    collection: AsyncIOMotorCollection = Depends(get_mongo_collection)
):
    """
    Calculate real correlation between stock price movements and sentiment scores.
    Analyzes price changes and sentiment data within a time window around the specified date.
    """
    try:
        ticker = ticker.upper()

        # Use current date if not specified
        if not date:
            target_date = datetime.now()
        else:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                target_date = datetime.now()

        # Define analysis window
        start_date = target_date - timedelta(days=days_window)
        end_date = target_date + timedelta(days=days_window)

        # Get stock price data for the window
        price_stmt = select(
            StockPrice.date,
            StockPrice.close_price,
            StockPrice.price_change_pct
        ).where(
            and_(
                StockPrice.ticker == ticker,
                StockPrice.date >= start_date.date(),
                StockPrice.date <= end_date.date()
            )
        ).order_by(StockPrice.date)

        price_result = await db.execute(price_stmt)
        price_data = price_result.fetchall()

        if not price_data:
            return {
                "ticker": ticker,
                "date": date,
                "correlation": 0.0,
                "message": f"No price data found for {ticker} in the specified window",
                "data_points": 0,
                "status": "no_data"
            }

        # Get sentiment data for the same window
        sentiment_data = []
        if collection:
            try:
                # Query MongoDB for sentiment data
                sentiment_filter = {
                    'ticker': ticker,
                    'published_date': {
                        '$gte': start_date,
                        '$lte': end_date
                    }
                }

                cursor = collection.find(
                    sentiment_filter,
                    {
                        'published_date': 1,
                        'sentiment_analysis.overall_score': 1
                    }
                ).sort('published_date', 1)

                async for doc in cursor:
                    if doc.get('sentiment_analysis', {}).get('overall_score') is not None:
                        sentiment_data.append({
                            'date': doc['published_date'].date(),
                            'sentiment': doc['sentiment_analysis']['overall_score']
                        })

            except Exception as e:
                logger.warning(f"Error fetching sentiment data: {e}")

        if not sentiment_data:
            return {
                "ticker": ticker,
                "date": date,
                "correlation": 0.0,
                "message": f"No sentiment data found for {ticker} in the specified window",
                "price_points": len(price_data),
                "sentiment_points": 0,
                "status": "no_sentiment_data"
            }

        # Align price and sentiment data by date
        aligned_data = []
        sentiment_by_date = {item['date']: item['sentiment'] for item in sentiment_data}

        for price_row in price_data:
            price_date = price_row.date
            price_change = float(price_row.price_change_pct or 0)

            # Find sentiment data for the same date or closest date
            sentiment_score = sentiment_by_date.get(price_date)
            if sentiment_score is None:
                # Try to find sentiment within 1 day
                for delta in [-1, 1, -2, 2]:
                    check_date = price_date + timedelta(days=delta)
                    if check_date in sentiment_by_date:
                        sentiment_score = sentiment_by_date[check_date]
                        break

            if sentiment_score is not None:
                aligned_data.append({
                    'date': price_date,
                    'price_change': price_change,
                    'sentiment': float(sentiment_score)
                })

        if len(aligned_data) < 3:
            return {
                "ticker": ticker,
                "date": date,
                "correlation": 0.0,
                "message": f"Insufficient aligned data points ({len(aligned_data)}) for correlation analysis",
                "price_points": len(price_data),
                "sentiment_points": len(sentiment_data),
                "aligned_points": len(aligned_data),
                "status": "insufficient_data"
            }

        # Calculate correlation
        price_changes = [item['price_change'] for item in aligned_data]
        sentiment_scores = [item['sentiment'] for item in aligned_data]

        try:
            # Calculate Pearson correlation coefficient
            correlation = statistics.correlation(price_changes, sentiment_scores)
        except statistics.StatisticsError:
            correlation = 0.0

        # Determine correlation strength
        abs_corr = abs(correlation)
        if abs_corr >= 0.7:
            strength = "strong"
        elif abs_corr >= 0.5:
            strength = "moderate"
        elif abs_corr >= 0.3:
            strength = "weak"
        else:
            strength = "very weak"

        direction = "positive" if correlation > 0 else "negative" if correlation < 0 else "none"

        return {
            "ticker": ticker,
            "date": date,
            "correlation": round(correlation, 4),
            "strength": strength,
            "direction": direction,
            "analysis_window": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "days": days_window * 2 + 1
            },
            "data_summary": {
                "price_points": len(price_data),
                "sentiment_points": len(sentiment_data),
                "aligned_points": len(aligned_data),
                "avg_price_change": round(statistics.mean(price_changes), 4) if price_changes else 0,
                "avg_sentiment": round(statistics.mean(sentiment_scores), 4) if sentiment_scores else 0
            },
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error calculating correlation for {ticker}: {str(e)}")
        handle_database_error(e)

