"""
Monitoring Endpoints (Task 50: Logging and Monitoring)
Provides endpoints for system monitoring and health checks
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any
import logging
import os
import psutil
from datetime import datetime
from pathlib import Path

from config.database import get_mysql_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/monitoring/health", response_model=dict)
async def health_check_detailed(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Detailed health check endpoint (Task 50: Logging and Monitoring).
    Returns comprehensive system health information.
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {}
        }
        
        # Database health
        try:
            async for db_session in db:
                result = await db_session.execute(text("SELECT 1"))
                result.scalar()
                health_status["services"]["database"] = {
                    "status": "healthy",
                    "message": "Database connection successful"
                }
                break
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "unhealthy",
                "message": str(e)
            }
            health_status["status"] = "degraded"
        
        # System resources
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health_status["services"]["system"] = {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024 * 1024 * 1024)
            }
        except Exception as e:
            health_status["services"]["system"] = {
                "status": "unhealthy",
                "message": str(e)
            }
            health_status["status"] = "degraded"
        
        # Log files
        try:
            log_dir = Path("logs")
            log_files = []
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    stat = log_file.stat()
                    log_files.append({
                        "name": log_file.name,
                        "size_mb": stat.st_size / (1024 * 1024),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            health_status["services"]["logging"] = {
                "status": "healthy",
                "log_files": log_files,
                "log_dir": str(log_dir.absolute())
            }
        except Exception as e:
            health_status["services"]["logging"] = {
                "status": "unhealthy",
                "message": str(e)
            }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/monitoring/metrics", response_model=dict)
async def get_metrics(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get system metrics (Task 50: Logging and Monitoring).
    Returns performance and resource metrics.
    """
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": {},
            "database": {},
            "application": {}
        }
        
        # System metrics
        try:
            metrics["system"] = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "cpu_count": psutil.cpu_count(),
                "memory": {
                    "total_gb": psutil.virtual_memory().total / (1024 * 1024 * 1024),
                    "available_gb": psutil.virtual_memory().available / (1024 * 1024 * 1024),
                    "percent": psutil.virtual_memory().percent,
                    "used_gb": psutil.virtual_memory().used / (1024 * 1024 * 1024)
                },
                "disk": {
                    "total_gb": psutil.disk_usage('/').total / (1024 * 1024 * 1024),
                    "free_gb": psutil.disk_usage('/').free / (1024 * 1024 * 1024),
                    "percent": psutil.disk_usage('/').percent,
                    "used_gb": psutil.disk_usage('/').used / (1024 * 1024 * 1024)
                }
            }
        except Exception as e:
            metrics["system"]["error"] = str(e)
        
        # Database metrics
        try:
            async for db_session in db:
                # Get connection pool stats
                result = await db_session.execute(text("""
                    SELECT 
                        VARIABLE_NAME,
                        VARIABLE_VALUE
                    FROM information_schema.GLOBAL_STATUS
                    WHERE VARIABLE_NAME IN (
                        'Threads_connected',
                        'Threads_running',
                        'Questions',
                        'Uptime'
                    )
                """))
                
                db_stats = {}
                for row in result.fetchall():
                    db_stats[row[0]] = row[1]
                
                metrics["database"] = {
                    "status": "connected",
                    "stats": db_stats
                }
                break
        except Exception as e:
            metrics["database"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Application metrics
        metrics["application"] = {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "python_version": os.sys.version,
            "log_level": logging.getLogger().level
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting metrics: {str(e)}"
        )


@router.get("/monitoring/logs", response_model=dict)
async def get_log_info():
    """
    Get log file information (Task 50: Logging and Monitoring).
    Returns information about log files.
    """
    try:
        log_dir = Path("logs")
        log_files = []
        
        if log_dir.exists():
            for log_file in sorted(log_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True):
                stat = log_file.stat()
                log_files.append({
                    "name": log_file.name,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": str(log_file.absolute())
                })
        
        return {
            "status": "success",
            "log_dir": str(log_dir.absolute()),
            "log_files": log_files,
            "count": len(log_files)
        }
        
    except Exception as e:
        logger.error(f"Error getting log info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting log info: {str(e)}"
        )

