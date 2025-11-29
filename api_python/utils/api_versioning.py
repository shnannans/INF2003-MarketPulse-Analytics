"""
API Versioning Utilities (Task 54: API Versioning)
Provides utilities for API version management
"""
from typing import Optional
from fastapi import Request, HTTPException, status
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class APIVersion(str, Enum):
    """API Version enumeration (Task 54: API Versioning)."""
    V1 = "v1"
    V2 = "v2"
    LATEST = "v1"  # Current latest version


def get_api_version(request: Request) -> str:
    """
    Extract API version from request (Task 54: API Versioning).
    Checks Accept header, URL path, or query parameter.
    
    Args:
        request: FastAPI request object
    
    Returns:
        API version string (defaults to latest)
    """
    # Check URL path (e.g., /api/v1/companies)
    path = request.url.path
    if "/v1/" in path or path.startswith("/api/v1/"):
        return "v1"
    if "/v2/" in path or path.startswith("/api/v2/"):
        return "v2"
    
    # Check Accept header (e.g., application/vnd.marketpulse.v1+json)
    accept_header = request.headers.get("Accept", "")
    if "vnd.marketpulse.v1" in accept_header:
        return "v1"
    if "vnd.marketpulse.v2" in accept_header:
        return "v2"
    
    # Check query parameter (e.g., ?version=v1)
    version_param = request.query_params.get("version")
    if version_param:
        return version_param.lower()
    
    # Default to latest version
    return APIVersion.LATEST.value


def validate_api_version(version: str) -> bool:
    """
    Validate API version (Task 54: API Versioning).
    
    Args:
        version: Version string to validate
    
    Returns:
        True if version is valid
    """
    try:
        APIVersion(version.lower())
        return True
    except ValueError:
        return False


def get_versioned_response(data: dict, version: str) -> dict:
    """
    Get versioned response format (Task 54: API Versioning).
    Adapts response format based on API version.
    
    Args:
        data: Response data
        version: API version
    
    Returns:
        Versioned response dictionary
    """
    if version == "v1":
        return {
            "status": "success",
            "version": "v1",
            "data": data
        }
    elif version == "v2":
        return {
            "success": True,
            "api_version": "v2",
            "result": data,
            "meta": {
                "version": "v2",
                "format": "json"
            }
        }
    else:
        # Default to v1 format
        return {
            "status": "success",
            "version": APIVersion.LATEST.value,
            "data": data
        }


class VersionedRouter:
    """
    Versioned router helper (Task 54: API Versioning).
    Helps create versioned API routes.
    """
    
    @staticmethod
    def get_version_prefix(version: str) -> str:
        """Get version prefix for routes."""
        return f"/api/{version}"
    
    @staticmethod
    def create_versioned_route(base_path: str, version: str) -> str:
        """Create versioned route path."""
        if base_path.startswith("/"):
            base_path = base_path[1:]
        return f"/api/{version}/{base_path}"

