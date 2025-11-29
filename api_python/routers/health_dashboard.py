"""
Health Dashboard Endpoints (Task 60: System Status & Monitoring - Health Dashboard)
Enhanced health endpoint with comprehensive system monitoring
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Dict, Any
from datetime import datetime
import logging
import time
import psutil

from config.database import get_mysql_session, get_pool_status
from models.database_models import Company, StockPrice
from utils.cache_utils import get_cache_stats
from config import firestore as firestore_config

router = APIRouter()
logger = logging.getLogger(__name__)

# Track API response times
_response_times: list = []
_max_response_times = 100  # Keep last 100 response times


def record_response_time(response_time: float):
    """Record API response time for monitoring."""
    global _response_times
    _response_times.append(response_time)
    if len(_response_times) > _max_response_times:
        _response_times = _response_times[-_max_response_times:]


def get_average_response_time() -> float:
    """Get average API response time."""
    if not _response_times:
        return 0.0
    return sum(_response_times) / len(_response_times)


@router.get("/health/dashboard", response_model=dict)
async def get_health_dashboard(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Enhanced health dashboard endpoint (Task 60: System Status & Monitoring - Health Dashboard).
    Returns comprehensive system health information including:
    - Database connection status
    - Firestore connection status
    - API response times
    - Cache hit/miss rates
    - Connection pool status
    - Row counts per ticker
    - System metrics
    """
    start_time = time.time()
    
    try:
        db_session = db
        
        health_dashboard = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "metrics": {},
            "database": {},
            "cache": {},
            "pool": {},
            "system": {}
        }
        
        # Database connection status
        try:
            result = await db_session.execute(text("SELECT 1"))
            result.scalar()
            health_dashboard["database"]["status"] = "healthy"
            health_dashboard["database"]["message"] = "Database connection successful"
        except Exception as e:
            health_dashboard["database"]["status"] = "unhealthy"
            health_dashboard["database"]["message"] = str(e)
            health_dashboard["status"] = "degraded"
        
        # Firestore connection status
        try:
            firestore_status = await firestore_config.test_firestore_connection()
            health_dashboard["services"]["firestore"] = {
                "status": "healthy" if firestore_status else "unhealthy",
                "message": "Firestore connection successful" if firestore_status else "Firestore connection failed"
            }
            if not firestore_status:
                health_dashboard["status"] = "degraded"
        except Exception as e:
            health_dashboard["services"]["firestore"] = {
                "status": "unhealthy",
                "message": str(e)
            }
            health_dashboard["status"] = "degraded"
        
        # API response times
        avg_response_time = get_average_response_time()
        health_dashboard["metrics"]["api_response_times"] = {
            "average_ms": round(avg_response_time * 1000, 2),
            "samples": len(_response_times),
            "min_ms": round(min(_response_times) * 1000, 2) if _response_times else 0,
            "max_ms": round(max(_response_times) * 1000, 2) if _response_times else 0
        }
        
        # Cache hit/miss rates
        try:
            cache_stats = get_cache_stats()
            health_dashboard["cache"] = cache_stats
        except Exception as e:
            health_dashboard["cache"] = {
                "status": "error",
                "message": str(e)
            }
        
        # Connection pool status
        try:
            pool_status = get_pool_status()
            health_dashboard["pool"] = pool_status
        except Exception as e:
            health_dashboard["pool"] = {
                "status": "error",
                "message": str(e)
            }
        
        # Row counts per ticker
        try:
            ticker_counts_result = await db_session.execute(
                select(
                    StockPrice.ticker,
                    func.count(StockPrice.id).label("count")
                ).group_by(StockPrice.ticker).order_by(func.count(StockPrice.id).desc()).limit(20)
            )
            ticker_counts = [
                {"ticker": row[0], "count": row[1]}
                for row in ticker_counts_result.fetchall()
            ]
            health_dashboard["database"]["ticker_counts"] = ticker_counts
            health_dashboard["database"]["total_tickers"] = len(ticker_counts)
        except Exception as e:
            health_dashboard["database"]["ticker_counts"] = []
            health_dashboard["database"]["ticker_counts_error"] = str(e)
        
        # System metrics
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health_dashboard["system"] = {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count(),
                "memory": {
                    "total_gb": round(memory.total / (1024 * 1024 * 1024), 2),
                    "available_gb": round(memory.available / (1024 * 1024 * 1024), 2),
                    "percent": memory.percent,
                    "used_gb": round(memory.used / (1024 * 1024 * 1024), 2)
                },
                "disk": {
                    "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
                    "free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                    "percent": disk.percent,
                    "used_gb": round(disk.used / (1024 * 1024 * 1024), 2)
                }
            }
        except Exception as e:
            health_dashboard["system"] = {
                "status": "unhealthy",
                "message": str(e)
            }
            health_dashboard["status"] = "degraded"
        
        # Record this response time
        response_time = time.time() - start_time
        record_response_time(response_time)
        
        return health_dashboard
        
    except Exception as e:
        logger.error(f"Error in health dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health dashboard failed: {str(e)}"
        )


@router.get("/health", response_model=dict)
async def get_health_simple():
    """
    Simple health check endpoint (backward compatible).
    """
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

