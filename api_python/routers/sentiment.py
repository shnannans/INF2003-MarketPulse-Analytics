from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import Optional
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re

from config.database import get_mongo_collection
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
    live: Optional[bool] = Query(True, description="Use live NewsAPI (True) or fallback to MongoDB (False)"),
    collection: AsyncIOMotorCollection = Depends(get_mongo_collection)
):
    """
    Get sentiment analysis statistics and trends from live news data (REST-style endpoint).
    Supports both live NewsAPI integration and MongoDB fallback.
    """
    return await get_sentiment_internal(ticker, days, live, collection)

async def get_sentiment_internal(
    ticker: Optional[str] = Query("", description="Stock ticker to filter by"),
    days: Optional[int] = Query(7, ge=1, le=30, description="Number of days to analyze"),
    live: Optional[bool] = Query(True, description="Use live NewsAPI (True) or fallback to MongoDB (False)"),
    collection: AsyncIOMotorCollection = Depends(get_mongo_collection)
):
    """
    Get sentiment analysis statistics and trends from live news data.
    Supports both live NewsAPI integration and MongoDB fallback.
    """
    try:
        stats = {}
        trends = []
        topics = []

        if live:
            # Use live NewsAPI service for sentiment analysis
            logger.info(f"Fetching live sentiment data for ticker: {ticker}, days: {days}")
            articles = await get_financial_news(ticker=ticker, days=days)

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

        # Extract topics from live articles
        topics = []
        if articles:
            topics = extract_topics_from_articles(articles, max_topics=10)
            logger.info(f"Extracted {len(topics)} topics from {len(articles)} articles")

        # Fallback to MongoDB if live fails or returns no results
        if not stats and collection is not None:
            logger.info("Falling back to MongoDB for sentiment analysis")

            # Build match filter
            cutoff_timestamp = datetime.now() - timedelta(days=days)
            match_filter = {
                'published_date': {'$gte': cutoff_timestamp}
            }

            if ticker:
                match_filter['ticker'] = ticker.upper()

            # Aggregate statistics
            stats_pipeline = [
                {'$match': match_filter},
                {
                    '$group': {
                        '_id': None,
                        'total_articles': {'$sum': 1},
                        'avg_sentiment': {'$avg': '$sentiment_analysis.overall_score'},
                        'positive_count': {
                            '$sum': {
                                '$cond': [
                                    {'$gt': ['$sentiment_analysis.overall_score', 0.1]},
                                    1,
                                    0
                                ]
                            }
                        },
                        'negative_count': {
                            '$sum': {
                                '$cond': [
                                    {'$lt': ['$sentiment_analysis.overall_score', -0.1]},
                                    1,
                                    0
                                ]
                            }
                        },
                        'neutral_count': {
                            '$sum': {
                                '$cond': [
                                    {
                                        '$and': [
                                            {'$gte': ['$sentiment_analysis.overall_score', -0.1]},
                                            {'$lte': ['$sentiment_analysis.overall_score', 0.1]}
                                        ]
                                    },
                                    1,
                                    0
                                ]
                            }
                        }
                    }
                }
            ]

            stats_cursor = collection.aggregate(stats_pipeline)
            stats_result = await stats_cursor.to_list(length=1)

            # Default stats if no data
            stats = stats_result[0] if stats_result else {
                'total_articles': 0,
                'avg_sentiment': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0
            }

            # Remove MongoDB _id
            stats.pop('_id', None)

            # Daily trend analysis
            trends_pipeline = [
                {'$match': match_filter},
                {
                    '$group': {
                        '_id': {
                            'date': {
                                '$dateToString': {
                                    'format': "%Y-%m-%d",
                                    'date': '$published_date'
                                }
                            }
                        },
                        'avg_sentiment': {'$avg': '$sentiment_analysis.overall_score'},
                        'article_count': {'$sum': 1}
                    }
                },
                {'$sort': {'_id.date': 1}}
            ]

            trends_cursor = collection.aggregate(trends_pipeline)
            trends_raw = await trends_cursor.to_list(length=None)

            # Format trends for consistency
            trends = trends_raw

            # Extract topics from MongoDB articles if we have some
            if not topics and collection is not None:
                try:
                    # Get recent articles for topic extraction
                    recent_articles = await collection.find(
                        match_filter,
                        {'title': 1, 'content': 1, '_id': 0}
                    ).limit(50).to_list(length=50)

                    if recent_articles:
                        topics = extract_topics_from_articles(recent_articles, max_topics=10)
                        logger.info(f"Extracted {len(topics)} topics from {len(recent_articles)} MongoDB articles")
                except Exception as e:
                    logger.error(f"Error extracting topics from MongoDB: {e}")
                    topics = []

        # Default stats if still empty
        if not stats:
            stats = {
                'total_articles': 0,
                'avg_sentiment': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0
            }

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
                "data_source": "newsapi_live" if live and stats.get('total_articles', 0) > 0 else "mongodb_fallback" if stats.get('total_articles', 0) > 0 else "no_data",
                "analysis_method": "textblob_vader_combined" if live else "pre_calculated",
                "topics_extracted": len(topics)
            },
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error fetching sentiment data: {str(e)}")
        handle_database_error(e)

# Keep the old function name for backward compatibility
get_sentiment = get_sentiment_internal