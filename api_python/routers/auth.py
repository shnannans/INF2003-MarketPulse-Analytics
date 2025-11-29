"""
Authentication endpoints (Task 48: User Authentication & Authorization System)
Handles login, logout, and token management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import Optional
import logging
from datetime import datetime, timedelta
import secrets

from config.database import get_mysql_session
from models.database_models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from routers.users import verify_password

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple token storage (in production, use Redis or database)
token_store = {}  # {token: {user_id, username, email, role, expires_at}}


class LoginRequest:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password


@router.post("/auth/login", response_model=dict)
async def login(
    request: dict = Body(...),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Authenticate user and return access token.
    
    Accepts email and password, verifies credentials, and returns:
    - access_token: Token for API authentication
    - refresh_token: Token for refreshing access token
    - user: User information
    - role: User role
    """
    try:
        email = request.get("email", "").strip()
        password = request.get("password", "")
        
        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )
        
        # Find user by email
        result = await db.execute(
            select(User).where(User.email == email).where(User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Verify password
        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Generate tokens (simple implementation - in production use JWT)
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        
        # Store token info (expires in 1 hour)
        expires_at = datetime.now() + timedelta(hours=1)
        token_store[access_token] = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "expires_at": expires_at
        }
        
        # Store refresh token (expires in 7 days)
        refresh_expires_at = datetime.now() + timedelta(days=7)
        token_store[refresh_token] = {
            "user_id": user.id,
            "type": "refresh",
            "expires_at": refresh_expires_at
        }
        
        logger.info(f"User {user.username} (ID: {user.id}) logged in successfully")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 3600,  # 1 hour in seconds
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active)
            },
            "role": user.role,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}"
        )


@router.post("/auth/refresh", response_model=dict)
async def refresh_token(
    request: dict = Body(...),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Refresh access token using refresh token.
    """
    try:
        refresh_token = request.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required"
            )
        
        # Check if refresh token exists and is valid
        token_info = token_store.get(refresh_token)
        if not token_info or token_info.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if token expired
        if datetime.now() > token_info.get("expires_at", datetime.now()):
            del token_store[refresh_token]
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        
        # Get user info
        user_id = token_info.get("user_id")
        result = await db.execute(
            select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new access token
        access_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)
        token_store[access_token] = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "expires_at": expires_at
        }
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 3600,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing token: {str(e)}"
        )


@router.post("/auth/logout", response_model=dict)
async def logout(
    request: dict = Body(...)
):
    """
    Logout user by invalidating tokens.
    """
    try:
        access_token = request.get("access_token")
        
        if access_token and access_token in token_store:
            del token_store[access_token]
        
        return {
            "message": "Logged out successfully",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during logout: {str(e)}"
        )


def get_current_user(token: str) -> Optional[dict]:
    """
    Get current user from token (for use in dependencies).
    """
    token_info = token_store.get(token)
    if not token_info:
        return None
    
    # Check if token expired
    if datetime.now() > token_info.get("expires_at", datetime.now()):
        del token_store[token]
        return None
    
    return token_info

