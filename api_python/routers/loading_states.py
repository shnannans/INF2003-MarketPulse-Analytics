"""
Loading States Endpoints (Task 63: Error Handling & User Feedback - Loading States)
Provides endpoints for loading state management and progress tracking
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging
import uuid

from config.database import get_mysql_session
from utils.loading_states import LoadingStateManager, LoadingState, track_operation_progress

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/loading/{operation_id}", response_model=dict)
async def get_loading_state(
    operation_id: str,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get loading state for an operation (Task 63: Error Handling & User Feedback - Loading States).
    Returns current loading state, progress, and status message.
    """
    try:
        loading_state = LoadingStateManager.get_loading_state(operation_id)
        
        if not loading_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Loading state not found for operation: {operation_id}"
            )
        
        return {
            "status": "success",
            "loading_state": loading_state,
            "message": "Loading state retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting loading state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting loading state: {str(e)}"
        )


@router.post("/loading/{operation_id}/update", response_model=dict)
async def update_loading_state(
    operation_id: str,
    progress: Optional[int] = Query(None, ge=0, le=100, description="Progress percentage (0-100)"),
    message: Optional[str] = Query(None, description="Status message"),
    state: Optional[str] = Query(None, description="New state: loading, success, error, cancelled"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Update loading state for an operation (Task 63: Error Handling & User Feedback - Loading States).
    """
    try:
        state_enum = None
        if state:
            try:
                state_enum = LoadingState(state.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid state: {state}. Valid states: loading, success, error, cancelled"
                )
        
        updated_state = LoadingStateManager.update_loading_state(
            operation_id,
            progress=progress,
            message=message,
            state=state_enum
        )
        
        if not updated_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Loading state not found for operation: {operation_id}"
            )
        
        return {
            "status": "success",
            "loading_state": updated_state,
            "message": "Loading state updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating loading state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating loading state: {str(e)}"
        )


@router.post("/loading/{operation_id}/complete", response_model=dict)
async def complete_loading_state(
    operation_id: str,
    success: bool = Query(True, description="Whether operation was successful"),
    message: Optional[str] = Query(None, description="Completion message"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Complete loading state for an operation (Task 63: Error Handling & User Feedback - Loading States).
    """
    try:
        completed_state = LoadingStateManager.complete_loading_state(
            operation_id,
            success=success,
            message=message
        )
        
        if not completed_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Loading state not found for operation: {operation_id}"
            )
        
        return {
            "status": "success",
            "loading_state": completed_state,
            "message": "Loading state completed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing loading state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completing loading state: {str(e)}"
        )


@router.post("/loading/{operation_id}/cancel", response_model=dict)
async def cancel_loading_state(
    operation_id: str,
    message: Optional[str] = Query(None, description="Cancellation message"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Cancel loading state for an operation (Task 63: Error Handling & User Feedback - Loading States).
    """
    try:
        cancelled_state = LoadingStateManager.cancel_loading_state(
            operation_id,
            message=message
        )
        
        if not cancelled_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Loading state not found for operation: {operation_id}"
            )
        
        return {
            "status": "success",
            "loading_state": cancelled_state,
            "message": "Loading state cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling loading state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling loading state: {str(e)}"
        )


@router.get("/loading", response_model=dict)
async def get_all_loading_states(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get all active loading states (Task 63: Error Handling & User Feedback - Loading States).
    """
    try:
        loading_states = LoadingStateManager.get_all_loading_states()
        
        return {
            "status": "success",
            "loading_states": loading_states,
            "count": len(loading_states),
            "message": "Loading states retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting loading states: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting loading states: {str(e)}"
        )


@router.post("/loading/create", response_model=dict)
async def create_loading_state(
    operation_type: str = Query(..., description="Type of operation"),
    estimated_duration: Optional[float] = Query(None, description="Estimated duration in seconds"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Create a new loading state (Task 63: Error Handling & User Feedback - Loading States).
    Returns operation_id for tracking.
    """
    try:
        operation_id = str(uuid.uuid4())
        
        loading_state = LoadingStateManager.create_loading_state(
            operation_id,
            operation_type,
            estimated_duration
        )
        
        return {
            "status": "success",
            "operation_id": operation_id,
            "loading_state": loading_state,
            "message": "Loading state created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating loading state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating loading state: {str(e)}"
        )

