"""
Rate Limiting Utilities (Task 49: API Rate Limiting)
Provides rate limiting functionality for API endpoints
"""
import time
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate Limiter for API endpoints (Task 49: API Rate Limiting).
    Uses in-memory storage (use Redis for distributed systems).
    """
    
    def __init__(self, requests_per_minute: int = 1000, requests_per_hour: int = 10000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests: Dict[str, list] = defaultdict(list)
        self.hour_requests: Dict[str, list] = defaultdict(list)
        self._cleanup_interval = 300  # Clean up old entries every 5 minutes
        self._last_cleanup = time.time()
    
    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory leaks."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        # Clean up minute requests older than 1 minute
        cutoff_minute = current_time - 60
        for key in list(self.minute_requests.keys()):
            self.minute_requests[key] = [
                ts for ts in self.minute_requests[key] if ts > cutoff_minute
            ]
            if not self.minute_requests[key]:
                del self.minute_requests[key]
        
        # Clean up hour requests older than 1 hour
        cutoff_hour = current_time - 3600
        for key in list(self.hour_requests.keys()):
            self.hour_requests[key] = [
                ts for ts in self.hour_requests[key] if ts > cutoff_hour
            ]
            if not self.hour_requests[key]:
                del self.hour_requests[key]
        
        self._last_cleanup = current_time
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for the client."""
        # Try to get IP from X-Forwarded-For header (for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Optionally include user ID if authenticated
        # user_id = getattr(request.state, "user_id", None)
        # if user_id:
        #     return f"{client_ip}:{user_id}"
        
        return client_ip
    
    def check_rate_limit(self, request: Request) -> tuple[bool, Optional[str]]:
        """
        Check if request is within rate limits.
        Returns (is_allowed, error_message).
        """
        self._cleanup_old_entries()
        
        client_id = self._get_client_identifier(request)
        current_time = time.time()
        
        # Check per-minute limit
        minute_requests = self.minute_requests[client_id]
        minute_requests = [ts for ts in minute_requests if ts > current_time - 60]
        self.minute_requests[client_id] = minute_requests
        
        if len(minute_requests) >= self.requests_per_minute:
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
        
        # Check per-hour limit
        hour_requests = self.hour_requests[client_id]
        hour_requests = [ts for ts in hour_requests if ts > current_time - 3600]
        self.hour_requests[client_id] = hour_requests
        
        if len(hour_requests) >= self.requests_per_hour:
            return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
        
        # Record this request
        minute_requests.append(current_time)
        hour_requests.append(current_time)
        
        return True, None
    
    def get_rate_limit_headers(self, request: Request) -> Dict[str, str]:
        """Get rate limit headers for response."""
        client_id = self._get_client_identifier(request)
        current_time = time.time()
        
        # Count remaining requests per minute
        minute_requests = [ts for ts in self.minute_requests[client_id] if ts > current_time - 60]
        remaining_minute = max(0, self.requests_per_minute - len(minute_requests))
        
        # Count remaining requests per hour
        hour_requests = [ts for ts in self.hour_requests[client_id] if ts > current_time - 3600]
        remaining_hour = max(0, self.requests_per_hour - len(hour_requests))
        
        return {
            "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
            "X-RateLimit-Remaining-Minute": str(remaining_minute),
            "X-RateLimit-Limit-Hour": str(self.requests_per_hour),
            "X-RateLimit-Remaining-Hour": str(remaining_hour),
            "X-RateLimit-Reset": str(int(current_time) + 60)  # Reset in 60 seconds
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate Limiting Middleware (Task 49: API Rate Limiting).
    """
    
    def __init__(self, app, requests_per_minute: int = 1000, requests_per_hour: int = 10000):
        super().__init__(app)
        self.rate_limiter = RateLimiter(requests_per_minute, requests_per_hour)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/health"]:
            response = await call_next(request)
            return response
        
        # Check rate limit
        is_allowed, error_message = self.rate_limiter.check_rate_limit(request)
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded: {error_message}")
            return Response(
                content=f'{{"detail": "{error_message}"}}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={
                    "Retry-After": "60",
                    **self.rate_limiter.get_rate_limit_headers(request)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        rate_limit_headers = self.rate_limiter.get_rate_limit_headers(request)
        for key, value in rate_limit_headers.items():
            response.headers[key] = value
        
        return response


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(requests_per_minute: int = 1000, requests_per_hour: int = 10000) -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(requests_per_minute, requests_per_hour)
    return _global_rate_limiter


def rate_limit_decorator(requests_per_minute: int = 1000, requests_per_hour: int = 10000):
    """
    Decorator for rate limiting specific endpoints (Task 49: API Rate Limiting).
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            rate_limiter = get_rate_limiter(requests_per_minute, requests_per_hour)
            is_allowed, error_message = rate_limiter.check_rate_limit(request)
            
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=error_message,
                    headers={"Retry-After": "60"}
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator

