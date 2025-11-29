"""
API Integration Layer Endpoints (Task 73: API Integration Layer)
Provides configuration and utilities for API client integration
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
import logging

from config.database import get_mysql_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api-integration/config", response_model=dict)
async def get_api_integration_config(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get API integration layer configuration (Task 73: API Integration Layer).
    Returns configuration for API service layer.
    """
    try:
        api_config = {
            "base_url": "http://localhost:8000/api",
            "timeout_seconds": 30,
            "retry": {
                "enabled": True,
                "max_retries": 3,
                "retry_delay_ms": 1000,
                "retryable_status_codes": [500, 502, 503, 504]
            },
            "interceptors": {
                "request": {
                    "enabled": True,
                    "add_auth_token": True,
                    "add_timestamp": True,
                    "log_requests": True
                },
                "response": {
                    "enabled": True,
                    "transform_errors": True,
                    "log_responses": True,
                    "handle_token_refresh": True
                }
            },
            "caching": {
                "enabled": True,
                "default_ttl_seconds": 300,
                "cacheable_methods": ["GET"],
                "cache_key_strategy": "url_and_params"
            },
            "deduplication": {
                "enabled": True,
                "window_ms": 1000,
                "deduplicate_identical_requests": True
            },
            "cancellation": {
                "enabled": True,
                "cancel_on_unmount": True,
                "cancel_on_navigation": True
            },
            "loading_state": {
                "enabled": True,
                "global_loading": True,
                "per_request_loading": True,
                "loading_timeout_ms": 5000
            }
        }
        
        return {
            "status": "success",
            "api_integration_config": api_config,
            "message": "API integration configuration retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting API integration config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting API integration config: {str(e)}"
        )


@router.get("/api-integration/interceptors", response_model=dict)
async def get_interceptors_config(
    interceptor_type: Optional[str] = Query(None, description="Interceptor type: request, response"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get request/response interceptors configuration (Task 73: API Integration Layer).
    Returns configuration for interceptors.
    """
    try:
        interceptors = {
            "request": {
                "description": "Request interceptors run before sending requests",
                "functions": [
                    "Add authentication token",
                    "Add request timestamp",
                    "Add request ID for tracking",
                    "Log request details",
                    "Transform request data",
                    "Add custom headers"
                ],
                "example": """
// Request interceptor example
axios.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  config.headers['X-Request-ID'] = generateRequestId();
  return config;
});
"""
            },
            "response": {
                "description": "Response interceptors run after receiving responses",
                "functions": [
                    "Transform response data",
                    "Handle errors globally",
                    "Refresh authentication token",
                    "Log response details",
                    "Extract error messages",
                    "Handle rate limiting"
                ],
                "example": """
// Response interceptor example
axios.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Handle token refresh
      return refreshTokenAndRetry(error.config);
    }
    return Promise.reject(transformError(error));
  }
);
"""
            }
        }
        
        if interceptor_type and interceptor_type.lower() in interceptors:
            selected = {interceptor_type.lower(): interceptors[interceptor_type.lower()]}
        else:
            selected = interceptors
        
        return {
            "status": "success",
            "interceptor_type": interceptor_type,
            "interceptors": selected,
            "message": "Interceptors configuration retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting interceptors config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting interceptors config: {str(e)}"
        )


@router.get("/api-integration/error-handling", response_model=dict)
async def get_error_handling_config(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get error handling configuration (Task 73: API Integration Layer).
    Returns configuration for API error handling.
    """
    try:
        error_handling = {
            "error_types": {
                "network_error": {
                    "status_code": 0,
                    "message": "Network error. Please check your connection.",
                    "recoverable": True,
                    "retry": True
                },
                "timeout_error": {
                    "status_code": 408,
                    "message": "Request timeout. Please try again.",
                    "recoverable": True,
                    "retry": True
                },
                "server_error": {
                    "status_code": 500,
                    "message": "Server error. Please try again later.",
                    "recoverable": True,
                    "retry": True
                },
                "client_error": {
                    "status_code": 400,
                    "message": "Invalid request. Please check your input.",
                    "recoverable": True,
                    "retry": False
                },
                "authentication_error": {
                    "status_code": 401,
                    "message": "Authentication required. Please log in.",
                    "recoverable": True,
                    "retry": False,
                    "action": "redirect_to_login"
                },
                "authorization_error": {
                    "status_code": 403,
                    "message": "You do not have permission to perform this action.",
                    "recoverable": False,
                    "retry": False
                }
            },
            "error_transformation": {
                "enabled": True,
                "extract_message": True,
                "extract_details": True,
                "extract_error_id": True,
                "user_friendly_messages": True
            },
            "retry_strategy": {
                "enabled": True,
                "max_retries": 3,
                "retry_delay_ms": 1000,
                "exponential_backoff": True,
                "retryable_errors": ["network_error", "timeout_error", "server_error"]
            }
        }
        
        return {
            "status": "success",
            "error_handling": error_handling,
            "message": "Error handling configuration retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting error handling config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting error handling config: {str(e)}"
        )


