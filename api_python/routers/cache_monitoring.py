"""
Cache Monitoring Endpoints (Task 38)
Provides endpoints to monitor and manage cache
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from config.database import get_mysql_session
from utils.cache_utils import get_cache_stats, clear_cache

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/cache/stats", response_model=dict)
async def get_cache_stats_endpoint(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get cache statistics (Task 38: Caching Strategy).
    
    Returns information about:
    - In-memory cache sizes and TTLs
    - Redis connection status
    - Cache hit/miss rates (if available)
    """
    try:
        stats = get_cache_stats()
        
        return {
            "status": "success",
            "cache_stats": stats,
            "message": "Cache statistics retrieved"
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting cache stats: {str(e)}"
        )


@router.post("/cache/clear", response_model=dict)
async def clear_cache_endpoint(
    cache_type: str = Query(None, description="Cache type to clear: 'company', 'stock_prices', 'analytics', or None for all"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Clear cache (Task 38: Caching Strategy).
    
    Args:
        cache_type: Type of cache to clear (optional, clears all if not provided)
    """
    try:
        clear_cache(cache_type)
        
        return {
            "status": "success",
            "message": f"Cache cleared: {cache_type if cache_type else 'all'}"
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing cache: {str(e)}"
        )

