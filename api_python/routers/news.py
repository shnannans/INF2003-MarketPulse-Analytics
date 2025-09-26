from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import Optional
import logging
from datetime import datetime, timedelta

from config.database import get_mongo_collection
from models.pydantic_models import NewsQuery, NewsResponse
from utils.error_handlers import handle_database_error
from utils.news_service import get_financial_news

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/news", response_model=dict)
async def get_news_rest_style(
    ticker: Optional[str] = Query("", description="Stock ticker to filter by"),
    days: Optional[int] = Query(7, ge=1, le=30, description="Number of days to look back"),
    sentiment: Optional[str] = Query("", regex="^(positive|negative|neutral|)$", description="Sentiment filter"),
    limit: Optional[int] = Query(20, ge=1, le=100, description="Maximum number of articles"),
    live: Optional[bool] = Query(True, description="Use live NewsAPI (True) or fallback to MongoDB (False)"),
    collection: AsyncIOMotorCollection = Depends(get_mongo_collection)
):
    """
    Get news articles with real-time sentiment analysis (REST-style endpoint).
    Supports both live NewsAPI integration and MongoDB fallback.
    """
    return await get_news_internal(ticker, days, sentiment, limit, live, collection)

async def get_news_internal(
    ticker: Optional[str] = Query("", description="Stock ticker to filter by"),
    days: Optional[int] = Query(7, ge=1, le=30, description="Number of days to look back"),
    sentiment: Optional[str] = Query("", regex="^(positive|negative|neutral|)$", description="Sentiment filter"),
    limit: Optional[int] = Query(20, ge=1, le=100, description="Maximum number of articles"),
    live: Optional[bool] = Query(True, description="Use live NewsAPI (True) or fallback to MongoDB (False)"),
    collection: AsyncIOMotorCollection = Depends(get_mongo_collection)
):
    """
    Get news articles with real-time sentiment analysis.
    Supports both live NewsAPI integration and MongoDB fallback.
    """
    try:
        articles = []

        if live:
            # Use live NewsAPI service with real-time sentiment analysis
            logger.info(f"Fetching live news for ticker: {ticker}, days: {days}, sentiment: {sentiment}")
            articles = await get_financial_news(ticker=ticker, days=days, sentiment_filter=sentiment)

            # Apply limit
            if len(articles) > limit:
                articles = articles[:limit]

            logger.info(f"Live news service returned {len(articles)} articles")

        # Fallback to MongoDB if live fails or returns no results
        if not articles and collection is not None:
            logger.info("No live news articles found, falling back to MongoDB for news articles")

            # Build query filter for MongoDB
            import time
            cutoff_timestamp_ms = int((time.time() - days * 86400) * 1000)
            filter_query = {
                'published_date': {'$gte': cutoff_timestamp_ms}
            }

            # Add ticker filter
            if ticker:
                filter_query['ticker'] = ticker.upper()

            # Add sentiment filter
            if sentiment:
                if sentiment == 'positive':
                    filter_query['sentiment_analysis.overall_score'] = {'$gt': 0.1}
                elif sentiment == 'negative':
                    filter_query['sentiment_analysis.overall_score'] = {'$lt': -0.1}
                elif sentiment == 'neutral':
                    filter_query['sentiment_analysis.overall_score'] = {
                        '$gte': -0.1,
                        '$lte': 0.1
                    }

            # Set up query options
            projection = {
                'article_id': 1,
                'ticker': 1,
                'title': 1,
                'content': 1,
                'published_date': 1,
                'source': 1,
                'sentiment_analysis': 1,
                'extracted_entities': 1,
                'metadata': 1
            }

            # Execute query
            cursor = collection.find(filter_query, projection)
            cursor = cursor.sort('published_date', -1).limit(limit)
            articles_raw = await cursor.to_list(length=limit)

            # Format articles
            for article in articles_raw:
                # Convert ObjectId to string
                article['_id'] = str(article['_id'])

                # Format published_date - match MongoDB UTCDateTime handling
                if 'published_date' in article and article['published_date']:
                    # Handle MongoDB UTCDateTime objects
                    if hasattr(article['published_date'], 'as_datetime'):
                        article['published_date'] = article['published_date'].as_datetime().strftime('%Y-%m-%dT%H:%M:%S%z')
                    elif hasattr(article['published_date'], 'isoformat'):
                        article['published_date'] = article['published_date'].isoformat()
                    elif isinstance(article['published_date'], (int, float)):
                        # Handle timestamp in milliseconds
                        dt = datetime.fromtimestamp(article['published_date'] / 1000)
                        article['published_date'] = dt.strftime('%Y-%m-%dT%H:%M:%S%z')

                articles.append(article)

            logger.info(f"MongoDB fallback returned {len(articles)} articles")

        # Determine the message based on what we have
        message = ""
        if not articles:
            if ticker:
                message = f"No news available for {ticker.upper()}"
            else:
                message = "No news articles available"
        else:
            message = f"Found {len(articles)} articles"

        return {
            "articles": articles,
            "count": len(articles),
            "message": message,
            "filters": {
                "ticker": ticker,
                "days": days,
                "sentiment": sentiment,
                "live_mode": live
            },
            "metadata": {
                "data_source": "newsapi_live" if live and articles else "mongodb_fallback" if articles else "no_data",
                "cache_info": "Articles cached for 5 minutes when using live mode"
            },
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error fetching news: {str(e)}")
        handle_database_error(e)

# Keep the old function name for backward compatibility
get_news = get_news_internal