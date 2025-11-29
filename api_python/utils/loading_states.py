"""
Loading States Utilities (Task 63: Error Handling & User Feedback - Loading States)
Provides utilities for loading state management and progress tracking
"""
import logging
import time
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class LoadingState(Enum):
    """Loading state enumeration (Task 63: Loading States)."""
    IDLE = "idle"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class LoadingStateManager:
    """
    Loading state manager (Task 63: Error Handling & User Feedback - Loading States).
    Provides utilities for managing loading states and progress tracking.
    """
    
    # Global loading state tracking
    _loading_states: Dict[str, Dict[str, Any]] = {}
    
    @staticmethod
    def create_loading_state(
        operation_id: str,
        operation_type: str,
        estimated_duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a new loading state (Task 63: Loading States).
        
        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation (e.g., "data_sync", "query", "export")
            estimated_duration: Estimated duration in seconds
        
        Returns:
            Loading state dictionary
        """
        loading_state = {
            "operation_id": operation_id,
            "operation_type": operation_type,
            "state": LoadingState.LOADING.value,
            "start_time": datetime.now().isoformat(),
            "progress": 0,
            "estimated_duration": estimated_duration,
            "message": f"{operation_type} in progress..."
        }
        
        LoadingStateManager._loading_states[operation_id] = loading_state
        logger.info(f"Loading state created: {operation_id} ({operation_type})")
        
        return loading_state
    
    @staticmethod
    def update_loading_state(
        operation_id: str,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        state: Optional[LoadingState] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update loading state (Task 63: Loading States).
        
        Args:
            operation_id: Operation identifier
            progress: Progress percentage (0-100)
            message: Status message
            state: New loading state
        
        Returns:
            Updated loading state or None if not found
        """
        if operation_id not in LoadingStateManager._loading_states:
            logger.warning(f"Loading state not found: {operation_id}")
            return None
        
        loading_state = LoadingStateManager._loading_states[operation_id]
        
        if progress is not None:
            loading_state["progress"] = min(100, max(0, progress))
        
        if message is not None:
            loading_state["message"] = message
        
        if state is not None:
            loading_state["state"] = state.value
            if state == LoadingState.SUCCESS:
                loading_state["end_time"] = datetime.now().isoformat()
                if "start_time" in loading_state:
                    start = datetime.fromisoformat(loading_state["start_time"])
                    end = datetime.now()
                    loading_state["duration_seconds"] = (end - start).total_seconds()
            elif state == LoadingState.ERROR:
                loading_state["end_time"] = datetime.now().isoformat()
        
        return loading_state
    
    @staticmethod
    def get_loading_state(operation_id: str) -> Optional[Dict[str, Any]]:
        """Get loading state by operation ID."""
        return LoadingStateManager._loading_states.get(operation_id)
    
    @staticmethod
    def complete_loading_state(
        operation_id: str,
        success: bool = True,
        message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Complete loading state (Task 63: Loading States).
        
        Args:
            operation_id: Operation identifier
            success: Whether operation was successful
            message: Completion message
        
        Returns:
            Completed loading state or None if not found
        """
        state = LoadingState.SUCCESS if success else LoadingState.ERROR
        if message is None:
            message = "Operation completed successfully" if success else "Operation failed"
        
        return LoadingStateManager.update_loading_state(
            operation_id,
            progress=100,
            message=message,
            state=state
        )
    
    @staticmethod
    def cancel_loading_state(
        operation_id: str,
        message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Cancel loading state."""
        if message is None:
            message = "Operation cancelled"
        
        return LoadingStateManager.update_loading_state(
            operation_id,
            message=message,
            state=LoadingState.CANCELLED
        )
    
    @staticmethod
    def cleanup_loading_state(operation_id: str, max_age_seconds: int = 3600):
        """
        Clean up old loading states (Task 63: Loading States).
        
        Args:
            operation_id: Operation identifier
            max_age_seconds: Maximum age in seconds before cleanup
        """
        if operation_id not in LoadingStateManager._loading_states:
            return
        
        loading_state = LoadingStateManager._loading_states[operation_id]
        
        if "start_time" in loading_state:
            start = datetime.fromisoformat(loading_state["start_time"])
            age = (datetime.now() - start).total_seconds()
            
            if age > max_age_seconds:
                del LoadingStateManager._loading_states[operation_id]
                logger.info(f"Cleaned up old loading state: {operation_id}")
    
    @staticmethod
    def get_all_loading_states() -> Dict[str, Dict[str, Any]]:
        """Get all active loading states."""
        return LoadingStateManager._loading_states.copy()
    
    @staticmethod
    def cleanup_all_loading_states(max_age_seconds: int = 3600):
        """Clean up all old loading states."""
        operation_ids = list(LoadingStateManager._loading_states.keys())
        for operation_id in operation_ids:
            LoadingStateManager.cleanup_loading_state(operation_id, max_age_seconds)


async def track_operation_progress(
    operation_id: str,
    operation_type: str,
    operation_func: Callable,
    update_interval: float = 0.5
) -> Dict[str, Any]:
    """
    Track operation progress with loading state (Task 63: Loading States).
    
    Args:
        operation_id: Unique operation identifier
        operation_type: Type of operation
        operation_func: Async function to execute
        update_interval: Progress update interval in seconds
    
    Returns:
        Operation result with loading state
    """
    # Create loading state
    LoadingStateManager.create_loading_state(operation_id, operation_type)
    
    try:
        # Execute operation
        result = await operation_func()
        
        # Mark as successful
        LoadingStateManager.complete_loading_state(
            operation_id,
            success=True,
            message="Operation completed successfully"
        )
        
        return {
            "status": "success",
            "operation_id": operation_id,
            "result": result
        }
        
    except Exception as e:
        # Mark as failed
        LoadingStateManager.complete_loading_state(
            operation_id,
            success=False,
            message=f"Operation failed: {str(e)}"
        )
        
        logger.error(f"Operation {operation_id} failed: {e}")
        raise

