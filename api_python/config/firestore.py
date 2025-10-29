"""
Firestore database configuration and utilities
"""
import os
import logging
from typing import Optional
from google.cloud import firestore
from google.cloud.firestore import CollectionReference, DocumentReference
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Initialize Firestore client
db = None

def get_firestore_client():
    """Get Firestore client instance"""
    global db
    if db is None:
        try:
            # Set the service account key path
            service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'service_key.json')
            if os.path.exists(service_account_path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_path
            
            # Use databaseproj database instead of default
            db = firestore.Client(database='databaseproj')
            logger.info("Firestore client initialized successfully with database: databaseproj")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            db = None
    return db

def get_firestore_collection(collection_name: str) -> Optional[CollectionReference]:
    """Get Firestore collection"""
    client = get_firestore_client()
    if client:
        return client.collection(collection_name)
    return None

async def store_article_in_firestore(article_data: dict) -> bool:
    """Store a news article in Firestore"""
    try:
        collection = get_firestore_collection('financial_news')
        if not collection:
            logger.error("Firestore collection not available")
            return False
        
        # Add timestamp if not present
        if 'metadata' not in article_data:
            article_data['metadata'] = {}
        
        article_data['metadata']['stored_at'] = datetime.now().isoformat()
        
        # Use article_id as document ID if available
        doc_id = article_data.get('article_id', f"article_{hash(article_data.get('url', ''))}")
        collection.document(doc_id).set(article_data)
        
        logger.info(f"Stored article {doc_id} in Firestore")
        return True
    except Exception as e:
        logger.error(f"Error storing article in Firestore: {e}")
        return False

async def store_sentiment_trend_in_firestore(trend_data: dict) -> bool:
    """Store sentiment trend data in Firestore"""
    try:
        collection = get_firestore_collection('sentiment_trends')
        if not collection:
            logger.error("Firestore sentiment collection not available")
            return False
        
        # Add timestamp
        trend_data['created_at'] = datetime.now().isoformat()
        
        # Use ticker_date as document ID
        doc_id = f"{trend_data.get('ticker', 'unknown')}_{trend_data.get('date', 'unknown')}"
        collection.document(doc_id).set(trend_data)
        
        logger.info(f"Stored sentiment trend {doc_id} in Firestore")
        return True
    except Exception as e:
        logger.error(f"Error storing sentiment trend in Firestore: {e}")
        return False

async def get_articles_from_firestore(ticker: str = "", days: int = 7, sentiment_filter: str = "", limit: int = 20) -> list:
    """Get articles from Firestore with filters"""
    try:
        collection = get_firestore_collection('financial_news')
        if not collection:
            logger.warning("Firestore collection not available")
            return []
        
        # Build query
        query = collection
        
        # Don't filter by ticker field here - we'll do content-based filtering later
        
        # Filter by date (last N days) - fixed version
        try:
            from datetime import timezone
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            # Convert to UTC format to match Firestore dates
            cutoff_date_utc = cutoff_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            logger.info(f"Filtering by date >= {cutoff_date_utc}")
            query = query.where('published_date', '>=', cutoff_date_utc)
        except Exception as e:
            logger.warning(f"Date filtering failed: {e}, getting recent documents without date filter")
        
        # Filter by sentiment
        if sentiment_filter == 'positive':
            query = query.where('sentiment_analysis.overall_score', '>', 0.1)
        elif sentiment_filter == 'negative':
            query = query.where('sentiment_analysis.overall_score', '<', -0.1)
        elif sentiment_filter == 'neutral':
            query = query.where('sentiment_analysis.overall_score', '>=', -0.1).where('sentiment_analysis.overall_score', '<=', 0.1)
        
        # Order by published date (newest first) and get more documents for filtering
        # Get more articles to ensure we have a good mix of ticker and non-ticker articles
        query = query.order_by('published_date', direction=firestore.Query.DESCENDING).limit(limit * 20)  # Get more to filter
        
        # Execute query
        docs = query.stream()
        all_articles = []
        for doc in docs:
            article = doc.to_dict()
            article['_id'] = doc.id
            all_articles.append(article)
        
        # Filter by ticker if provided
        if ticker and ticker.strip():
            ticker_upper = ticker.upper()
            filtered_articles = []
            
            # First, try to find articles with exact ticker match
            for article in all_articles:
                article_ticker = article.get('ticker', '').upper()
                if article_ticker == ticker_upper:
                    filtered_articles.append(article)
            
            # If we found ticker-specific articles, use only those
            if filtered_articles:
                articles = filtered_articles[:limit]
            else:
                # No ticker-specific articles found, search in content
                logger.info(f"No articles found with ticker '{ticker_upper}', searching in content...")
                
                # Create a mapping of common tickers to company names
                ticker_to_company = {
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
                
                # Get company names to search for
                search_terms = [ticker_upper]
                if ticker_upper in ticker_to_company:
                    search_terms.extend(ticker_to_company[ticker_upper])
                
                for article in all_articles:
                    # Check if any search term appears in title or content
                    title = article.get('title', '').upper()
                    content = article.get('content', '').upper()
                    
                    for term in search_terms:
                        if term in title or term in content:
                            filtered_articles.append(article)
                            break
                
                # Limit the filtered results
                articles = filtered_articles[:limit]
        else:
            # No ticker filter, prioritize articles with tickers for better variety
            articles_with_tickers = [a for a in all_articles if a.get('ticker', '').strip()]
            articles_without_tickers = [a for a in all_articles if not a.get('ticker', '').strip()]
            
            # Mix articles: 70% with tickers, 30% without tickers
            ticker_limit = int(limit * 0.7)
            no_ticker_limit = limit - ticker_limit
            
            mixed_articles = articles_with_tickers[:ticker_limit] + articles_without_tickers[:no_ticker_limit]
            articles = mixed_articles[:limit]
        
        logger.info(f"Retrieved {len(articles)} articles from Firestore (filtered from {len(all_articles)} total)")
        return articles
    except Exception as e:
        logger.error(f"Error getting articles from Firestore: {e}")
        return []

async def get_sentiment_trends_from_firestore(ticker: str = "", days: int = 7) -> list:
    """Get sentiment trends from Firestore"""
    try:
        collection = get_firestore_collection('sentiment_trends')
        if not collection:
            logger.warning("Firestore sentiment collection not available")
            return []
        
        # Build query
        query = collection
        
        # Filter by date
        from datetime import timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.where('date', '>=', cutoff_date.strftime('%Y-%m-%d'))
        
        # Order by date (newest first) and get more documents for filtering
        query = query.order_by('date', direction=firestore.Query.DESCENDING).limit(days * 10)
        
        # Execute query
        docs = query.stream()
        all_trends = []
        for doc in docs:
            trend = doc.to_dict()
            trend['_id'] = {'date': trend.get('date', '')}
            all_trends.append(trend)
        
        # Filter by ticker if provided
        if ticker and ticker.strip():
            ticker_upper = ticker.upper()
            filtered_trends = []
            
            # First, try to find trends with exact ticker match
            for trend in all_trends:
                if trend.get('ticker', '').upper() == ticker_upper:
                    filtered_trends.append(trend)
            
            # If we found ticker-specific trends, use only those
            if filtered_trends:
                trends = filtered_trends[:days]
            else:
                # No ticker-specific trends found, return general trends
                logger.info(f"No sentiment trends found with ticker '{ticker_upper}', returning general trends")
                trends = all_trends[:days]
        else:
            # No ticker filter, return all trends
            trends = all_trends[:days]
        
        logger.info(f"Retrieved {len(trends)} sentiment trends from Firestore")
        return trends
    except Exception as e:
        logger.error(f"Error getting sentiment trends from Firestore: {e}")
        return []

async def get_sentiment_stats_from_firestore(ticker: str = "", days: int = 7) -> dict:
    """Get sentiment statistics from Firestore"""
    try:
        collection = get_firestore_collection('sentiment_trends')
        if not collection:
            logger.warning("Firestore sentiment collection not available")
            return {}
        
        # Build query
        query = collection
        
        # Filter by date
        from datetime import timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.where('date', '>=', cutoff_date.strftime('%Y-%m-%d'))
        
        # Execute query
        docs = query.stream()
        
        all_trends = []
        for doc in docs:
            all_trends.append(doc.to_dict())
        
        # Filter by ticker if provided
        if ticker and ticker.strip():
            ticker_upper = ticker.upper()
            filtered_trends = []
            
            # First, try to find trends with exact ticker match
            for trend in all_trends:
                if trend.get('ticker', '').upper() == ticker_upper:
                    filtered_trends.append(trend)
            
            # If we found ticker-specific trends, use only those
            if filtered_trends:
                trends_to_use = filtered_trends
            else:
                # No ticker-specific trends found, use general trends
                logger.info(f"No sentiment trends found with ticker '{ticker_upper}', using general trends")
                trends_to_use = all_trends
        else:
            # No ticker filter, use all trends
            trends_to_use = all_trends
        
        total_articles = 0
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        sentiment_scores = []
        
        for trend in trends_to_use:
            total_articles += trend.get('article_count', 0)
            positive_count += trend.get('positive_count', 0)
            negative_count += trend.get('negative_count', 0)
            neutral_count += trend.get('neutral_count', 0)
            sentiment_scores.append(trend.get('avg_sentiment', 0))
        
        # Calculate average sentiment
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        
        stats = {
            'total_articles': total_articles,
            'avg_sentiment': round(avg_sentiment, 4),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count
        }
        
        logger.info(f"Retrieved sentiment stats from Firestore: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Error getting sentiment stats from Firestore: {e}")
        return {}
