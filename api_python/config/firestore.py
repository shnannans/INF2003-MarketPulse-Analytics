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
            # Resolve path relative to project root (where .env file is), not current working directory
            # This handles cases where server runs from api_python/ but file is in project root
            if not os.path.isabs(credentials_path):
                # If relative path, try project root first, then current directory
                project_root = env_path.parent
                project_root_path = project_root / credentials_path
                cwd_path = Path(credentials_path)
                
                if project_root_path.exists():
                    credentials_path = str(project_root_path.absolute())
                    logger.debug(f"Resolved credentials path to project root: {credentials_path}")
                elif cwd_path.exists():
                    credentials_path = str(cwd_path.absolute())
                    logger.debug(f"Resolved credentials path to current directory: {credentials_path}")
                else:
                    # Try both locations in error message
                    logger.error(f"Firestore credentials file not found: {credentials_path}")
                    logger.error(f"  Searched in project root: {project_root_path.absolute()}")
                    logger.error(f"  Searched in current directory: {cwd_path.absolute()}")
                    logger.error(f"  Current working directory: {os.getcwd()}")
                    logger.error("  Please check FIRESTORE_CREDENTIALS_PATH in .env file")
                    logger.error("  File should be in project root or use absolute path")
                    return None
            else:
                # Absolute path provided
                if not os.path.exists(credentials_path):
                    logger.error(f"Firestore credentials file not found: {credentials_path}")
                    logger.error("  Please check FIRESTORE_CREDENTIALS_PATH in .env file")
                    return None
            
            if not os.access(credentials_path, os.R_OK):
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
        
        logger.debug(f"Firestore query: collection=financial_news, deleted_at==None")
        
        # Filter by ticker if provided
        if ticker and ticker.strip():
            query = query.where("ticker", "==", ticker.upper())
            logger.debug(f"Added ticker filter: {ticker.upper()}")
        
        # Filter by sentiment if provided (do this before date filter to avoid index issues)
        if sentiment_filter and sentiment_filter.strip():
            query = query.where("sentiment_analysis.overall_sentiment", "==", sentiment_filter.lower())
            logger.debug(f"Added sentiment filter: {sentiment_filter.lower()}")
        
        # Firestore requires composite indexes for queries with multiple where clauses + order_by
        # To avoid index requirements, we'll fetch documents and filter/sort in memory
        # This works well for small to medium collections
        
        # Calculate cutoff date if needed (we'll filter in memory)
        cutoff_date = None
        if days > 0 and days < 365:
            cutoff_date = datetime.now() - timedelta(days=days)
            logger.debug(f"Will filter by date in memory: published_date >= {cutoff_date.isoformat()} (last {days} days)")
        else:
            logger.debug(f"Skipping date filter (days={days}, fetching all articles)")
        
        # Fetch more documents than needed to account for date filtering
        # Fetch up to 10x the limit or 1000, whichever is smaller
        fetch_limit = min(limit * 10, 1000)
        query = query.limit(fetch_limit)
        
        articles = []
        doc_count = 0
        
        try:
            for doc in query.stream():
                doc_count += 1
                article_data = doc.to_dict()
                
                # Filter by date in memory if needed
                if cutoff_date:
                    published_date_str = article_data.get("published_date", "")
                    if published_date_str:
                        try:
                            # Parse the published_date
                            if isinstance(published_date_str, str):
                                # Handle ISO format strings (remove timezone for comparison)
                                pub_date_str = published_date_str.replace('Z', '+00:00')
                                pub_date = datetime.fromisoformat(pub_date_str)
                                # Remove timezone for comparison
                                pub_date = pub_date.replace(tzinfo=None)
                                if pub_date < cutoff_date:
                                    continue  # Skip articles older than cutoff
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"Could not parse published_date '{published_date_str}': {e}")
                            # If we can't parse the date, include the article (better to show than hide)
                
                article_data["article_id"] = doc.id
                articles.append(article_data)
            
            # Sort by published_date in memory (newest first)
            articles.sort(key=lambda x: x.get("published_date", ""), reverse=True)
            
            # Apply final limit
            articles = articles[:limit]
            
            logger.info(f"Firestore query returned {len(articles)} articles (fetched {doc_count}, filtered/sorted in memory)")
            return articles
            
        except Exception as query_error:
            error_msg = str(query_error)
            if "index" in error_msg.lower() or "FailedPrecondition" in error_msg:
                logger.warning(f"Firestore index required for query. Using fallback approach.")
                logger.warning(f"  To fix permanently, create the index at: https://console.firebase.google.com/project/inf1005-452110/firestore/indexes")
                
                # Fallback: Simple query without complex filters
                try:
                    simple_query = collection_ref.where("deleted_at", "==", None).limit(1000)
                    if ticker and ticker.strip():
                        simple_query = simple_query.where("ticker", "==", ticker.upper())
                    
                    articles = []
                    for doc in simple_query.stream():
                        article_data = doc.to_dict()
                        article_data["article_id"] = doc.id
                        articles.append(article_data)
                    
                    # Filter by date in memory
                    if cutoff_date:
                        filtered = []
                        for article in articles:
                            pub_date_str = article.get("published_date", "")
                            if pub_date_str:
                                try:
                                    if isinstance(pub_date_str, str):
                                        pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                                        pub_date = pub_date.replace(tzinfo=None)
                                        if pub_date >= cutoff_date:
                                            filtered.append(article)
                                except (ValueError, AttributeError):
                                    filtered.append(article)
                            else:
                                filtered.append(article)
                        articles = filtered
                    
                    # Filter by sentiment in memory
                    if sentiment_filter and sentiment_filter.strip():
                        articles = [a for a in articles if a.get("sentiment_analysis", {}).get("overall_sentiment", "").lower() == sentiment_filter.lower()]
                    
                    # Sort by published_date in memory
                    articles.sort(key=lambda x: x.get("published_date", ""), reverse=True)
                    articles = articles[:limit]
                    
                    logger.info(f"Fallback query returned {len(articles)} articles")
                    return articles
                except Exception as fallback_error:
                    logger.error(f"Fallback query also failed: {fallback_error}")
                    return []
            else:
                # Re-raise if it's not an index error
                raise
        
    except Exception as e:
        logger.error(f"Error getting articles from Firestore: {e}", exc_info=True)
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


