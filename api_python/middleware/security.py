"""
Security Middleware (Task 48: Security Best Practices)
Provides security utilities and middleware for the API
"""
import logging
import re
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses (Task 48: Security Best Practices).
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy - Allow CDN resources and inline styles/scripts for frontend
        # This is necessary for Bootstrap, Google Fonts, Font Awesome, and inline styles in HTML files
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' http://localhost:* https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class SQLInjectionProtection:
    """
    SQL Injection Protection Utilities (Task 48: Security Best Practices).
    """
    
    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """
        Basic input sanitization to prevent SQL injection.
        Note: Parameterized queries are the primary defense.
        This is an additional layer.
        """
        if not isinstance(input_str, str):
            return str(input_str)
        
        # Remove or escape dangerous characters
        dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
        sanitized = input_str
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized.strip()
    
    @staticmethod
    def validate_ticker(ticker: str) -> bool:
        """
        Validate ticker symbol format.
        """
        if not ticker:
            return False
        
        # Ticker should be 1-10 uppercase alphanumeric characters
        pattern = r'^[A-Z0-9]{1,10}$'
        return bool(re.match(pattern, ticker.upper()))
    
    @staticmethod
    def validate_table_name(table_name: str) -> bool:
        """
        Validate table name to prevent SQL injection.
        """
        if not table_name:
            return False
        
        # Table name should only contain alphanumeric characters and underscores
        pattern = r'^[a-zA-Z0-9_]+$'
        return bool(re.match(pattern, table_name))
    
    @staticmethod
    def validate_column_name(column_name: str) -> bool:
        """
        Validate column name to prevent SQL injection.
        """
        if not column_name:
            return False
        
        # Column name should only contain alphanumeric characters and underscores
        pattern = r'^[a-zA-Z0-9_]+$'
        return bool(re.match(pattern, column_name))


class InputValidation:
    """
    Input Validation Utilities (Task 48: Security Best Practices).
    """
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format.
        """
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password_strength(password: str):
        """
        Validate password strength.
        Returns (is_valid, error_message).
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password must be less than 128 characters"
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        # Check for at least one digit
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, ""
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """
        Validate username format.
        """
        if not username:
            return False
        
        if len(username) < 3:
            return False
        
        if len(username) > 50:
            return False
        
        # Username should only contain alphanumeric characters, underscores, and hyphens
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def validate_date_format(date_str: str) -> bool:
        """
        Validate date format (YYYY-MM-DD).
        """
        if not date_str:
            return False
        
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False
        
        try:
            from datetime import datetime
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Basic Rate Limiting Middleware (Task 49: API Rate Limiting).
    Note: For production, use a more robust solution like Redis-based rate limiting.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In-memory store (use Redis in production)
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get current minute timestamp
        from datetime import datetime
        current_minute = datetime.now().strftime("%Y-%m-%d %H:%M")
        key = f"{client_ip}:{current_minute}"
        
        # Check rate limit
        if key in self.request_counts:
            if self.request_counts[key] >= self.requests_per_minute:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return Response(
                    content='{"detail": "Rate limit exceeded. Please try again later."}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json",
                    headers={"Retry-After": "60"}
                )
            self.request_counts[key] += 1
        else:
            # Reset counts for new minute
            self.request_counts = {key: 1}
        
        response = await call_next(request)
        return response

