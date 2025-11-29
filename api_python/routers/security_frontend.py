"""
Frontend Security Endpoints (Task 71: Security Considerations)
Provides security configuration and utilities for frontend
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
import logging
import re

from config.database import get_mysql_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/security/config", response_model=dict)
async def get_security_config(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get frontend security configuration (Task 71: Security Considerations).
    Returns security settings and best practices.
    """
    try:
        security_config = {
            "input_validation": {
                "enabled": True,
                "client_side_validation": True,
                "server_side_validation": True,
                "xss_prevention": True,
                "csrf_protection": True,
                "sql_injection_prevention": True
            },
            "authentication": {
                "secure_token_storage": True,
                "token_storage_method": "httpOnly_cookies",  # Recommended over localStorage
                "token_refresh_enabled": True,
                "session_timeout_minutes": 30,
                "logout_on_inactivity": True,
                "inactivity_timeout_minutes": 15
            },
            "password": {
                "strength_indicator": True,
                "min_length": 8,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_special_chars": True,
                "password_history": 5  # Prevent reusing last 5 passwords
            },
            "form_security": {
                "secure_submission": True,
                "error_message_sanitization": True,
                "rate_limiting": True,
                "captcha_for_sensitive_forms": False
            },
            "security_headers": {
                "enabled": True,
                "headers": [
                    "X-Content-Type-Options: nosniff",
                    "X-Frame-Options: DENY",
                    "X-XSS-Protection: 1; mode=block",
                    "Strict-Transport-Security: max-age=31536000",
                    "Content-Security-Policy: default-src 'self'",
                    "Referrer-Policy: strict-origin-when-cross-origin",
                    "Permissions-Policy: geolocation=(), microphone=(), camera=()"
                ]
            }
        }
        
        return {
            "status": "success",
            "security_config": security_config,
            "message": "Security configuration retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting security config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting security config: {str(e)}"
        )


