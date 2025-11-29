"""
Logging Middleware (Task 50: Logging and Monitoring)
Provides request/response logging middleware
"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from utils.logging_config import RequestLogger

logger = logging.getLogger(__name__)
request_logger = RequestLogger(logger)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware (Task 50: Logging and Monitoring).
    Logs all API requests and responses for monitoring.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Skip logging for health checks and docs
        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]
        if request.url.path in skip_paths:
            response = await call_next(request)
            return response
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Log request
        start_time = time.time()
        method = request.method
        path = request.url.path
        
        # Get query parameters
        query_params = dict(request.query_params)
        
        request_logger.log_request(
            method=method,
            path=path,
            client_ip=client_ip,
            params=query_params
        )
        
        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            request_logger.log_response(
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms
            )
            
            # Add performance header
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            # Record response time for health dashboard (Task 60)
            try:
                from routers.health_dashboard import record_response_time
                record_response_time(duration_ms / 1000.0)  # Convert to seconds
            except ImportError:
                pass  # Health dashboard not available
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            request_logger.log_error(
                method=method,
                path=path,
                error=e
            )
            
            raise

