"""
Notification System Endpoints (Task 74: Notification System)
Provides configuration and utilities for user notifications
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel
import logging

from config.database import get_mysql_session

router = APIRouter()
logger = logging.getLogger(__name__)


class NotificationCreateRequest(BaseModel):
    """Request model for creating a notification"""
    type: str  # success, error, warning, info
    title: str
    message: str
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    auto_dismiss: bool = True
    dismiss_duration_ms: Optional[int] = 5000


@router.get("/notifications/config", response_model=dict)
async def get_notifications_config(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get notification system configuration (Task 74: Notification System).
    Returns configuration for toast and in-app notifications.
    """
    try:
        notifications_config = {
            "toast_notifications": {
                "enabled": True,
                "types": ["success", "error", "warning", "info"],
                "position": "top-right",
                "auto_dismiss": True,
                "default_duration_ms": 5000,
                "max_notifications": 5,
                "stacking": True
            },
            "in_app_notifications": {
                "enabled": True,
                "types": ["system_alert", "data_sync", "permission_change", "account_update"],
                "storage": "session",
                "persist": False,
                "max_notifications": 50,
                "show_badge": True
            },
            "ui_features": {
                "non_intrusive": True,
                "auto_dismiss": True,
                "action_buttons": True,
                "notification_history": True,
                "sound_enabled": False,
                "desktop_notifications": False
            }
        }
        
        return {
            "status": "success",
            "notifications_config": notifications_config,
            "message": "Notification system configuration retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting notifications config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting notifications config: {str(e)}"
        )


@router.get("/notifications/toast-types", response_model=dict)
async def get_toast_notification_types(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get toast notification types and configurations (Task 74: Notification System).
    Returns configuration for different toast notification types.
    """
    try:
        toast_types = {
            "success": {
                "icon": "check-circle",
                "color": "green",
                "default_duration_ms": 3000,
                "auto_dismiss": True,
                "use_cases": [
                    "Operation completed successfully",
                    "Data saved",
                    "User created",
                    "Settings updated"
                ]
            },
            "error": {
                "icon": "error-circle",
                "color": "red",
                "default_duration_ms": 7000,
                "auto_dismiss": True,
                "use_cases": [
                    "Operation failed",
                    "Validation error",
                    "Network error",
                    "Server error"
                ]
            },
            "warning": {
                "icon": "warning",
                "color": "orange",
                "default_duration_ms": 5000,
                "auto_dismiss": True,
                "use_cases": [
                    "Warning message",
                    "Data may be stale",
                    "Action required",
                    "Deprecated feature"
                ]
            },
            "info": {
                "icon": "info",
                "color": "blue",
                "default_duration_ms": 4000,
                "auto_dismiss": True,
                "use_cases": [
                    "Information message",
                    "System update",
                    "Feature announcement",
                    "Helpful tip"
                ]
            }
        }
        
        return {
            "status": "success",
            "toast_types": toast_types,
            "message": "Toast notification types retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting toast notification types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting toast notification types: {str(e)}"
        )


@router.get("/notifications/in-app-types", response_model=dict)
async def get_in_app_notification_types(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get in-app notification types and configurations (Task 74: Notification System).
    Returns configuration for different in-app notification types.
    """
    try:
        in_app_types = {
            "system_alert": {
                "description": "System alerts and important announcements",
                "priority": "high",
                "show_badge": True,
                "persist_until_read": True,
                "use_cases": [
                    "System maintenance scheduled",
                    "Security alert",
                    "Service interruption",
                    "Important update"
                ]
            },
            "data_sync": {
                "description": "Data synchronization status updates",
                "priority": "medium",
                "show_badge": True,
                "persist_until_read": False,
                "use_cases": [
                    "Data sync completed",
                    "Data sync failed",
                    "Data sync in progress",
                    "New data available"
                ]
            },
            "permission_change": {
                "description": "Permission and role changes",
                "priority": "high",
                "show_badge": True,
                "persist_until_read": True,
                "use_cases": [
                    "Role changed",
                    "Permissions updated",
                    "Access granted",
                    "Access revoked"
                ]
            },
            "account_update": {
                "description": "Account and profile updates",
                "priority": "medium",
                "show_badge": True,
                "persist_until_read": False,
                "use_cases": [
                    "Profile updated",
                    "Password changed",
                    "Email verified",
                    "Account settings changed"
                ]
            }
        }
        
        return {
            "status": "success",
            "in_app_types": in_app_types,
            "message": "In-app notification types retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting in-app notification types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting in-app notification types: {str(e)}"
        )


@router.post("/notifications/create", response_model=dict)
async def create_notification(
    notification: NotificationCreateRequest,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Create a notification (Task 74: Notification System).
    Returns notification configuration for frontend display.
    """
    try:
        # Validate notification type
        valid_types = ["success", "error", "warning", "info"]
        if notification.type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid notification type. Must be one of: {', '.join(valid_types)}"
            )
        
        notification_data = {
            "id": f"notif_{datetime.now().timestamp()}",
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "timestamp": datetime.now().isoformat(),
            "auto_dismiss": notification.auto_dismiss,
            "dismiss_duration_ms": notification.dismiss_duration_ms or 5000,
            "action": {
                "url": notification.action_url,
                "text": notification.action_text
            } if notification.action_url else None
        }
        
        return {
            "status": "success",
            "notification": notification_data,
            "message": "Notification created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating notification: {str(e)}"
        )


@router.get("/notifications/best-practices", response_model=dict)
async def get_notification_best_practices(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get notification system best practices (Task 74: Notification System).
    Returns best practices and guidelines for notifications.
    """
    try:
        best_practices = {
            "toast_notifications": [
                "Keep messages concise and clear",
                "Use appropriate notification types (success, error, warning, info)",
                "Set appropriate auto-dismiss durations",
                "Limit the number of simultaneous notifications",
                "Provide action buttons for important notifications",
                "Use success notifications sparingly to avoid notification fatigue"
            ],
            "in_app_notifications": [
                "Show important system alerts prominently",
                "Persist critical notifications until read",
                "Use badges to indicate unread notifications",
                "Group related notifications",
                "Allow users to dismiss notifications",
                "Provide notification history for reference"
            ],
            "user_experience": [
                "Make notifications non-intrusive",
                "Allow users to control notification preferences",
                "Provide clear action buttons when needed",
                "Use consistent styling and positioning",
                "Test notifications on different screen sizes",
                "Consider accessibility (screen readers, keyboard navigation)"
            ],
            "performance": [
                "Limit notification history size",
                "Clean up old notifications regularly",
                "Use efficient notification rendering",
                "Avoid blocking UI with notification animations",
                "Consider lazy loading for notification history"
            ]
        }
        
        return {
            "status": "success",
            "best_practices": best_practices,
            "message": "Notification best practices retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting notification best practices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting notification best practices: {str(e)}"
        )