@router.post("/security/validate-password-strength", response_model=dict)
async def validate_password_strength(
    password: str = Query(..., description="Password to validate"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Validate password strength (Task 71: Security Considerations).
    Returns password strength analysis and recommendations.
    """
    try:
        strength_score = 0
        issues = []
        recommendations = []
        
        # Check length
        if len(password) >= 12:
            strength_score += 2
        elif len(password) >= 8:
            strength_score += 1
        else:
            issues.append("Password is too short (minimum 8 characters)")
            recommendations.append("Use at least 8 characters, preferably 12 or more")
        
        # Check for uppercase
        if re.search(r'[A-Z]', password):
            strength_score += 1
        else:
            issues.append("Missing uppercase letters")
            recommendations.append("Include at least one uppercase letter")
        
        # Check for lowercase
        if re.search(r'[a-z]', password):
            strength_score += 1
        else:
            issues.append("Missing lowercase letters")
            recommendations.append("Include at least one lowercase letter")
        
        # Check for numbers
        if re.search(r'[0-9]', password):
            strength_score += 1
        else:
            issues.append("Missing numbers")
            recommendations.append("Include at least one number")
        
        # Check for special characters
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            strength_score += 1
        else:
            issues.append("Missing special characters")
            recommendations.append("Include at least one special character (!@#$%^&*)")
        
        # Check for common patterns
        common_patterns = ['123', 'abc', 'password', 'qwerty', 'admin']
        if any(pattern.lower() in password.lower() for pattern in common_patterns):
            strength_score -= 1
            issues.append("Contains common patterns")
            recommendations.append("Avoid common patterns like '123' or 'password'")
        
        # Determine strength level
        if strength_score >= 5:
            strength_level = "strong"
        elif strength_score >= 3:
            strength_level = "medium"
        else:
            strength_level = "weak"
        
        return {
            "status": "success",
            "password_strength": {
                "strength_level": strength_level,
                "strength_score": strength_score,
                "max_score": 6,
                "is_valid": len(password) >= 8 and strength_score >= 3,
                "issues": issues,
                "recommendations": recommendations
            },
            "message": "Password strength validated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error validating password strength: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating password strength: {str(e)}"
        )


@router.post("/security/sanitize-input", response_model=dict)
async def sanitize_input(
    input_text: str = Query(..., description="Input text to sanitize"),
    input_type: Optional[str] = Query("text", description="Input type: text, html, url, email"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Sanitize user input (Task 71: Security Considerations).
    Returns sanitized input to prevent XSS and injection attacks.
    """
    try:
        import html
        
        sanitized = input_text
        
        if input_type == "html":
            # Basic HTML sanitization (remove script tags and dangerous attributes)
            import re
            # Remove script tags
            sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
            # Remove event handlers
            sanitized = re.sub(r'on\w+="[^"]*"', '', sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(r"on\w+='[^']*'", '', sanitized, flags=re.IGNORECASE)
        elif input_type == "url":
            # URL validation
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            if not url_pattern.match(sanitized):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid URL format"
                )
        elif input_type == "email":
            # Email validation
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_pattern.match(sanitized):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email format"
                )
        else:
            # Text sanitization - escape HTML entities
            sanitized = html.escape(sanitized)
        
        # Remove null bytes and control characters
        sanitized = sanitized.replace('\x00', '')
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\r\t')
        
        return {
            "status": "success",
            "input_type": input_type,
            "original": input_text,
            "sanitized": sanitized,
            "was_modified": sanitized != input_text,
            "message": "Input sanitized successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sanitizing input: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sanitizing input: {str(e)}"
        )


@router.get("/security/authentication-settings", response_model=dict)
async def get_authentication_settings(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get authentication security settings (Task 71: Security Considerations).
    Returns settings for secure token storage and session management.
    """
    try:
        auth_settings = {
            "token_storage": {
                "method": "httpOnly_cookies",
                "secure": True,
                "same_site": "strict",
                "http_only": True,
                "max_age_seconds": 3600  # 1 hour
            },
            "token_refresh": {
                "enabled": True,
                "refresh_threshold_seconds": 300,  # Refresh 5 minutes before expiry
                "refresh_endpoint": "/api/auth/refresh"
            },
            "session_management": {
                "timeout_minutes": 30,
                "inactivity_timeout_minutes": 15,
                "logout_on_inactivity": True,
                "logout_endpoint": "/api/auth/logout"
            },
            "security_practices": [
                "Use httpOnly cookies for token storage",
                "Implement automatic token refresh",
                "Logout on inactivity",
                "Clear tokens on logout",
                "Use HTTPS in production",
                "Implement CSRF protection"
            ]
        }
        
        return {
            "status": "success",
            "authentication_settings": auth_settings,
            "message": "Authentication settings retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting authentication settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting authentication settings: {str(e)}"
        )


@router.get("/security/validation-rules", response_model=dict)
async def get_validation_rules(
    field_type: Optional[str] = Query(None, description="Field type: email, password, ticker, username"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get input validation rules (Task 71: Security Considerations).
    Returns validation rules for different field types.
    """
    try:
        validation_rules = {
            "email": {
                "pattern": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                "min_length": 5,
                "max_length": 254,
                "required": True,
                "message": "Please enter a valid email address"
            },
            "password": {
                "pattern": r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>])[A-Za-z\d!@#$%^&*(),.?":{}|<>]{8,}$',
                "min_length": 8,
                "max_length": 128,
                "required": True,
                "message": "Password must be at least 8 characters with uppercase, lowercase, number, and special character"
            },
            "ticker": {
                "pattern": r'^[A-Z]{1,5}$',
                "min_length": 1,
                "max_length": 5,
                "required": True,
                "message": "Ticker must be 1-5 uppercase letters"
            },
            "username": {
                "pattern": r'^[a-zA-Z0-9_]{3,20}$',
                "min_length": 3,
                "max_length": 20,
                "required": True,
                "message": "Username must be 3-20 alphanumeric characters or underscores"
            }
        }
        
        if field_type and field_type.lower() in validation_rules:
            selected = {field_type.lower(): validation_rules[field_type.lower()]}
        else:
            selected = validation_rules
        
        return {
            "status": "success",
            "field_type": field_type,
            "validation_rules": selected,
            "message": "Validation rules retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting validation rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting validation rules: {str(e)}"
        )


@router.get("/security/security-headers", response_model=dict)
async def get_security_headers(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get security headers configuration (Task 71: Security Considerations).
    Returns security headers that should be set in responses.
    """
    try:
        security_headers = {
            "headers": {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:;",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
            },
            "descriptions": {
                "X-Content-Type-Options": "Prevents MIME type sniffing",
                "X-Frame-Options": "Prevents clickjacking attacks",
                "X-XSS-Protection": "Enables XSS filtering in browsers",
                "Strict-Transport-Security": "Forces HTTPS connections",
                "Content-Security-Policy": "Controls resource loading to prevent XSS",
                "Referrer-Policy": "Controls referrer information",
                "Permissions-Policy": "Controls browser features and APIs"
            }
        }
        
        return {
            "status": "success",
            "security_headers": security_headers,
            "message": "Security headers retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting security headers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting security headers: {str(e)}"
        )

