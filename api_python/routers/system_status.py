"""
System Status & Monitoring Endpoints (Task 59: System Status & Monitoring)
Provides endpoints for system status, sync status, and monitoring
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Dict, Any
from datetime import datetime
import logging

from config.database import get_mysql_session
from models.database_models import Company, StockPrice, MarketIndex, SectorPerformance
from utils.startup_sync import sync_all_data, ENABLE_STARTUP_SYNC

router = APIRouter()
logger = logging.getLogger(__name__)

# Global sync status tracking (Task 59)
_sync_status: Dict[str, Any] = {
    "is_running": False,
    "last_sync": None,
    "last_sync_summary": None,
    "sync_history": []
}

def get_sync_status_global():
    """Get sync status from startup_sync module."""
    try:
        from utils.startup_sync import _sync_status_global
        return _sync_status_global
    except ImportError:
        return {"is_running": False, "last_sync": None, "last_sync_summary": None}


@router.get("/status/sync", response_model=dict)
async def get_sync_status(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get startup synchronization status (Task 59: System Status & Monitoring).
    Returns last sync timestamp, progress, and counts.
    """
    try:
        # db is already an AsyncSession from Depends(get_mysql_session)
        # FastAPI's Depends automatically handles the generator
        db_session = db
        
        # Get counts from database
        companies_result = await db_session.execute(
            select(func.count(Company.ticker)).where(Company.deleted_at.is_(None))
        )
        companies_count = companies_result.scalar() or 0
        
        stock_prices_result = await db_session.execute(
            select(func.count(StockPrice.id))
        )
        stock_prices_count = stock_prices_result.scalar() or 0
        
        indices_result = await db_session.execute(
            select(func.count(MarketIndex.id))
        )
        indices_count = indices_result.scalar() or 0
        
        sector_performance_result = await db_session.execute(
            select(func.count(SectorPerformance.id))
        )
        sector_performance_count = sector_performance_result.scalar() or 0
        
        # Get latest stock price date
        latest_price_result = await db_session.execute(
            select(func.max(StockPrice.date))
        )
        latest_price_date = latest_price_result.scalar()
        
        # Get sync status from startup_sync module
        global_sync = get_sync_status_global()
        
        return {
            "status": "success",
            "sync_status": {
                "is_running": global_sync.get("is_running", False) or _sync_status["is_running"],
                "is_enabled": ENABLE_STARTUP_SYNC,
                "last_sync": (global_sync.get("last_sync") or _sync_status["last_sync"]).isoformat() if (global_sync.get("last_sync") or _sync_status["last_sync"]) else None,
                "last_sync_summary": global_sync.get("last_sync_summary") or _sync_status["last_sync_summary"],
                "counts": {
                    "companies": companies_count,
                    "stock_prices": stock_prices_count,
                    "indices": indices_count,
                    "sector_performance": sector_performance_count
                },
                "latest_price_date": latest_price_date.isoformat() if latest_price_date else None
            },
            "message": "Sync status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sync status: {str(e)}"
        )


@router.post("/status/sync/trigger", response_model=dict)
async def trigger_manual_sync(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Trigger manual data synchronization (Task 59: System Status & Monitoring).
    Manually triggers the startup sync process.
    """
    global _sync_status
    
    try:
        if _sync_status["is_running"]:
            return {
                "status": "error",
                "message": "Sync is already running",
                "sync_status": _sync_status
            }
        
        # Mark as running
        _sync_status["is_running"] = True
        _sync_status["last_sync"] = datetime.now()
        
        try:
            # Run sync
            logger.info("Manual sync triggered")
            summary = await sync_all_data(db)
            
            # Update status
            _sync_status["last_sync_summary"] = summary
            _sync_status["sync_history"].append({
                "timestamp": datetime.now().isoformat(),
                "summary": summary
            })
            
            # Keep only last 10 syncs in history
            if len(_sync_status["sync_history"]) > 10:
                _sync_status["sync_history"] = _sync_status["sync_history"][-10:]
            
            return {
                "status": "success",
                "message": "Manual sync completed successfully",
                "summary": summary
            }
        finally:
            _sync_status["is_running"] = False
        
    except Exception as e:
        _sync_status["is_running"] = False
        logger.error(f"Error triggering manual sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering manual sync: {str(e)}"
        )


@router.get("/status/sync/history", response_model=dict)
async def get_sync_history():
    """
    Get synchronization history (Task 59: System Status & Monitoring).
    Returns history of sync operations.
    """
    try:
        return {
            "status": "success",
            "sync_history": _sync_status["sync_history"],
            "count": len(_sync_status["sync_history"]),
            "message": "Sync history retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sync history: {str(e)}"
        )


@router.get("/status/system", response_model=dict)
async def get_system_status(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get comprehensive system status (Task 59: System Status & Monitoring).
    Returns system health, sync status, and database statistics.
    """
    try:
        # db is already an AsyncSession from Depends(get_mysql_session)
        db_session = db
        
        # Database connection test
        db_status = "healthy"
        try:
            await db_session.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        # Get database statistics
        companies_result = await db_session.execute(
            select(func.count(Company.ticker)).where(Company.deleted_at.is_(None))
        )
        companies_count = companies_result.scalar() or 0
        
        stock_prices_result = await db_session.execute(
            select(func.count(StockPrice.id))
        )
        stock_prices_count = stock_prices_result.scalar() or 0
        
        # Get ticker counts
        ticker_counts_result = await db_session.execute(
            select(
                StockPrice.ticker,
                func.count(StockPrice.id).label("count")
            ).group_by(StockPrice.ticker).limit(10)
        )
        ticker_counts = [
            {"ticker": row[0], "count": row[1]}
            for row in ticker_counts_result.fetchall()
        ]
        
        # Get sync status from startup_sync module
        global_sync = get_sync_status_global()
        
        return {
            "status": "success",
            "system_status": {
                "database": {
                    "status": db_status,
                    "companies_count": companies_count,
                    "stock_prices_count": stock_prices_count
                },
                "sync": {
                    "is_running": global_sync.get("is_running", False) or _sync_status["is_running"],
                    "is_enabled": ENABLE_STARTUP_SYNC,
                    "last_sync": (global_sync.get("last_sync") or _sync_status["last_sync"]).isoformat() if (global_sync.get("last_sync") or _sync_status["last_sync"]) else None
                },
                "ticker_counts": ticker_counts,
                "timestamp": datetime.now().isoformat()
            },
            "message": "System status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system status: {str(e)}"
        )
