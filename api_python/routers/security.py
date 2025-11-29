"""
Security Endpoints (Task 48: Security Best Practices)
Provides endpoints for security validation and testing
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
import logging

from middleware.security import SQLInjectionProtection, InputValidation

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/security/validate-ticker", response_model=dict)
async def validate_ticker(
    ticker: str = Query(..., description="Ticker symbol to validate")
):
    """
    Validate ticker symbol format (Task 48: Security Best Practices).
    """
    is_valid = SQLInjectionProtection.validate_ticker(ticker)
    
    return {
        "status": "success",
        "ticker": ticker.upper(),
        "is_valid": is_valid,
        "message": "Ticker is valid" if is_valid else "Ticker format is invalid"
    }


@router.post("/security/validate-email", response_model=dict)
async def validate_email(
    email: str = Query(..., description="Email address to validate")
):
    """
    Validate email format (Task 48: Security Best Practices).
    """
    is_valid = InputValidation.validate_email(email)
    
    return {
        "status": "success",
        "email": email,
        "is_valid": is_valid,
        "message": "Email is valid" if is_valid else "Email format is invalid"
    }


@router.post("/security/validate-password", response_model=dict)
async def validate_password(
    password: str = Query(..., description="Password to validate")
):
    """
    Validate password strength (Task 48: Security Best Practices).
    """
    is_valid, error_message = InputValidation.validate_password_strength(password)
    
    return {
        "status": "success",
        "is_valid": is_valid,
        "message": error_message if not is_valid else "Password meets strength requirements"
    }


@router.post("/security/validate-username", response_model=dict)
async def validate_username(
    username: str = Query(..., description="Username to validate")
):
    """
    Validate username format (Task 48: Security Best Practices).
    """
    is_valid = InputValidation.validate_username(username)
    
    return {
        "status": "success",
        "username": username,
        "is_valid": is_valid,
        "message": "Username is valid" if is_valid else "Username format is invalid"
    }


@router.post("/security/sanitize-input", response_model=dict)
async def sanitize_input(
    input_str: str = Query(..., description="Input string to sanitize")
):
    """
    Sanitize input to prevent SQL injection (Task 48: Security Best Practices).
    Note: This is a demonstration. Always use parameterized queries as the primary defense.
    """
    sanitized = SQLInjectionProtection.sanitize_input(input_str)
    
    return {
        "status": "success",
        "original": input_str,
        "sanitized": sanitized,
        "message": "Input sanitized (use parameterized queries as primary defense)"
    }


@router.get("/security/headers", response_model=dict)
async def get_security_headers():
    """
    Get information about security headers (Task 48: Security Best Practices).
    """
    return {
        "status": "success",
        "security_headers": {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        },
        "message": "Security headers are configured"
    }

