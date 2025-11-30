from fastapi import APIRouter, Depends, Query, HTTPException, status, Body
from typing import Optional, Union, Any, Dict, List
import logging
from datetime import datetime, timedelta
import uuid

from config.firestore import get_articles_from_firestore, store_article_in_firestore, update_article_in_firestore, get_article_from_firestore, patch_article_in_firestore, soft_delete_article_in_firestore
from models.pydantic_models import NewsQuery, NewsResponse, NewsArticleIngestRequest, NewsBulkIngestRequest, NewsArticlePatchRequest
from utils.error_handlers import handle_database_error
from utils.news_service import get_financial_news, combine_sentiment_analysis

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/news", response_model=dict)
async def get_news_rest_style(
    ticker: Optional[str] = Query("", description="Stock ticker to filter by"),
    days: Optional[int] = Query(7, ge=1, le=365, description="Number of days to look back (365 = all articles)"),
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
    days: Optional[int] = Query(7, ge=1, le=365, description="Number of days to look back (365 = all articles)"),
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
        firestore_articles = []
        newsapi_articles = []

        # If live mode is requested, fetch from NewsAPI and store in Firestore
        # Note: When live=False, we only fetch from Firestore (no NewsAPI)
        if live:
            try:
                # Use live NewsAPI service with real-time sentiment analysis
                logger.info(f"Live mode enabled, fetching fresh news from NewsAPI for ticker: {ticker}, days: {days}, sentiment: {sentiment}")
                newsapi_articles = await get_financial_news(ticker=ticker, days=days, sentiment_filter=sentiment)
                
                # Apply limit to NewsAPI results
                if len(newsapi_articles) > limit:
                    newsapi_articles = newsapi_articles[:limit]
                
                logger.info(f"NewsAPI returned {len(newsapi_articles)} fresh articles")
                
                # Store new articles in Firestore for future use
                if newsapi_articles:
                    logger.info(f"📦 Starting to store {len(newsapi_articles)} articles in Firestore...")
                    stored_count = 0
                    updated_count = 0
                    failed_count = 0
                    for article in newsapi_articles:
                        try:
                            success, is_new = await store_article_in_firestore(article)
                            if success:
                                if is_new:
                                    stored_count += 1
                                else:
                                    updated_count += 1
                            else:
                                failed_count += 1
                                logger.warning(f"Failed to store article in Firestore (returned False): {article.get('title', 'No title')[:50]}")
                                logger.warning(f"  URL: {article.get('url', 'N/A')[:80]}")
                        except Exception as store_error:
                            failed_count += 1
                            logger.error(f"Exception storing article in Firestore: {store_error}", exc_info=True)
                            logger.error(f"  Article: {article.get('title', 'No title')[:50]}")
                            logger.error(f"  URL: {article.get('url', 'N/A')[:80]}")
                    
                    if stored_count > 0:
                        logger.info(f"✅ Successfully stored {stored_count} NEW articles in Firestore")
                    if updated_count > 0:
                        logger.info(f"🔄 Updated timestamps for {updated_count} existing articles in Firestore")
                    if failed_count > 0:
                        logger.warning(f"❌ Failed to store {failed_count} articles in Firestore (check logs for details)")
                    if stored_count == 0 and updated_count == 0 and failed_count == 0:
                        logger.warning("⚠️ No articles were processed for storage (all may have been duplicates or Firestore unavailable)")
                
            except Exception as e:
                logger.warning(f"NewsAPI failed (possibly rate limited): {e}")
                logger.info("Falling back to Firestore only")
        
        # Fetch from Firestore (always, regardless of live mode)
        logger.info(f"Fetching articles from Firestore for ticker: {ticker}, days: {days}, sentiment: {sentiment}")
        firestore_articles = await get_articles_from_firestore(ticker=ticker, days=days, sentiment_filter=sentiment, limit=limit)
        logger.info(f"Firestore returned {len(firestore_articles)} articles for ticker '{ticker}'")
        
        # If no articles found for specific ticker, try general financial news
        if not firestore_articles and ticker and ticker.strip():
            logger.info(f"No articles found for ticker '{ticker}', trying general financial news")
            firestore_articles = await get_articles_from_firestore(ticker="", days=days, sentiment_filter=sentiment, limit=limit)
            logger.info(f"Firestore returned {len(firestore_articles)} general articles")
        
        # If live mode is disabled, return only Firestore articles
        if not live:
            articles = firestore_articles
            logger.info(f"Live mode disabled - returning {len(articles)} articles from Firestore only")
        else:
            # Merge NewsAPI and Firestore articles, prioritizing NewsAPI (fresh) articles
            # Use article_id or URL as unique identifier to avoid duplicates
            article_map = {}
            
            # First, add Firestore articles
            for article in firestore_articles:
                article_id = article.get("article_id") or article.get("url", "")
                if article_id:
                    article_map[article_id] = article
            
            # Then, add/overwrite with NewsAPI articles (these are fresher)
            for article in newsapi_articles:
                article_id = article.get("article_id") or article.get("url", "")
                if article_id:
                    article_map[article_id] = article
            
            # Convert map back to list and sort by published_date (newest first)
            articles = list(article_map.values())
            articles.sort(key=lambda x: x.get("published_date", ""), reverse=True)
            
            # Apply final limit
            if len(articles) > limit:
                articles = articles[:limit]
            
            logger.info(f"Final merged result: {len(articles)} unique articles (NewsAPI: {len(newsapi_articles)}, Firestore: {len(firestore_articles)})")


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


@router.get("/news/{article_id}", response_model=dict)
async def get_news_article(article_id: str):
    """
    Get a single news article by ID from Firestore.
    
    Returns the full article document including all fields.
    Returns 404 if article does not exist or is soft-deleted.
    """
    try:
        article = await get_article_from_firestore(article_id)
        
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Article with ID {article_id} not found"
            )
        
        return {
            "status": "success",
            "article_id": article_id,
            "article": article,
            "message": "Article retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting article {article_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving article: {str(e)}"
        )


