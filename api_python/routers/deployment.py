"""
Deployment Endpoints (Task 52: Deployment Configuration)
Provides endpoints for deployment information and configuration
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import logging

from utils.deployment import DeploymentManager, create_env_example
from config.environment import config

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/deployment/info", response_model=Dict[str, Any])
async def get_deployment_info():
    """
    Get deployment information (Task 52: Deployment Configuration).
    Returns deployment status, dependencies, and configuration.
    """
    try:
        info = DeploymentManager.get_deployment_info()
        return {
            "status": "success",
            "deployment": info
        }
    except Exception as e:
        logger.error(f"Error getting deployment info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting deployment info: {str(e)}"
        )


@router.get("/deployment/validate", response_model=Dict[str, Any])
async def validate_deployment():
    """
    Validate deployment configuration (Task 52: Deployment Configuration).
    Checks dependencies, environment, and configuration.
    """
    try:
        is_valid, errors = DeploymentManager.validate_deployment_config()
        
        return {
            "status": "success",
            "is_valid": is_valid,
            "errors": errors,
            "message": "Deployment configuration is valid" if is_valid else "Deployment configuration has errors"
        }
    except Exception as e:
        logger.error(f"Error validating deployment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating deployment: {str(e)}"
        )


@router.get("/deployment/config", response_model=Dict[str, Any])
async def get_configuration():
    """
    Get current configuration (Task 53: Environment Management).
    Returns safe configuration summary (excludes secrets).
    """
    try:
        return {
            "status": "success",
            "config": config.get_config_summary(),
            "environment": config.ENVIRONMENT,
            "is_production": config.is_production(),
            "is_development": config.is_development()
        }
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting configuration: {str(e)}"
        )


@router.post("/deployment/create-env-example", response_model=Dict[str, Any])
async def create_env_example_endpoint():
    """
    Create .env.example file (Task 52: Deployment Configuration).
    Generates example environment file from current configuration.
    """
    try:
        success = create_env_example()
        
        if success:
            return {
                "status": "success",
                "message": ".env.example file created successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create .env.example file"
            )
    except Exception as e:
        logger.error(f"Error creating .env.example: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating .env.example: {str(e)}"
        )

