"""
Firestore utility functions for news article storage and retrieval.
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from google.cloud import firestore
from google.cloud.firestore import Client
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists (in case environment.py hasn't been imported yet)
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)  # Don't override existing env vars

logger = logging.getLogger(__name__)

# Global Firestore client
_firestore_client: Optional[Client] = None


def get_firestore_client() -> Optional[Client]:
    """
    Get or create Firestore client.
    Returns None if Firestore is not configured.
    """
    global _firestore_client
    
    if _firestore_client is not None:
        return _firestore_client
    
    try:
        # Reload .env file to ensure latest values (in case it was just created)
        if env_path.exists():
            load_dotenv(env_path, override=False)
        
        project_id = os.getenv("FIRESTORE_PROJECT_ID")
        credentials_path = os.getenv("FIRESTORE_CREDENTIALS_PATH")
        
        # Debug logging to help diagnose
        logger.debug(f"Firestore config check - Project ID: {project_id or 'NOT SET'}, Credentials Path: {credentials_path or 'NOT SET'}")
        logger.debug(f"  .env file exists: {env_path.exists()}")
        logger.debug(f"  .env file path: {env_path}")
        logger.debug(f"  Current working directory: {os.getcwd()}")
        
        if not project_id:
            logger.warning("FIRESTORE_PROJECT_ID not set, Firestore disabled")
            logger.warning("  To enable: Set FIRESTORE_PROJECT_ID environment variable or create .env file")
            logger.warning(f"  Expected .env file location: {env_path}")
            if env_path.exists():
                logger.warning("  .env file exists but FIRESTORE_PROJECT_ID is not set in it")
                logger.warning("  Check .env file format: FIRESTORE_PROJECT_ID=inf1005-452110")
            else:
                logger.warning("  .env file not found at expected location")
            return None
        
        # Check credentials file if path is provided
        if credentials_path:
            if not os.path.exists(credentials_path):
                logger.error(f"Firestore credentials file not found: {credentials_path}")
                logger.error(f"  Current working directory: {os.getcwd()}")
                logger.error(f"  Absolute path would be: {os.path.abspath(credentials_path)}")
                logger.error("  Please check FIRESTORE_CREDENTIALS_PATH in .env file or environment variables")
                return None
            elif not os.access(credentials_path, os.R_OK):
                logger.error(f"Firestore credentials file not readable: {credentials_path}")
                logger.error("  Please check file permissions")
                return None
            else:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
                logger.debug(f"Using Firestore credentials from: {os.path.abspath(credentials_path)}")
        
        _firestore_client = firestore.Client(project=project_id)
        logger.info(f"Firestore client initialized for project: {project_id}")
        return _firestore_client
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error initializing Firestore client: {error_msg}")
        
        # Provide more specific error guidance
        if "403" in error_msg or "Permission denied" in error_msg:
            logger.error("  → This is a permissions issue. Possible causes:")
            logger.error("     1. Service account lacks 'Cloud Firestore User' role")
            logger.error("     2. Firestore API not enabled for project")
            logger.error("     3. Service account key is invalid or expired")
        elif "404" in error_msg or "not found" in error_msg.lower():
            logger.error("  → Project not found. Check FIRESTORE_PROJECT_ID matches Google Cloud project ID")
        elif "401" in error_msg or "authentication" in error_msg.lower():
            logger.error("  → Authentication failed. Check credentials file is valid JSON")
        else:
            logger.error(f"  → Error type: {type(e).__name__}")
            logger.error("  → See FIRESTORE_TROUBLESHOOTING.md for detailed solutions")
        
        return None


def get_firestore_collection(collection_name: str):
    """
    Get a Firestore collection reference.
    Returns None if Firestore is not configured.
    """
    try:
        client = get_firestore_client()
        if client is None:
            return None
        return client.collection(collection_name)
    except Exception as e:
        logger.error(f"Error getting Firestore collection: {e}")
        return None


async def test_firestore_connection() -> bool:
    """
    Test Firestore connection (Task 60: Health Dashboard).
    Returns True if connection is successful, False otherwise.
    """
    try:
        client = get_firestore_client()
        if client is None:
            return False
        
        # Try to access a collection to test connection
        # Use a simple query that should work even if collection is empty
        collection_ref = client.collection("financial_news")
        # Just check if we can access the collection
        list(collection_ref.limit(1).stream())
        return True
        
    except Exception as e:
        logger.error(f"Firestore connection test failed: {e}")
        return False


async def get_articles_from_firestore(
    ticker: Optional[str] = "",
    days: int = 7,
    sentiment_filter: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get articles from Firestore with optional filters.
    Excludes soft-deleted articles (deleted_at is None).
    """
    try:
        client = get_firestore_client()
        if client is None:
            logger.warning("Firestore client not available")
            return []
        
        collection_ref = client.collection("financial_news")
        query = collection_ref.where("deleted_at", "==", None)
        
        # Filter by ticker if provided
        if ticker:
            query = query.where("ticker", "==", ticker.upper())
        
        # Filter by date (last N days)
        if days > 0:
            cutoff_date = datetime.now() - timedelta(days=days)
            query = query.where("published_date", ">=", cutoff_date.isoformat())
        
        # Filter by sentiment if provided
        if sentiment_filter:
            query = query.where("sentiment_analysis.overall_sentiment", "==", sentiment_filter.lower())
        
        # Order by published date (newest first) and limit
        query = query.order_by("published_date", direction=firestore.Query.DESCENDING).limit(limit)
        
        articles = []
        for doc in query.stream():
            article_data = doc.to_dict()
            article_data["article_id"] = doc.id
            articles.append(article_data)
        
        return articles
        
    except Exception as e:
        logger.error(f"Error getting articles from Firestore: {e}")
        return []