@router.post("/news/ingest", response_model=dict, status_code=status.HTTP_201_CREATED)
async def ingest_news(
    request: Dict[str, Any] = Body(...)
):
    """
    Create/Ingest news articles into Firestore.
    
    Supports both single article and bulk ingestion:
    - Single article: Send article object directly (e.g., {"title": "...", "content": "...", ...})
    - Bulk ingestion: Send {"articles": [article1, article2, ...]}
    
    If sentiment_analysis is not provided, it will be automatically computed.
    Articles are stored in Firestore 'financial_news' collection.
    """
    try:
        # Determine if this is a bulk request or single article
        if "articles" in request and isinstance(request["articles"], list):
            # Bulk ingestion
            bulk_request = NewsBulkIngestRequest(**request)
            articles_to_process = bulk_request.articles
        else:
            # Single article
            article_request = NewsArticleIngestRequest(**request)
            articles_to_process = [article_request]
        
        results = []
        errors = []
        
        for article_request in articles_to_process:
            try:
                # Prepare article data
                article_data = {
                    "title": article_request.title,
                    "content": article_request.content,
                    "published_date": article_request.published_date,
                    "source": article_request.source,
                    "ticker": article_request.ticker.upper() if article_request.ticker else None,
                    "url": article_request.url,
                    "extracted_entities": article_request.extracted_entities,
                    "metadata": article_request.metadata or {}
                }
                
                # Generate unique article ID if not provided
                article_id = article_data.get("article_id")
                if not article_id:
                    # Generate ID from URL hash or create new UUID
                    if article_request.url:
                        article_id = f"article_{abs(hash(article_request.url))}"
                    else:
                        article_id = f"article_{uuid.uuid4().hex[:16]}"
                
                article_data["article_id"] = article_id
                
                # Handle sentiment analysis
                if article_request.sentiment_analysis:
                    # Use provided sentiment analysis
                    sentiment_data = article_request.sentiment_analysis.dict(exclude_none=True)
                    # Ensure overall_score exists (use polarity if overall_score not provided)
                    if "overall_score" not in sentiment_data and "polarity" in sentiment_data:
                        sentiment_data["overall_score"] = sentiment_data["polarity"]
                    article_data["sentiment_analysis"] = sentiment_data
                    logger.info(f"Using provided sentiment analysis for article: {article_id}")
                else:
                    # Compute sentiment analysis automatically
                    logger.info(f"Computing sentiment analysis for article: {article_id}")
                    sentiment_text = f"{article_request.title}. {article_request.content}"
                    sentiment_result = combine_sentiment_analysis(sentiment_text)
                    article_data["sentiment_analysis"] = sentiment_result
                
                # Store article in Firestore
                success, is_new = await store_article_in_firestore(article_data)
                
                if success:
                    results.append({
                        "article_id": article_id,
                        "title": article_request.title,
                        "ticker": article_data.get("ticker"),
                        "status": "ingested"
                    })
                    logger.info(f"Successfully ingested article: {article_id} - {article_request.title[:50]}")
                else:
                    errors.append({
                        "title": article_request.title,
                        "error": "Failed to store article in Firestore"
                    })
                    logger.error(f"Failed to ingest article: {article_request.title[:50]}")
                    
            except Exception as e:
                error_msg = str(e)
                errors.append({
                    "title": article_request.title if hasattr(article_request, 'title') else "Unknown",
                    "error": error_msg
                })
                logger.error(f"Error processing article: {error_msg}")
                continue
        
        # Prepare response
        if errors and not results:
            # All articles failed
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to ingest all articles. Errors: {errors}"
            )
        
        response = {
            "message": f"Successfully ingested {len(results)} article(s)" + (f", {len(errors)} failed" if errors else ""),
            "ingested_count": len(results),
            "failed_count": len(errors),
            "results": results,
            "status": "success"
        }
        
        if errors:
            response["errors"] = errors
            # Return 207 Multi-Status if some succeeded and some failed
            response["status_code"] = 207
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in news ingestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ingesting news articles: {str(e)}"
        )


