"""
User Management API endpoints
Handles user CRUD operations with soft delete support
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
import logging
from datetime import datetime
import bcrypt
import re

from config.database import get_mysql_session
from models.database_models import User
from models.pydantic_models import UserCreateRequest, UserResponse, UserUpdateRequest, PasswordChangeRequest, RoleChangeRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

router = APIRouter()
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength
    Returns: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    return True, None


@router.post("/users", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreateRequest,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Create a new user account.
    
    Creates a new user record in the database with hashed password.
    Username and email must be unique.
    Password is hashed before storage (never stored in plain text).
    
    Returns the created user (without password).
    """
    try:
        # Validate email format
        if not validate_email(request.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Validate password strength
        is_valid, error_msg = validate_password(request.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Validate role
        if request.role not in ["user", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be either 'user' or 'admin'"
            )
        
        # Check if username already exists
        existing_username = await db.execute(
            select(User).where(User.username == request.username).where(User.deleted_at.is_(None))
        )
        if existing_username.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{request.username}' already exists"
            )
        
        # Check if email already exists
        existing_email = await db.execute(
            select(User).where(User.email == request.email).where(User.deleted_at.is_(None))
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{request.email}' already exists"
            )
        
        # Hash password
        password_hash = hash_password(request.password)
        
        # Create user
        now = datetime.now()
        new_user = User(
            username=request.username,
            email=request.email,
            password_hash=password_hash,
            role=request.role,
            is_active=1,  # Active by default
            created_at=now,
            updated_at=None,
            deleted_at=None
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(f"Created new user: {new_user.username} (ID: {new_user.id}, Role: {new_user.role})")
        
        return {
            "message": f"User '{request.username}' created successfully",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "role": new_user.role,
                "is_active": bool(new_user.is_active),
                "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
                "updated_at": new_user.updated_at.isoformat() if new_user.updated_at else None,
                "deleted_at": None
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


@router.get("/users", response_model=dict)
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role (user/admin)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false)"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: Optional[int] = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    List all users with filtering and pagination.
    
    Returns list of users (excluding soft-deleted users).
    Excludes password from response.
    Supports filtering by role and active status.
    """
    try:
        # Build query - exclude soft-deleted users
        stmt = select(User).where(User.deleted_at.is_(None))
        
        # Apply filters
        if role:
            if role not in ["user", "admin"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role must be either 'user' or 'admin'"
                )
            stmt = stmt.where(User.role == role)
        
        if is_active is not None:
            stmt = stmt.where(User.is_active == (1 if is_active else 0))
        
        # Apply pagination
        stmt = stmt.order_by(User.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        # Convert to response format (exclude password)
        users_list = []
        for user in users:
            users_list.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "deleted_at": None  # Never return deleted_at for active users
            })
        
        # Get total count for pagination info
        count_stmt = select(func.count(User.id)).where(User.deleted_at.is_(None))
        if role:
            count_stmt = count_stmt.where(User.role == role)
        if is_active is not None:
            count_stmt = count_stmt.where(User.is_active == (1 if is_active else 0))
        
        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar()
        
        return {
            "users": users_list,
            "count": len(users_list),
            "total": total_count,
            "filters": {
                "role": role,
                "is_active": is_active,
                "limit": limit,
                "offset": offset
            },
            "pagination": {
                "offset": offset,
                "limit": limit,
                "has_more": (offset + len(users_list)) < total_count
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing users: {str(e)}"
        )


@router.get("/users/{user_id}", response_model=dict)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get user details by ID.
    
    Returns user details (excluding password).
    Returns 404 if user doesn't exist or is soft-deleted.
    """
    try:
        # Query user - exclude soft-deleted users
        stmt = select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
        
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "deleted_at": None  # Never return deleted_at for active users
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user: {str(e)}"
        )


@router.put("/users/{user_id}", response_model=dict)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Full update (PUT) - Replace entire user record (except password).
    
    Replaces ALL fields of the user with the provided values.
    Fields not provided will be set to null.
    Password is not updated via this endpoint (use separate password change endpoint).
    The user_id in the URL must match an existing user.
    
    Returns 404 if user does not exist or is soft-deleted.
    """
    try:
        # Check if user exists and is not soft-deleted
        stmt = select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Validate email format if provided
        if request.email is not None:
            if not validate_email(request.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email format"
                )
        
        # Validate role if provided
        if request.role is not None:
            if request.role not in ["user", "admin"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role must be either 'user' or 'admin'"
                )
        
        # Check for duplicate username if provided and different from current
        if request.username is not None and request.username != user.username:
            existing_username = await db.execute(
                select(User).where(User.username == request.username)
                .where(User.deleted_at.is_(None))
                .where(User.id != user_id)
            )
            if existing_username.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Username '{request.username}' already exists"
                )
        
        # Check for duplicate email if provided and different from current
        if request.email is not None and request.email != user.email:
            existing_email = await db.execute(
                select(User).where(User.email == request.email)
                .where(User.deleted_at.is_(None))
                .where(User.id != user_id)
            )
            if existing_email.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email '{request.email}' already exists"
                )
        
        # Update all fields (PUT behavior - replace entire record)
        # If a field is provided, update it; if None, keep existing value (for required fields)
        # This is safer than setting to null for required fields like username and email
        if request.username is not None:
            user.username = request.username
        
        if request.email is not None:
            user.email = request.email
        
        if request.role is not None:
            user.role = request.role
        
        if request.is_active is not None:
            user.is_active = 1 if request.is_active else 0
        
        # Update updated_at timestamp
        user.updated_at = datetime.now()
        
        # Note: password, id, created_at, and deleted_at are not updated
        # - password: use separate endpoint
        # - id: primary key, immutable
        # - created_at: immutable
        # - deleted_at: use DELETE endpoint for soft delete
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Updated user {user_id}: username={user.username}, email={user.email}, role={user.role}, is_active={user.is_active}")
        
        return {
            "message": f"User {user_id} updated successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "deleted_at": None
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )


@router.patch("/users/{user_id}", response_model=dict)
async def patch_user(
    user_id: int,
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Partial update (PATCH) - Update only provided fields of a user.
    
    Only updates the fields that are provided in the request.
    Fields not provided will remain unchanged.
    Password is not updated via this endpoint (use separate password change endpoint).
    The user_id in the URL must match an existing user.
    
    Returns 404 if user does not exist or is soft-deleted.
    """
    try:
        # Check if user exists and is not soft-deleted
        stmt = select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Prepare update data - only include non-None fields (PATCH behavior)
        update_data = {}
        updated_fields = []
        
        # Validate and collect fields to update
        if request.username is not None:
            # Check for duplicate username if different from current
            if request.username != user.username:
                existing_username = await db.execute(
                    select(User).where(User.username == request.username)
                    .where(User.deleted_at.is_(None))
                    .where(User.id != user_id)
                )
                if existing_username.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Username '{request.username}' already exists"
                    )
            user.username = request.username
            updated_fields.append("username")
        
        if request.email is not None:
            # Validate email format
            if not validate_email(request.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email format"
                )
            # Check for duplicate email if different from current
            if request.email != user.email:
                existing_email = await db.execute(
                    select(User).where(User.email == request.email)
                    .where(User.deleted_at.is_(None))
                    .where(User.id != user_id)
                )
                if existing_email.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Email '{request.email}' already exists"
                    )
            user.email = request.email
            updated_fields.append("email")
        
        if request.role is not None:
            # Validate role
            if request.role not in ["user", "admin"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role must be either 'user' or 'admin'"
                )
            user.role = request.role
            updated_fields.append("role")
        
        if request.is_active is not None:
            user.is_active = 1 if request.is_active else 0
            updated_fields.append("is_active")
        
        # Check if any fields were provided to update
        if not updated_fields:
            logger.info(f"No fields provided for update for user {user_id}")
            return {
                "message": f"No fields provided for update. User {user_id} unchanged.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "is_active": bool(user.is_active),
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                    "deleted_at": None
                },
                "status": "success"
            }
        
        # Update updated_at timestamp
        user.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Patched user {user_id}: updated fields={updated_fields}")
        
        return {
            "message": f"User {user_id} updated successfully",
            "updated_fields": updated_fields,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "deleted_at": None
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error patching user {user_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )


@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Soft delete a user.
    
    Marks the user as deleted by setting the `deleted_at` timestamp.
    The user record remains in the database but will be excluded from GET queries.
    User cannot log in after soft delete.
    
    Returns 404 if user does not exist or is already deleted.
    """
    try:
        # Check if user exists and is not soft-deleted
        stmt = select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Check if already deleted
        if user.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} is already deleted"
            )
        
        # Soft delete: set deleted_at timestamp
        user.deleted_at = datetime.now()
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Soft deleted user {user_id} at {user.deleted_at}")
        
        return {
            "message": f"User {user_id} has been soft deleted",
            "user_id": user_id,
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error soft deleting user {user_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )


@router.patch("/users/{user_id}/restore", response_model=dict)
async def restore_user(
    user_id: int,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Restore a soft-deleted user.
    
    Sets `deleted_at` to NULL, making the user account active again.
    User can log in again after restoration.
    
    Returns 404 if user does not exist or is not deleted.
    """
    try:
        # Check if user exists (including soft-deleted users)
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Check if user is actually deleted
        if user.deleted_at is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} is not deleted (already active)"
            )
        
        # Restore: set deleted_at to NULL
        user.deleted_at = None
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Restored user {user_id} (deleted_at set to NULL)")
        
        return {
            "message": f"User {user_id} has been restored",
            "user_id": user_id,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "deleted_at": None
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring user {user_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restoring user: {str(e)}"
        )


@router.patch("/users/{user_id}/password", response_model=dict)
async def change_user_password(
    user_id: int,
    request: PasswordChangeRequest,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Change user password.
    
    Validates current password (if provided) and updates to new password.
    New password is hashed before storage.
    
    Returns 404 if user does not exist or is soft-deleted.
    Returns 400 if current password is incorrect or new password is invalid.
    """
    try:
        # Check if user exists and is not soft-deleted
        stmt = select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Verify current password if provided
        if request.current_password:
            if not verify_password(request.current_password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
        # Note: For admin password resets, current_password can be omitted
        # This can be enhanced later with role-based permissions
        
        # Validate new password strength
        is_valid, error_msg = validate_password(request.new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Hash new password
        new_password_hash = hash_password(request.new_password)
        
        # Update password
        user.password_hash = new_password_hash
        user.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Password changed for user {user_id}")
        
        return {
            "message": f"Password for user {user_id} has been changed successfully",
            "user_id": user_id,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password for user {user_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}"
        )


@router.patch("/users/{user_id}/role", response_model=dict)
async def change_user_role(
    user_id: int,
    request: RoleChangeRequest,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Change user role.
    
    Updates the user's role to either 'user' or 'admin'.
    Changes permissions immediately.
    
    Returns 404 if user does not exist or is soft-deleted.
    Returns 400 if role is invalid.
    
    Note: In a production system, this should check if the requester is an admin
    and prevent users from changing their own role to prevent lockout.
    """
    try:
        # Validate role
        if request.role not in ["user", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be either 'user' or 'admin'"
            )
        
        # Check if user exists and is not soft-deleted
        stmt = select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Check if role is already the requested role
        if user.role == request.role:
            logger.info(f"User {user_id} already has role '{request.role}'")
            return {
                "message": f"User {user_id} already has role '{request.role}'",
                "user_id": user_id,
                "role": user.role,
                "status": "success"
            }
        
        # Store old role for logging
        old_role = user.role
        
        # Update role
        user.role = request.role
        user.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Changed role for user {user_id} from '{old_role}' to '{request.role}'")
        
        return {
            "message": f"Role for user {user_id} has been changed from '{old_role}' to '{request.role}'",
            "user_id": user_id,
            "old_role": old_role,
            "new_role": user.role,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "deleted_at": None
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing role for user {user_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing role: {str(e)}"
        )


@router.get("/admins", response_model=dict)
async def list_admins(
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false)"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: Optional[int] = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    List all admin users with filtering and pagination.
    
    Returns list of users with role="admin" (excluding soft-deleted admins).
    Excludes password from response.
    Supports filtering by active status.
    
    Note: In a production system, this should check if the requester is an admin.
    """
    try:
        # Build query - filter by role="admin" and exclude soft-deleted users
        stmt = select(User).where(User.role == "admin").where(User.deleted_at.is_(None))
        
        # Apply filters
        if is_active is not None:
            stmt = stmt.where(User.is_active == (1 if is_active else 0))
        
        # Apply pagination
        stmt = stmt.order_by(User.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(stmt)
        admins = result.scalars().all()
        
        # Convert to response format (exclude password)
        admins_list = []
        for admin in admins:
            admins_list.append({
                "id": admin.id,
                "username": admin.username,
                "email": admin.email,
                "role": admin.role,
                "is_active": bool(admin.is_active),
                "created_at": admin.created_at.isoformat() if admin.created_at else None,
                "updated_at": admin.updated_at.isoformat() if admin.updated_at else None,
                "deleted_at": None  # Never return deleted_at for active admins
            })
        
        # Get total count for pagination info
        count_stmt = select(func.count(User.id)).where(User.role == "admin").where(User.deleted_at.is_(None))
        if is_active is not None:
            count_stmt = count_stmt.where(User.is_active == (1 if is_active else 0))
        
        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar()
        
        return {
            "admins": admins_list,
            "count": len(admins_list),
            "total": total_count,
            "filters": {
                "is_active": is_active,
                "limit": limit,
                "offset": offset
            },
            "pagination": {
                "offset": offset,
                "limit": limit,
                "has_more": (offset + len(admins_list)) < total_count
            },
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error listing admins: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing admins: {str(e)}"
        )


@router.post("/admins", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_admin(
    request: UserCreateRequest,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Create a new admin account.
    
    Creates a new user with role="admin".
    Password is hashed before storage (never stored in plain text).
    Username and email must be unique.
    
    Note: The role in the request will be overridden to "admin".
    Note: In a production system, this should check if the requester is an admin.
    
    Returns the created admin (without password).
    """
    try:
        # Validate email format
        if not validate_email(request.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Validate password strength
        is_valid, error_msg = validate_password(request.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Force role to "admin" (override any role in request)
        admin_role = "admin"
        
        # Check if username already exists
        existing_username = await db.execute(
            select(User).where(User.username == request.username).where(User.deleted_at.is_(None))
        )
        if existing_username.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{request.username}' already exists"
            )
        
        # Check if email already exists
        existing_email = await db.execute(
            select(User).where(User.email == request.email).where(User.deleted_at.is_(None))
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{request.email}' already exists"
            )
        
        # Hash password
        password_hash = hash_password(request.password)
        
        # Create admin user
        now = datetime.now()
        new_admin = User(
            username=request.username,
            email=request.email,
            password_hash=password_hash,
            role=admin_role,  # Always set to "admin"
            is_active=1,  # Active by default
            created_at=now,
            updated_at=None,
            deleted_at=None
        )
        
        db.add(new_admin)
        await db.commit()
        await db.refresh(new_admin)
        
        logger.info(f"Created new admin: {new_admin.username} (ID: {new_admin.id}, Role: {new_admin.role})")
        
        return {
            "message": f"Admin '{request.username}' created successfully",
            "admin": {
                "id": new_admin.id,
                "username": new_admin.username,
                "email": new_admin.email,
                "role": new_admin.role,
                "is_active": bool(new_admin.is_active),
                "created_at": new_admin.created_at.isoformat() if new_admin.created_at else None,
                "updated_at": new_admin.updated_at.isoformat() if new_admin.updated_at else None,
                "deleted_at": None
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating admin: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating admin: {str(e)}"
        )


@router.patch("/admins/{user_id}/demote", response_model=dict)
async def demote_admin(
    user_id: int,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Demote an admin to regular user.
    
    Changes the user's role from "admin" to "user".
    User loses admin permissions immediately.
    
    Returns 404 if user does not exist or is soft-deleted.
    Returns 400 if user is not an admin.
    
    Note: In a production system, this should:
    - Check if the requester is an admin
    - Prevent users from demoting themselves
    - Ensure at least one admin remains in the system
    """
    try:
        # Check if user exists and is not soft-deleted
        stmt = select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Check if user is actually an admin
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with ID {user_id} is not an admin (current role: {user.role})"
            )
        
        # Store old role for logging
        old_role = user.role
        
        # Demote: change role from "admin" to "user"
        user.role = "user"
        user.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Demoted admin {user_id} from '{old_role}' to 'user'")
        
        return {
            "message": f"Admin {user_id} has been demoted to regular user",
            "user_id": user_id,
            "old_role": old_role,
            "new_role": user.role,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "deleted_at": None
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error demoting admin {user_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error demoting admin: {str(e)}"
        )


@router.patch("/admins/{user_id}/promote", response_model=dict)
async def promote_user(
    user_id: int,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Promote a regular user to admin.
    
    Changes the user's role from "user" to "admin".
    User gains admin permissions immediately.
    
    Returns 404 if user does not exist or is soft-deleted.
    Returns 400 if user is already an admin.
    
    Note: In a production system, this should check if the requester is an admin.
    """
    try:
        # Check if user exists and is not soft-deleted
        stmt = select(User).where(User.id == user_id).where(User.deleted_at.is_(None))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Check if user is already an admin
        if user.role == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with ID {user_id} is already an admin"
            )
        
        # Store old role for logging
        old_role = user.role
        
        # Promote: change role from "user" to "admin"
        user.role = "admin"
        user.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Promoted user {user_id} from '{old_role}' to 'admin'")
        
        return {
            "message": f"User {user_id} has been promoted to admin",
            "user_id": user_id,
            "old_role": old_role,
            "new_role": user.role,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": bool(user.is_active),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "deleted_at": None
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error promoting user {user_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error promoting user: {str(e)}"
        )

