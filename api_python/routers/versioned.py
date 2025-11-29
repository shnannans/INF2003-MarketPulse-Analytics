"""
Versioned API Endpoints (Task 54: API Versioning)
Provides versioned API endpoints for backward compatibility
"""
from fastapi import APIRouter, Depends, Request, Query
from typing import Optional
import logging

from utils.api_versioning import get_api_version, get_versioned_response, validate_api_version

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/version")
async def get_api_version_info(request: Request):
    """
    Get API version information (Task 54: API Versioning).
    Returns current API version and supported versions.
    """
    current_version = get_api_version(request)
    
    return get_versioned_response({
        "current_version": current_version,
        "supported_versions": ["v1", "v2"],
        "latest_version": "v1",
        "deprecation_policy": "Versions are supported for at least 12 months after a new version is released"
    }, current_version)


@router.get("/version/check")
async def check_api_version(
    version: Optional[str] = Query(None, description="API version to check")
):
    """
    Check if API version is valid (Task 54: API Versioning).
    """
    if not version:
        return {
            "status": "error",
            "message": "Version parameter is required"
        }
    
    is_valid = validate_api_version(version)
    
    return {
        "status": "success" if is_valid else "error",
        "version": version,
        "is_valid": is_valid,
        "message": "Version is valid" if is_valid else "Version is not supported"
    }

