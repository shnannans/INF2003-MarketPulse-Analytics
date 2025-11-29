"""
Error States Utilities (Task 62: Error Handling & User Feedback - Error States)
Provides utilities for error state management and user-friendly error responses
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorStateManager:
    """
    Error state manager (Task 62: Error Handling & User Feedback - Error States).
    Provides utilities for managing error states and user-friendly error responses.
    """
    
    # Error type mappings
    ERROR_TYPES = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_server_error",
        503: "service_unavailable"
    }
    
    # User-friendly error messages
    ERROR_MESSAGES = {
        "bad_request": "The request was invalid. Please check your input and try again.",
        "unauthorized": "You are not authorized to access this resource. Please log in.",
        "forbidden": "You do not have permission to perform this action.",
        "not_found": "The requested resource was not found.",
        "conflict": "A conflict occurred. The resource may already exist or be in use.",
        "validation_error": "The provided data is invalid. Please check your input.",
        "rate_limit_exceeded": "Too many requests. Please try again later.",
        "internal_server_error": "An internal server error occurred. Please try again later.",
        "service_unavailable": "The service is temporarily unavailable. Please try again later.",
        "database_error": "A database error occurred. Please try again later.",
        "network_error": "A network error occurred. Please check your connection and try again."
    }
    
    # Actionable guidance for errors
    ERROR_GUIDANCE = {
        "bad_request": "Check your input parameters and ensure all required fields are provided.",
        "unauthorized": "Please log in or check your authentication credentials.",
        "forbidden": "Contact an administrator if you believe you should have access.",
        "not_found": "Verify the resource ID or path is correct.",
        "conflict": "The resource may already exist. Try updating instead of creating.",
        "validation_error": "Review the validation errors and correct your input.",
        "rate_limit_exceeded": "Wait a few moments before making another request.",
        "internal_server_error": "If the problem persists, contact support.",
        "service_unavailable": "The service should be available shortly. Please try again in a moment.",
        "database_error": "The database may be temporarily unavailable. Please try again.",
        "network_error": "Check your internet connection and try again."
    }
    
    @staticmethod
    def create_error_response(
        status_code: int,
        error_type: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        retry_after: Optional[int] = None,
        error_id: Optional[str] = None
    ) -> JSONResponse:
        """
        Create a user-friendly error response (Task 62: Error States).
        
        Args:
            status_code: HTTP status code
            error_type: Error type identifier
            message: User-friendly error message
            details: Additional error details
            recoverable: Whether the error is recoverable
            retry_after: Seconds to wait before retrying (for rate limits)
            error_id: Unique error ID for tracking
        
        Returns:
            JSONResponse with error information
        """
        if error_type is None:
            error_type = ErrorStateManager.ERROR_TYPES.get(status_code, "unknown_error")
        
        if message is None:
            message = ErrorStateManager.ERROR_MESSAGES.get(error_type, "An error occurred.")
        
        guidance = ErrorStateManager.ERROR_GUIDANCE.get(error_type, "Please try again later.")
        
        error_dict = {
            "type": error_type,
            "status_code": status_code,
            "message": message,
            "guidance": guidance,
            "recoverable": recoverable,
            "timestamp": datetime.now().isoformat()
        }
        
        if error_id:
            error_dict["error_id"] = error_id
        
        if details:
            error_dict["details"] = details
        
        if retry_after:
            error_dict["retry_after"] = retry_after
        
        error_response = {
            "error": error_dict
        }
        
        # Log error for admin tracking
        logger.error(
            f"Error {status_code} ({error_type}): {message} - "
            f"Recoverable: {recoverable}, Error ID: {error_id}"
        )
        
        # Build headers
        headers = {
            "X-Error-Type": error_type,
            "X-Recoverable": str(recoverable).lower()
        }
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        return JSONResponse(
            status_code=status_code,
            content=error_response,
            headers=headers
        )
    
    @staticmethod
    def create_not_found_response(
        resource_type: str = "resource",
        resource_id: Optional[str] = None
    ) -> JSONResponse:
        """Create a 404 Not Found error response."""
        message = f"The {resource_type} was not found."
        if resource_id:
            message = f"The {resource_type} with ID '{resource_id}' was not found."
        
        return ErrorStateManager.create_error_response(
            status_code=404,
            error_type="not_found",
            message=message,
            details={"resource_type": resource_type, "resource_id": resource_id} if resource_id else {"resource_type": resource_type}
        )
    
    @staticmethod
    def create_forbidden_response(
        action: Optional[str] = None
    ) -> JSONResponse:
        """Create a 403 Forbidden error response."""
        message = "You do not have permission to perform this action."
        if action:
            message = f"You do not have permission to {action}."
        
        return ErrorStateManager.create_error_response(
            status_code=403,
            error_type="forbidden",
            message=message,
            details={"action": action} if action else None
        )
    
    @staticmethod
    def create_validation_error_response(
        validation_errors: List[Dict[str, Any]]
    ) -> JSONResponse:
        """Create a 422 Validation Error response."""
        return ErrorStateManager.create_error_response(
            status_code=422,
            error_type="validation_error",
            message="The provided data is invalid. Please check your input.",
            details={"validation_errors": validation_errors}
        )
    
    @staticmethod
    def create_rate_limit_response(
        retry_after: int = 60
    ) -> JSONResponse:
        """Create a 429 Rate Limit Exceeded response."""
        return ErrorStateManager.create_error_response(
            status_code=429,
            error_type="rate_limit_exceeded",
            message="Too many requests. Please try again later.",
            retry_after=retry_after,
            recoverable=True
        )
    
    @staticmethod
    def create_network_error_response(
        details: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """Create a network error response."""
        return ErrorStateManager.create_error_response(
            status_code=503,
            error_type="network_error",
            message="A network error occurred. Please check your connection and try again.",
            details=details,
            recoverable=True
        )


# Global error log for admin tracking (Task 62)
_error_log: List[Dict[str, Any]] = []
_max_error_log_size = 1000


def log_error(error_info: Dict[str, Any]):
    """Log error for admin tracking (Task 62: Error States)."""
    global _error_log
    _error_log.append({
        **error_info,
        "timestamp": datetime.now().isoformat()
    })
    if len(_error_log) > _max_error_log_size:
        _error_log = _error_log[-_max_error_log_size:]


def get_error_log(limit: int = 100) -> List[Dict[str, Any]]:
    """Get error log for admin viewing (Task 62: Error States)."""
    return _error_log[-limit:]

