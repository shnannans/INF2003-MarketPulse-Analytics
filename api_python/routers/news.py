from fastapi import APIRouter, Depends, Query
from typing import Optional
import logging
from datetime import datetime, timedelta

from config.firestore import get_articles_from_firestore, store_article_in_firestore
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
    live: Optional[bool] = Query(True, description="Use live NewsAPI (True) or Firestore (False)")
):
    """
    Get news articles with real-time sentiment analysis (REST-style endpoint).
    Supports both live NewsAPI integration and Firestore fallback.
    """
    return await get_news_internal(ticker, days, sentiment, limit, live)

async def get_news_internal(
    ticker: Optional[str] = Query("", description="Stock ticker to filter by"),
    days: Optional[int] = Query(7, ge=1, le=30, description="Number of days to look back"),
    sentiment: Optional[str] = Query("", regex="^(positive|negative|neutral|)$", description="Sentiment filter"),
    limit: Optional[int] = Query(20, ge=1, le=100, description="Maximum number of articles"),
    live: Optional[bool] = Query(True, description="Use live NewsAPI (True) or Firestore (False)")
):
    """
    Get news articles with real-time sentiment analysis.
    Supports both live NewsAPI integration and Firestore fallback.
    """
    try:
        articles = []

        # Always try Firestore first (fallback mechanism)
        logger.info(f"Fetching news from Firestore for ticker: {ticker}, days: {days}, sentiment: {sentiment}")
        articles = await get_articles_from_firestore(ticker=ticker, days=days, sentiment_filter=sentiment, limit=limit)
        logger.info(f"Firestore returned {len(articles)} articles for ticker '{ticker}'")
        
        # If no articles found for specific ticker, try general financial news
        if not articles and ticker and ticker.strip():
            logger.info(f"No articles found for ticker '{ticker}', trying general financial news")
            articles = await get_articles_from_firestore(ticker="", days=days, sentiment_filter=sentiment, limit=limit)
            logger.info(f"Firestore returned {len(articles)} general articles")

        # If no articles from Firestore and live mode requested, try NewsAPI as fallback
        if not articles and live:
            try:
                # Use live NewsAPI service with real-time sentiment analysis
                logger.info(f"Firestore empty, fetching live news for ticker: {ticker}, days: {days}, sentiment: {sentiment}")
                articles = await get_financial_news(ticker=ticker, days=days, sentiment_filter=sentiment)

                # Apply limit
                if len(articles) > limit:
                    articles = articles[:limit]

                # Store new articles in Firestore for future use
                if articles:
                    for article in articles:
                        await store_article_in_firestore(article)

                logger.info(f"Live news service returned {len(articles)} articles")
            except Exception as e:
                logger.warning(f"NewsAPI failed (possibly rate limited): {e}")
                logger.info("Falling back to Firestore only")
                # Try to get any available articles from Firestore without ticker filter
                if not articles:
                    articles = await get_articles_from_firestore(ticker="", days=days, sentiment_filter=sentiment, limit=limit)
                    logger.info(f"Firestore fallback returned {len(articles)} articles")


        # Determine the message based on what we have
        message = ""
        if not articles:
            if ticker:
                message = f"No news available for {ticker.upper()}"
            else:
                message = "No news articles available"
        else:
            if ticker and ticker.strip():
                # Check if we got ticker-specific articles or general articles
                ticker_articles = [a for a in articles if a.get('ticker', '').upper() == ticker.upper()]
                if ticker_articles:
                    message = f"Found {len(articles)} articles for {ticker.upper()}"
                else:
                    # Check if articles contain the ticker/company name in content
                    ticker_upper = ticker.upper()
                    company_names = {
                        'AAPL': ['APPLE', 'APPLE INC'],
                        'MSFT': ['MICROSOFT'],
                        'GOOGL': ['GOOGLE', 'ALPHABET'],
                        'AMZN': ['AMAZON'],
                        'TSLA': ['TESLA'],
                        'META': ['FACEBOOK', 'META'],
                        'NVDA': ['NVIDIA'],
                        'NFLX': ['NETFLIX'],
                        'AMD': ['ADVANCED MICRO DEVICES'],
                        'INTC': ['INTEL']
                    }
                    
                    search_terms = [ticker_upper]
                    if ticker_upper in company_names:
                        search_terms.extend(company_names[ticker_upper])
                    
                    content_matches = 0
                    for article in articles:
                        title = article.get('title', '').upper()
                        content = article.get('content', '').upper()
                        for term in search_terms:
                            if term in title or term in content:
                                content_matches += 1
                                break
                    
                    if content_matches > 0:
                        message = f"Found {len(articles)} articles mentioning {ticker.upper()}"
                    else:
                        message = f"Found {len(articles)} general financial articles (no specific news for {ticker.upper()})"
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
                "data_source": "firestore_fallback" if articles and not live else "newsapi_live" if live and articles else "firestore_only" if articles else "no_data",
                "cache_info": "Articles from Firestore cache" if not live else "Articles from NewsAPI + cached in Firestore" if live and articles else "No articles available"
            },
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error fetching news: {str(e)}")
        handle_database_error(e)

# Keep the old function name for backward compatibility
get_news = get_news_internal