async def get_article_from_firestore(article_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a single article from Firestore by ID.
    Returns None if article doesn't exist or is soft-deleted.
    """
    try:
        client = get_firestore_client()
        if client is None:
            logger.warning("Firestore client not available")
            return None
        
        doc_ref = client.collection("financial_news").document(article_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
        
        article_data = doc.to_dict()
        
        # Check if article is soft-deleted
        if article_data.get("deleted_at") is not None:
            return None
        
        article_data["article_id"] = doc.id
        return article_data
        
    except Exception as e:
        logger.error(f"Error getting article from Firestore: {e}")
        return None


async def store_article_in_firestore(article_data: Dict[str, Any]) -> bool:
    """
    Store a new article in Firestore.
    Returns True if successful, False otherwise.
    """
    try:
        client = get_firestore_client()
        if client is None:
            logger.warning("Firestore client not available")
            return False
        
        # Remove article_id from data if present (it will be the document ID)
        article_id = article_data.pop("article_id", None)
        
        # Add timestamps
        article_data["created_at"] = datetime.now().isoformat()
        article_data["updated_at"] = datetime.now().isoformat()
        article_data["deleted_at"] = None
        
        collection_ref = client.collection("financial_news")
        
        if article_id:
            # Use provided article_id as document ID
            doc_ref = collection_ref.document(article_id)
            doc_ref.set(article_data)
        else:
            # Generate new document ID
            _, doc_ref = collection_ref.add(article_data)
            article_id = doc_ref.id
        
        logger.info(f"Stored article {article_id} in Firestore")
        return True
        
    except Exception as e:
        logger.error(f"Error storing article in Firestore: {e}")
        return False


async def update_article_in_firestore(article_id: str, article_data: Dict[str, Any]) -> bool:
    """
    Full update (PUT) of an article in Firestore.
    Replaces all fields of the article.
    Returns True if successful, False otherwise.
    """
    try:
        client = get_firestore_client()
        if client is None:
            logger.warning("Firestore client not available")
            return False
        
        # Remove article_id from data
        article_data.pop("article_id", None)
        
        # Update timestamp
        article_data["updated_at"] = datetime.now().isoformat()
        # Preserve created_at and deleted_at if they exist
        doc_ref = client.collection("financial_news").document(article_id)
        existing_doc = doc_ref.get()
        
        if existing_doc.exists:
            existing_data = existing_doc.to_dict()
            article_data["created_at"] = existing_data.get("created_at", datetime.now().isoformat())
            article_data["deleted_at"] = existing_data.get("deleted_at", None)
        else:
            article_data["created_at"] = datetime.now().isoformat()
            article_data["deleted_at"] = None
        
        doc_ref.set(article_data)
        logger.info(f"Updated article {article_id} in Firestore")
        return True
        
    except Exception as e:
        logger.error(f"Error updating article in Firestore: {e}")
        return False


async def patch_article_in_firestore(article_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Partial update (PATCH) of an article in Firestore.
    Only updates the provided fields.
    Returns True if successful, False otherwise.
    """
    try:
        client = get_firestore_client()
        if client is None:
            logger.warning("Firestore client not available")
            return False
        
        # Remove article_id from data
        update_data.pop("article_id", None)
        
        # Update timestamp
        update_data["updated_at"] = datetime.now().isoformat()
        
        doc_ref = client.collection("financial_news").document(article_id)
        doc_ref.update(update_data)
        
        logger.info(f"Patched article {article_id} in Firestore")
        return True
        
    except Exception as e:
        logger.error(f"Error patching article in Firestore: {e}")
        return False


async def soft_delete_article_in_firestore(article_id: str) -> bool:
    """
    Soft delete an article in Firestore by setting deleted_at timestamp.
    Returns True if successful, False otherwise.
    """
    try:
        client = get_firestore_client()
        if client is None:
            logger.warning("Firestore client not available")
            return False
        
        doc_ref = client.collection("financial_news").document(article_id)
        doc_ref.update({
            "deleted_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
        
        logger.info(f"Soft deleted article {article_id} in Firestore")
        return True
        
    except Exception as e:
        logger.error(f"Error soft deleting article in Firestore: {e}")
        return False


async def get_sentiment_stats_from_firestore(
    ticker: Optional[str] = "",
    days: int = 7
) -> Dict[str, Any]:
    """
    Get sentiment statistics from Firestore for a given ticker and time period.
    Returns aggregated sentiment statistics.
    """
    try:
        client = get_firestore_client()
        if client is None:
            logger.warning("Firestore client not available")
            return {}
        
        # Get articles for the ticker and time period
        articles = await get_articles_from_firestore(ticker=ticker, days=days, limit=1000)
        
        if not articles:
            return {
                "total_articles": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "average_sentiment": 0.0
            }
        
        # Aggregate sentiment statistics
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        sentiment_scores = []
        
        for article in articles:
            sentiment_analysis = article.get("sentiment_analysis", {})
            overall_sentiment = sentiment_analysis.get("overall_sentiment", "neutral")
            overall_score = sentiment_analysis.get("overall_score", 0.0)
            
            if overall_sentiment == "positive":
                positive_count += 1
            elif overall_sentiment == "negative":
                negative_count += 1
            else:
                neutral_count += 1
            
            sentiment_scores.append(overall_score)
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        
        return {
            "total_articles": len(articles),
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
            "average_sentiment": avg_sentiment
        }
        
    except Exception as e:
        logger.error(f"Error getting sentiment stats from Firestore: {e}")
        return {}


async def get_sentiment_trends_from_firestore(
    ticker: Optional[str] = "",
    days: int = 7
) -> List[Dict[str, Any]]:
    """
    Get sentiment trends from Firestore for a given ticker and time period.
    Returns daily sentiment trends.
    """
    try:
        client = get_firestore_client()
        if client is None:
            logger.warning("Firestore client not available")
            return []
        
        # Get articles for the ticker and time period
        articles = await get_articles_from_firestore(ticker=ticker, days=days, limit=1000)
        
        if not articles:
            return []
        
        # Group articles by date
        trends_by_date = {}
        
        for article in articles:
            published_date = article.get("published_date")
            if not published_date:
                continue
            
            # Extract date (YYYY-MM-DD) from ISO format
            date_str = published_date.split("T")[0] if "T" in published_date else published_date[:10]
            
            if date_str not in trends_by_date:
                trends_by_date[date_str] = {
                    "date": date_str,
                    "positive": 0,
                    "negative": 0,
                    "neutral": 0,
                    "total": 0,
                    "average_sentiment": 0.0
                }
            
            sentiment_analysis = article.get("sentiment_analysis", {})
            overall_sentiment = sentiment_analysis.get("overall_sentiment", "neutral")
            overall_score = sentiment_analysis.get("overall_score", 0.0)
            
            trends_by_date[date_str]["total"] += 1
            trends_by_date[date_str]["average_sentiment"] += overall_score
            
            if overall_sentiment == "positive":
                trends_by_date[date_str]["positive"] += 1
            elif overall_sentiment == "negative":
                trends_by_date[date_str]["negative"] += 1
            else:
                trends_by_date[date_str]["neutral"] += 1
        
        # Calculate average sentiment per day
        trends = []
        for date_str, trend_data in trends_by_date.items():
            if trend_data["total"] > 0:
                trend_data["average_sentiment"] = trend_data["average_sentiment"] / trend_data["total"]
            trends.append(trend_data)
        
        # Sort by date
        trends.sort(key=lambda x: x["date"])
        
        return trends
        
    except Exception as e:
        logger.error(f"Error getting sentiment trends from Firestore: {e}")
        return []


async def store_sentiment_trend_in_firestore(trend_data: Dict[str, Any]) -> bool:
    """
    Store sentiment trend data in Firestore.
    Returns True if successful, False otherwise.
    """
    try:
        client = get_firestore_client()
        if client is None:
            logger.warning("Firestore client not available")
            return False
        
        collection_ref = client.collection("sentiment_trends")
        
        # Use date and ticker as document ID if available
        date_str = trend_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        ticker = trend_data.get("ticker", "")
        
        if ticker:
            doc_id = f"{ticker}_{date_str}"
        else:
            doc_id = f"all_{date_str}"
        
        trend_data["updated_at"] = datetime.now().isoformat()
        
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(trend_data, merge=True)
        
        logger.info(f"Stored sentiment trend {doc_id} in Firestore")
        return True
        
    except Exception as e:
        logger.error(f"Error storing sentiment trend in Firestore: {e}")
        return False