@router.put("/news/{article_id}", response_model=dict)
async def update_news_article(
    article_id: str,
    request: NewsArticleIngestRequest
):
    """
    Full update (PUT) - Replace entire news article document in Firestore.
    
    Replaces ALL fields of the article with the provided values.
    All fields must be provided (or set to null).
    The article_id in the URL must match an existing article.
    
    Returns 404 if article does not exist.
    """
    try:
        # Check if article exists
        existing_article = await get_article_from_firestore(article_id)
        
        if not existing_article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Article with ID {article_id} not found"
            )
        
        # Prepare article data for full replacement (PUT behavior)
        article_data = {
            "title": request.title,
            "content": request.content,
            "published_date": request.published_date,
            "source": request.source,
            "ticker": request.ticker.upper() if request.ticker else None,
            "url": request.url,
            "extracted_entities": request.extracted_entities,
            "metadata": request.metadata or {}
        }
        
        # Handle sentiment analysis - must be provided for PUT
        if request.sentiment_analysis:
            sentiment_data = request.sentiment_analysis.dict(exclude_none=True)
            # Ensure overall_score exists (use polarity if overall_score not provided)
            if "overall_score" not in sentiment_data and "polarity" in sentiment_data:
                sentiment_data["overall_score"] = sentiment_data["polarity"]
            article_data["sentiment_analysis"] = sentiment_data
        else:
            # For PUT, if sentiment not provided, set to None (full replacement)
            article_data["sentiment_analysis"] = None
        
        # Update article in Firestore
        success = await update_article_in_firestore(article_id, article_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update article {article_id} in Firestore"
            )
        
        # Get updated article to return
        updated_article = await get_article_from_firestore(article_id)
        
        logger.info(f"Updated article {article_id} in Firestore")
        
        return {
            "message": f"Article {article_id} updated successfully",
            "article_id": article_id,
            "article": updated_article,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating article {article_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating article: {str(e)}"
        )


@router.patch("/news/{article_id}", response_model=dict)
async def patch_news_article(
    article_id: str,
    request: NewsArticlePatchRequest
):
    """
    Partial update (PATCH) - Update only provided fields of a news article.
    
    Only updates the fields that are provided in the request.
    Fields not provided will remain unchanged.
    The article_id in the URL must match an existing article.
    
    Returns 404 if article does not exist.
    """
    try:
        # Check if article exists
        existing_article = await get_article_from_firestore(article_id)
        
        if not existing_article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Article with ID {article_id} not found"
            )
        
        # Prepare update data - only include non-None fields (PATCH behavior)
        update_data = {}
        updated_fields = []
        
        if request.title is not None:
            update_data["title"] = request.title
            updated_fields.append("title")
        
        if request.content is not None:
            update_data["content"] = request.content
            updated_fields.append("content")
        
        if request.published_date is not None:
            update_data["published_date"] = request.published_date
            updated_fields.append("published_date")
        
        if request.source is not None:
            update_data["source"] = request.source
            updated_fields.append("source")
        
        if request.ticker is not None:
            update_data["ticker"] = request.ticker.upper()
            updated_fields.append("ticker")
        
        if request.url is not None:
            update_data["url"] = request.url
            updated_fields.append("url")
        
        if request.extracted_entities is not None:
            update_data["extracted_entities"] = request.extracted_entities
            updated_fields.append("extracted_entities")
        
        if request.metadata is not None:
            update_data["metadata"] = request.metadata
            updated_fields.append("metadata")
        
        # Handle sentiment analysis
        if request.sentiment_analysis is not None:
            sentiment_data = request.sentiment_analysis.dict(exclude_none=True)
            # Ensure overall_score exists (use polarity if overall_score not provided)
            if "overall_score" not in sentiment_data and "polarity" in sentiment_data:
                sentiment_data["overall_score"] = sentiment_data["polarity"]
            update_data["sentiment_analysis"] = sentiment_data
            updated_fields.append("sentiment_analysis")
        
        # Check if any fields were provided to update
        if not updated_fields:
            logger.info(f"No fields provided for update for article {article_id}")
            return {
                "message": f"No fields provided for update. Article {article_id} unchanged.",
                "article_id": article_id,
                "article": existing_article,
                "status": "success"
            }
        
        # Update article in Firestore (partial update)
        success = await patch_article_in_firestore(article_id, update_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update article {article_id} in Firestore"
            )
        
        # Get updated article to return
        updated_article = await get_article_from_firestore(article_id)
        
        logger.info(f"Patched article {article_id}: updated fields={updated_fields}")
        
        return {
            "message": f"Article {article_id} updated successfully",
            "article_id": article_id,
            "updated_fields": updated_fields,
            "article": updated_article,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error patching article {article_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating article: {str(e)}"
        )


@router.delete("/news/{article_id}", response_model=dict)
async def delete_news_article(
    article_id: str
):
    """
    Soft delete a news article.
    
    Marks the article as deleted by setting the `deleted_at` timestamp.
    The article document remains in Firestore but will be excluded from GET queries.
    
    Returns 404 if article does not exist or is already deleted.
    """
    try:
        # Check if article exists
        existing_article = await get_article_from_firestore(article_id)
        
        if not existing_article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Article with ID {article_id} not found"
            )
        
        # Check if already deleted
        if existing_article.get('deleted_at'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Article with ID {article_id} is already deleted"
            )
        
        # Soft delete: set deleted_at timestamp
        success = await soft_delete_article_in_firestore(article_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to soft delete article {article_id} in Firestore"
            )
        
        # Get deleted article to return deleted_at timestamp
        # Note: get_article_from_firestore filters out deleted articles, so we need to get it directly
        from config.firestore import get_firestore_collection
        collection = get_firestore_collection('financial_news')
        if collection:
            doc = collection.document(article_id).get()
            if doc.exists:
                deleted_article = doc.to_dict()
                deleted_at = deleted_article.get('deleted_at')
            else:
                deleted_at = None
        else:
            deleted_at = None
        
        logger.info(f"Soft deleted article {article_id} at {deleted_at}")
        
        return {
            "message": f"Article {article_id} has been soft deleted",
            "article_id": article_id,
            "deleted_at": deleted_at,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error soft deleting article {article_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting article: {str(e)}"
        )