@router.get("/api-integration/caching", response_model=dict)
async def get_api_caching_config(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get API request caching configuration (Task 73: API Integration Layer).
    Returns configuration for request caching and deduplication.
    """
    try:
        caching_config = {
            "enabled": True,
            "strategy": "stale-while-revalidate",
            "default_ttl_seconds": 300,
            "cacheable_methods": ["GET"],
            "cache_key_generation": {
                "method": "url_and_params",
                "include_headers": False,
                "include_auth": False
            },
            "cache_storage": {
                "type": "memory",
                "max_size_mb": 50,
                "eviction_policy": "lru"
            },
            "deduplication": {
                "enabled": True,
                "window_ms": 1000,
                "deduplicate_identical_requests": True,
                "deduplicate_concurrent_requests": True
            },
            "cache_invalidation": {
                "on_mutation": True,
                "on_logout": True,
                "manual_invalidation": True,
                "invalidation_patterns": [
                    "POST /api/companies",
                    "PUT /api/companies/*",
                    "DELETE /api/companies/*"
                ]
            }
        }
        
        return {
            "status": "success",
            "caching_config": caching_config,
            "message": "API caching configuration retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting API caching config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting API caching config: {str(e)}"
        )


@router.get("/api-integration/token-management", response_model=dict)
async def get_token_management_config(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get token management configuration (Task 73: API Integration Layer).
    Returns configuration for automatic token refresh.
    """
    try:
        token_management = {
            "automatic_refresh": {
                "enabled": True,
                "refresh_threshold_seconds": 300,  # Refresh 5 minutes before expiry
                "refresh_endpoint": "/api/auth/refresh",
                "refresh_on_401": True
            },
            "token_storage": {
                "method": "httpOnly_cookies",
                "access_token_key": "access_token",
                "refresh_token_key": "refresh_token",
                "secure": True,
                "same_site": "strict"
            },
            "token_handling": {
                "add_to_requests": True,
                "header_name": "Authorization",
                "header_format": "Bearer {token}",
                "clear_on_logout": True,
                "clear_on_401": False  # Try refresh first
            },
            "refresh_flow": {
                "steps": [
                    "Detect token expiry or 401 response",
                    "Call refresh endpoint with refresh token",
                    "Update stored tokens",
                    "Retry original request with new token",
                    "Handle refresh failure (redirect to login)"
                ]
            }
        }
        
        return {
            "status": "success",
            "token_management": token_management,
            "message": "Token management configuration retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting token management config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting token management config: {str(e)}"
        )


@router.get("/api-integration/request-cancellation", response_model=dict)
async def get_request_cancellation_config(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get request cancellation configuration (Task 73: API Integration Layer).
    Returns configuration for request cancellation.
    """
    try:
        cancellation_config = {
            "enabled": True,
            "cancel_on_unmount": True,
            "cancel_on_navigation": True,
            "cancel_on_new_request": False,  # Don't cancel if same request
            "abort_controller": {
                "enabled": True,
                "signal_propagation": True
            },
            "use_cases": [
                "Cancel requests when component unmounts",
                "Cancel requests on navigation",
                "Cancel duplicate requests",
                "Cancel requests on user action (e.g., search change)"
            ],
            "implementation": {
                "method": "AbortController",
                "example": """
// Request cancellation example
const controller = new AbortController();
fetch(url, { signal: controller.signal })
  .then(response => response.json())
  .catch(error => {
    if (error.name === 'AbortError') {
      console.log('Request cancelled');
    }
  });

// Cancel request
controller.abort();
"""
            }
        }
        
        return {
            "status": "success",
            "cancellation_config": cancellation_config,
            "message": "Request cancellation configuration retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting request cancellation config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting request cancellation config: {str(e)}"
        )