async def store_article_in_firestore(article_data: Dict[str, Any]) -> tuple:
    """
    Store a new article in Firestore.
    Returns (success: bool, is_new: bool) where is_new indicates if it was a new article or existing.
    """
    try:
        client = get_firestore_client()
        if client is None:
            logger.warning("Firestore client not available - cannot store article")
            logger.warning(f"  Article title: {article_data.get('title', 'No title')[:50]}")
            return (False, False)
        
        # Make a copy to avoid modifying the original dict
        article_copy = article_data.copy()
        
        # Get article_id from copy (it will be the document ID)
        article_id = article_copy.pop("article_id", None)
        
        # If no article_id, try to generate one from URL
        if not article_id:
            url = article_copy.get("url", "")
            if url:
                # Use hash of URL, but ensure it's positive and valid for Firestore
                url_hash = abs(hash(url))
                article_id = f"newsapi_{url_hash}"
            else:
                # Generate a unique ID based on title and published_date
                title = article_copy.get("title", "")
                pub_date = article_copy.get("published_date", "")
                if title and pub_date:
                    article_id = f"newsapi_{abs(hash(f'{title}_{pub_date}'))}"
                else:
                    # Last resort: use timestamp
                    article_id = f"newsapi_{int(datetime.now().timestamp() * 1000000)}"
        
        # Ensure article_id is a valid Firestore document ID (no special chars, max 1500 chars)
        # Firestore document IDs can contain letters, numbers, and these: -_~!@#$%^&*()
        # But we'll keep it simple: alphanumeric, dash, underscore
        import re
        article_id = re.sub(r'[^a-zA-Z0-9_-]', '_', str(article_id))
        if len(article_id) > 1500:
            article_id = article_id[:1500]
        
        # Add timestamps
        article_copy["created_at"] = datetime.now().isoformat()
        article_copy["updated_at"] = datetime.now().isoformat()
        article_copy["deleted_at"] = None
        
        collection_ref = client.collection("financial_news")
        
        # Check if article already exists (to avoid overwriting with same data)
        doc_ref = collection_ref.document(article_id)
        existing_doc = doc_ref.get()
        
        if existing_doc.exists:
            existing_data = existing_doc.to_dict()
            # If article exists and is not deleted, update timestamp but don't overwrite content
            if existing_data.get("deleted_at") is None:
                # Update the updated_at timestamp to show it was recently accessed
                doc_ref.update({"updated_at": datetime.now().isoformat()})
                logger.debug(f"Article {article_id} already exists in Firestore, updated timestamp: {article_copy.get('title', 'No title')[:50]}")
                return (True, False)  # Success, but not new
        
        # Store the article (new article)
        try:
            doc_ref.set(article_copy)
            
            # Verify the article was actually stored by reading it back
            verify_doc = doc_ref.get()
            if verify_doc.exists:
                logger.info(f"✅ Stored NEW article {article_id} in Firestore (verified)")
                logger.info(f"   Collection: financial_news")
                logger.info(f"   Document ID: {article_id}")
                logger.info(f"   Title: {article_copy.get('title', 'No title')[:60]}")
                logger.info(f"   URL: {article_copy.get('url', 'N/A')[:80]}")
                logger.info(f"   Published: {article_copy.get('published_date', 'N/A')}")
                logger.info(f"   Ticker: {article_copy.get('ticker', 'N/A')}")
                logger.info(f"   Created at: {article_copy.get('created_at', 'N/A')}")
                return (True, True)  # Success and new
            else:
                logger.error(f"❌ Article {article_id} was not stored - document does not exist after set()")
                logger.error(f"   Title: {article_copy.get('title', 'No title')[:60]}")
                return (False, False)
        except Exception as set_error:
            logger.error(f"❌ Failed to set document in Firestore: {set_error}", exc_info=True)
            logger.error(f"   Article ID: {article_id}")
            logger.error(f"   Title: {article_copy.get('title', 'No title')[:60]}")
            logger.error(f"   Collection: financial_news")
            raise
        
    except Exception as e:
        logger.error(f"Error storing article in Firestore: {e}", exc_info=True)
        logger.error(f"  Article data: title={article_data.get('title', 'N/A')[:50]}, url={article_data.get('url', 'N/A')[:50]}")
        return (False, False)


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
        missing_sentiment_count = 0  # Track articles missing overall_sentiment field
        
        for article in articles:
            sentiment_analysis = article.get("sentiment_analysis", {})
            overall_sentiment = sentiment_analysis.get("overall_sentiment")
            overall_score = sentiment_analysis.get("overall_score", 0.0)
            
            # If overall_sentiment is not set, calculate it from overall_score
            # This handles articles stored before we added overall_sentiment field
            if overall_sentiment is None:
                missing_sentiment_count += 1
                if overall_score > 0.1:
                    overall_sentiment = "positive"
                elif overall_score < -0.1:
                    overall_sentiment = "negative"
                else:
                    overall_sentiment = "neutral"
            
            # Count by sentiment category
            if overall_sentiment == "positive":
                positive_count += 1
            elif overall_sentiment == "negative":
                negative_count += 1
            else:
                neutral_count += 1
            
            sentiment_scores.append(overall_score)
        
        # Log if we had to calculate sentiment from scores
        if missing_sentiment_count > 0:
            logger.debug(f"Calculated sentiment from score for {missing_sentiment_count} articles (missing overall_sentiment field)")
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        
        # Return in format expected by frontend: positive_count, negative_count, neutral_count, avg_sentiment
        return {
            "total_articles": len(articles),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "avg_sentiment": avg_sentiment,
            # Also include old field names for backward compatibility
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
                avg_sentiment = trend_data["average_sentiment"] / trend_data["total"]
                # Return in format expected by frontend: {date, avg_sentiment, ...}
                trends.append({
                    "date": date_str,
                    "avg_sentiment": round(avg_sentiment, 4),
                    "article_count": trend_data["total"],
                    "positive_count": trend_data["positive"],
                    "negative_count": trend_data["negative"],
                    "neutral_count": trend_data["neutral"]
                })
        
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