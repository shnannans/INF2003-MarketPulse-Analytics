from fastapi import APIRouter, Depends, Query
from typing import Optional
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

from config.firestore import get_sentiment_trends_from_firestore, get_sentiment_stats_from_firestore, store_sentiment_trend_in_firestore
from models.pydantic_models import SentimentQuery, SentimentResponse
from utils.error_handlers import handle_database_error
from utils.news_service import get_financial_news

router = APIRouter()
logger = logging.getLogger(__name__)

def extract_topics_from_articles(articles, max_topics=10):
    """Extract common topics/keywords from article titles and content"""
    # Common financial and business terms to look for
    financial_keywords = {
        'earnings', 'revenue', 'profit', 'loss', 'growth', 'sales', 'market', 'stock',
        'shares', 'dividend', 'investment', 'financial', 'quarterly', 'annual',
        'acquisition', 'merger', 'partnership', 'launch', 'product', 'service',
        'technology', 'AI', 'artificial intelligence', 'cloud', 'software', 'hardware',
        'automotive', 'electric vehicle', 'EV', 'semiconductor', 'chip', 'processor',
        'smartphone', 'iPhone', 'android', 'streaming', 'subscription', 'gaming',
        'e-commerce', 'retail', 'online', 'digital', 'cybersecurity', 'data',
        'energy', 'renewable', 'solar', 'battery', 'healthcare', 'pharmaceutical',
        'biotech', 'FDA', 'clinical', 'drug', 'vaccine', 'pandemic', 'COVID'
    }

    # Stopwords to exclude
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
    }

    word_counts = Counter()

    for article in articles:
        # Combine title and content for keyword extraction
        text = ""
        if article.get('title'):
            text += article['title'] + " "
        if article.get('content'):
            text += article['content']

        # Convert to lowercase and extract words
        text = text.lower()
        # Remove punctuation and split into words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)

        # Count relevant keywords
        for word in words:
            if (word in financial_keywords or
                len(word) >= 4 and word not in stopwords):
                # Skip very common words
                if word not in {'said', 'says', 'news', 'today', 'year', 'time',
                              'company', 'business', 'report', 'reports', 'new'}:
                    word_counts[word] += 1

    # Return top topics with counts
    topics = []
    for word, count in word_counts.most_common(max_topics):
        topics.append({
            'word': word.title(),
            'count': count
        })

    return topics


@router.get("/sentiment", response_model=dict)
async def get_sentiment_rest_style(
    ticker: Optional[str] = Query("", description="Stock ticker to filter by"),
    days: Optional[int] = Query(7, ge=1, le=30, description="Number of days to analyze"),
    live: Optional[bool] = Query(True, description="Use live NewsAPI (True) or Firestore (False)")
):
    """
    Get sentiment analysis statistics and trends from live news data (REST-style endpoint).
    Supports both live NewsAPI integration and Firestore fallback.
    """
    return await get_sentiment_internal(ticker, days, live)

async def get_sentiment_internal(
    ticker: Optional[str] = Query("", description="Stock ticker to filter by"),
    days: Optional[int] = Query(7, ge=1, le=30, description="Number of days to analyze"),
    live: Optional[bool] = Query(True, description="Use live NewsAPI (True) or Firestore (False)")
):
    """
    Get sentiment analysis statistics and trends from live news data.
    Supports both live NewsAPI integration and Firestore fallback.
    """
    try:
        stats = {}
        trends = []
        topics = []
        articles = []  # Initialize articles variable

        # Always try Firestore first (fallback mechanism)
        logger.info(f"Fetching sentiment data from Firestore for ticker: {ticker}, days: {days}")
        stats = await get_sentiment_stats_from_firestore(ticker=ticker, days=days)
        trends = await get_sentiment_trends_from_firestore(ticker=ticker, days=days)
        logger.info(f"Firestore returned stats: {stats}, trends: {len(trends)}")
        
        # Also fetch articles for topic extraction
        if stats and stats.get('total_articles', 0) > 0:
            logger.info("Fetching articles from Firestore for topic extraction")
            from config.firestore import get_articles_from_firestore
            articles = await get_articles_from_firestore(ticker=ticker, days=days, limit=50)
            logger.info(f"Fetched {len(articles)} articles for topic extraction")
            
            # If no articles found for specific ticker, try general articles
            if not articles and ticker and ticker.strip():
                logger.info(f"No articles found for ticker '{ticker}', fetching general articles for topic extraction")
                articles = await get_articles_from_firestore(ticker="", days=days, limit=50)
                logger.info(f"Fetched {len(articles)} general articles for topic extraction")

        # If no data from Firestore and live mode requested, try NewsAPI as fallback
        if (not stats or not trends) and live:
            try:
                logger.info(f"Firestore empty, trying NewsAPI for ticker: {ticker}, days: {days}")
                articles = await get_financial_news(ticker=ticker, days=days)
            except Exception as e:
                logger.warning(f"NewsAPI failed (possibly rate limited): {e}")
                logger.info("Falling back to Firestore only")
                # Try to get any available data from Firestore without ticker filter
                if not stats:
                    stats = await get_sentiment_stats_from_firestore(ticker="", days=days)
                if not trends:
                    trends = await get_sentiment_trends_from_firestore(ticker="", days=days)
                if not articles:
                    articles = await get_articles_from_firestore(ticker="", days=days, limit=50)
                logger.info(f"Firestore fallback returned stats: {stats}, trends: {len(trends)}")

            if articles:
                # Calculate statistics from live articles
                total_articles = len(articles)
                sentiment_scores = []
                positive_count = 0
                negative_count = 0
                neutral_count = 0

                # Daily trend data
                daily_data = defaultdict(list)

                for article in articles:
                    score = article.get('sentiment_analysis', {}).get('overall_score', 0)
                    sentiment_scores.append(score)

                    # Count sentiment categories
                    if score > 0.1:
                        positive_count += 1
                    elif score < -0.1:
                        negative_count += 1
                    else:
                        neutral_count += 1

                    # Group by date for trends
                    pub_date = article.get('published_date', '')
                    if pub_date:
                        try:
                            date_str = pub_date[:10]  # Extract YYYY-MM-DD
                            daily_data[date_str].append(score)
                        except:
                            pass

                # Calculate overall statistics
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0

                stats = {
                    'total_articles': total_articles,
                    'avg_sentiment': round(avg_sentiment, 4),
                    'positive_count': positive_count,
                    'negative_count': negative_count,
                    'neutral_count': neutral_count
                }

                # Calculate daily trends
                for date_str, scores in sorted(daily_data.items()):
                    daily_avg = sum(scores) / len(scores) if scores else 0.0
                    trends.append({
                        '_id': {'date': date_str},
                        'avg_sentiment': round(daily_avg, 4),
                        'article_count': len(scores)
                    })

                logger.info(f"Live sentiment analysis: {total_articles} articles, avg sentiment: {avg_sentiment:.3f}")

                # Store sentiment trends in Firestore for future use
                for date_str, scores in sorted(daily_data.items()):
                    daily_avg = sum(scores) / len(scores) if scores else 0.0
                    positive_count_daily = sum(1 for score in scores if score > 0.1)
                    negative_count_daily = sum(1 for score in scores if score < -0.1)
                    neutral_count_daily = len(scores) - positive_count_daily - negative_count_daily
                    
                    trend_data = {
                        'ticker': ticker.upper() if ticker else '',
                        'date': date_str,
                        'avg_sentiment': round(daily_avg, 4),
                        'article_count': len(scores),
                        'positive_count': positive_count_daily,
                        'negative_count': negative_count_daily,
                        'neutral_count': neutral_count_daily
                    }
                    await store_sentiment_trend_in_firestore(trend_data)

        # Extract topics from live articles
        topics = []
        if articles:
            topics = extract_topics_from_articles(articles, max_topics=10)
            logger.info(f"Extracted {len(topics)} topics from {len(articles)} articles")

        # Using Firestore only

        # Default stats if still empty
        if not stats:
            stats = {
                'total_articles': 0,
                'avg_sentiment': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0
            }
            logger.info("No sentiment data available from any source")

        return {
            "statistics": stats,
            "trends": trends,
            "topics": topics,  # Add topics to response
            "filters": {
                "ticker": ticker,
                "days": days,
                "live_mode": live
            },
            "metadata": {
                "data_source": "firestore_fallback" if stats.get('total_articles', 0) > 0 and not live else "newsapi_live" if live and stats.get('total_articles', 0) > 0 else "firestore_only" if stats.get('total_articles', 0) > 0 else "no_data",
                "analysis_method": "textblob_vader_combined" if live else "pre_calculated",
                "topics_extracted": len(topics)
            },
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error fetching sentiment data: {str(e)}")
        # Return empty data instead of raising an exception
        return {
            "statistics": {
                'total_articles': 0,
                'avg_sentiment': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0
            },
            "trends": [],
            "topics": [],
            "filters": {
                "ticker": ticker,
                "days": days,
                "live_mode": live
            },
            "metadata": {
                "data_source": "error",
                "analysis_method": "none",
                "topics_extracted": 0
            },
            "status": "error",
            "message": f"Error fetching sentiment data: {str(e)}"
        }

# Keep the old function name for backward compatibility
get_sentiment = get_sentiment_internal