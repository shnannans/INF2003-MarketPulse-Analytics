"""
Connection Pool Monitoring Endpoints (Task 37)
Provides endpoints to monitor connection pool status
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from config.database import get_mysql_session, get_pool_status

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/pool/status", response_model=dict)
async def get_pool_status_endpoint(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get connection pool status (Task 37: Connection Pooling).
    
    Returns information about:
    - Pool size
    - Checked out connections
    - Overflow connections
    - Pool class
    
    This helps monitor connection pool usage and identify potential issues.
    """
    try:
        status_info = get_pool_status()
        
        return {
            "status": "success",
            "pool_status": status_info,
            "message": "Connection pool status retrieved"
        }
    except Exception as e:
        logger.error(f"Error getting pool status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting pool status: {str(e)}"
        )

