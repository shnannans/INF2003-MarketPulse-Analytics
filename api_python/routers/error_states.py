"""
Error States Endpoints (Task 62: Error Handling & User Feedback - Error States)
Provides endpoints for error state management and error logging
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from config.database import get_mysql_session
from utils.error_states import ErrorStateManager, log_error, get_error_log
import time

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/errors/log", response_model=dict)
async def get_error_log_endpoint(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of errors to return"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get error log for admin viewing (Task 62: Error Handling & User Feedback - Error States).
    Returns recent errors for monitoring and debugging.
    """
    try:
        errors = get_error_log(limit)
        
        return {
            "status": "success",
            "error_count": len(errors),
            "errors": errors,
            "message": "Error log retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting error log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting error log: {str(e)}"
        )


@router.get("/errors/test/{error_type}", response_model=dict)
async def test_error_response(
    error_type: str,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Test error response formats (Task 62: Error Handling & User Feedback - Error States).
    Useful for testing error handling in frontend.
    
    Supported error types:
    - not_found (404)
    - forbidden (403)
    - bad_request (400)
    - validation_error (422)
    - rate_limit_exceeded (429)
    - internal_server_error (500)
    - service_unavailable (503)
    """
    try:
        error_type_map = {
            "not_found": (404, "not_found"),
            "forbidden": (403, "forbidden"),
            "bad_request": (400, "bad_request"),
            "validation_error": (422, "validation_error"),
            "rate_limit_exceeded": (429, "rate_limit_exceeded"),
            "internal_server_error": (500, "internal_server_error"),
            "service_unavailable": (503, "service_unavailable")
        }
        
        if error_type not in error_type_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown error type: {error_type}. Supported types: {', '.join(error_type_map.keys())}"
            )
        
        status_code, error_type_enum = error_type_map[error_type]
        
        # Log the test error
        log_error({
            "error_type": error_type_enum,
            "status_code": status_code,
            "test": True,
            "message": f"Test error response for {error_type}"
        })
        
        # Return appropriate error response
        return ErrorStateManager.create_error_response(
            status_code=status_code,
            error_type=error_type_enum,
            message=f"Test error response for {error_type}",
            details={"test": True},
            error_id=f"test_{error_type}_{int(time.time())}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in test error response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in test error response: {str(e)}"
        )


@router.get("/errors/stats", response_model=dict)
async def get_error_stats(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get error statistics (Task 62: Error Handling & User Feedback - Error States).
    Returns error counts by type for monitoring.
    """
    try:
        errors = get_error_log(limit=1000)
        
        # Count errors by type
        error_counts = {}
        for error in errors:
            error_type = error.get("error_type", "unknown")
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            "status": "success",
            "total_errors": len(errors),
            "error_counts": error_counts,
            "message": "Error statistics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting error stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting error stats: {str(e)}"
        )

