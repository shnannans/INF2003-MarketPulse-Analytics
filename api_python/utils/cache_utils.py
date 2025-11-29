"""
Caching Utilities (Task 38: Caching Strategy)
Provides in-memory and distributed caching for frequently accessed data
"""
import json
import logging
from typing import Optional, Any, Dict
from functools import lru_cache
from cachetools import TTLCache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# In-memory caches (Task 38: Caching Strategy)
company_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes TTL
stock_price_cache = TTLCache(maxsize=500, ttl=180)  # 3 minutes TTL
analytics_cache = TTLCache(maxsize=200, ttl=600)  # 10 minutes TTL

# Redis client (optional, for distributed caching)
redis_client = None

try:
    import redis
    try:
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        # Test connection
        redis_client.ping()
        logger.info("Redis connection established for distributed caching")
    except (redis.ConnectionError, Exception) as e:
        logger.warning(f"Redis not available, using in-memory cache only: {e}")
        redis_client = None
except ImportError:
    logger.warning("Redis package not installed, using in-memory cache only")
    redis_client = None


def get_cache_key(cache_type: str, identifier: str) -> str:
    """Generate cache key"""
    return f"{cache_type}:{identifier}"


async def get_company_cached(ticker: str, db_session, fetch_func) -> Optional[Dict[str, Any]]:
    """
    Get company data with caching (Task 38: Caching Strategy).
    
    Args:
        ticker: Stock ticker symbol
        db_session: Database session
        fetch_func: Function to fetch from database if not cached
    
    Returns:
        Company data or None
    """
    ticker = ticker.upper()
    cache_key = get_cache_key("company", ticker)
    
    # Check in-memory cache first
    if ticker in company_cache:
        logger.debug(f"Cache hit (in-memory): {ticker}")
        return company_cache[ticker]
    
    # Check Redis cache if available
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit (Redis): {ticker}")
                company_data = json.loads(cached)
                # Also store in in-memory cache
                company_cache[ticker] = company_data
                return company_data
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")
    
    # Cache miss - fetch from database
    logger.debug(f"Cache miss: {ticker}")
    company_data = await fetch_func(ticker, db_session)
    
    if company_data:
        # Store in in-memory cache
        company_cache[ticker] = company_data
        
        # Store in Redis if available
        if redis_client:
            try:
                redis_client.setex(
                    cache_key,
                    300,  # 5 minutes TTL
                    json.dumps(company_data, default=str)
                )
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")
    
    return company_data


async def get_stock_prices_cached(ticker: str, days: int, db_session, fetch_func) -> Optional[list]:
    """
    Get stock prices with caching (Task 38: Caching Strategy).
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days
        db_session: Database session
        fetch_func: Function to fetch from database if not cached
    
    Returns:
        List of stock prices or None
    """
    ticker = ticker.upper()
    cache_key = get_cache_key("stock_prices", f"{ticker}:{days}")
    
    # Check in-memory cache first
    if cache_key in stock_price_cache:
        logger.debug(f"Cache hit (in-memory): {cache_key}")
        return stock_price_cache[cache_key]
    
    # Check Redis cache if available
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit (Redis): {cache_key}")
                prices_data = json.loads(cached)
                # Also store in in-memory cache
                stock_price_cache[cache_key] = prices_data
                return prices_data
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")
    
    # Cache miss - fetch from database
    logger.debug(f"Cache miss: {cache_key}")
    prices_data = await fetch_func(ticker, days, db_session)
    
    if prices_data:
        # Store in in-memory cache
        stock_price_cache[cache_key] = prices_data
        
        # Store in Redis if available
        if redis_client:
            try:
                redis_client.setex(
                    cache_key,
                    180,  # 3 minutes TTL
                    json.dumps(prices_data, default=str)
                )
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")
    
    return prices_data


async def get_analytics_cached(cache_key: str, db_session, fetch_func) -> Optional[Any]:
    """
    Get analytics data with caching (Task 38: Caching Strategy).
    
    Args:
        cache_key: Unique cache key for the analytics query
        db_session: Database session
        fetch_func: Function to fetch from database if not cached
    
    Returns:
        Analytics data or None
    """
    full_key = get_cache_key("analytics", cache_key)
    
    # Check in-memory cache first
    if full_key in analytics_cache:
        logger.debug(f"Cache hit (in-memory): {full_key}")
        return analytics_cache[full_key]
    
    # Check Redis cache if available
    if redis_client:
        try:
            cached = redis_client.get(full_key)
            if cached:
                logger.debug(f"Cache hit (Redis): {full_key}")
                analytics_data = json.loads(cached)
                # Also store in in-memory cache
                analytics_cache[full_key] = analytics_data
                return analytics_data
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")
    
    # Cache miss - fetch from database
    logger.debug(f"Cache miss: {full_key}")
    analytics_data = await fetch_func(db_session)
    
    if analytics_data:
        # Store in in-memory cache
        analytics_cache[full_key] = analytics_data
        
        # Store in Redis if available
        if redis_client:
            try:
                redis_client.setex(
                    full_key,
                    600,  # 10 minutes TTL
                    json.dumps(analytics_data, default=str)
                )
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")
    
    return analytics_data


def clear_cache(cache_type: Optional[str] = None):
    """
    Clear cache (Task 38: Caching Strategy).
    
    Args:
        cache_type: Type of cache to clear ('company', 'stock_prices', 'analytics', or None for all)
    """
    if cache_type == "company" or cache_type is None:
        company_cache.clear()
        logger.info("Company cache cleared")
    
    if cache_type == "stock_prices" or cache_type is None:
        stock_price_cache.clear()
        logger.info("Stock prices cache cleared")
    
    if cache_type == "analytics" or cache_type is None:
        analytics_cache.clear()
        logger.info("Analytics cache cleared")
    
    # Clear Redis if available
    if redis_client and cache_type is None:
        try:
            redis_client.flushdb()
            logger.info("Redis cache cleared")
        except Exception as e:
            logger.warning(f"Redis cache clear error: {e}")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics (Task 38: Caching Strategy).
    
    Returns:
        Dictionary with cache statistics
    """
    stats = {
        "in_memory": {
            "company": {
                "size": len(company_cache),
                "maxsize": company_cache.maxsize,
                "ttl": company_cache.ttl
            },
            "stock_prices": {
                "size": len(stock_price_cache),
                "maxsize": stock_price_cache.maxsize,
                "ttl": stock_price_cache.ttl
            },
            "analytics": {
                "size": len(analytics_cache),
                "maxsize": analytics_cache.maxsize,
                "ttl": analytics_cache.ttl
            }
        },
        "redis": {
            "available": redis_client is not None,
            "connected": False
        }
    }
    
    if redis_client:
        try:
            redis_client.ping()
            stats["redis"]["connected"] = True
            stats["redis"]["info"] = redis_client.info()
        except Exception as e:
            logger.warning(f"Redis stats error: {e}")
    
    return stats

