"""
Transaction Demo Endpoints (Tasks 34-35)
Demonstrates isolation levels and optimistic locking
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
import logging

from config.database import get_mysql_session
from models.database_models import Company
from utils.transaction_utils import (
    IsolationLevel,
    set_transaction_isolation_level,
    get_current_isolation_level,
    update_with_optimistic_locking
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/transaction/isolation-level", response_model=dict)
async def get_isolation_level(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get current transaction isolation level (Task 34).
    
    Returns the current isolation level for the database session.
    """
    try:
        level = await get_current_isolation_level(db)
        
        return {
            "status": "success",
            "isolation_level": level,
            "message": "Current transaction isolation level retrieved"
        }
    except Exception as e:
        logger.error(f"Error getting isolation level: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting isolation level: {str(e)}"
        )


@router.post("/transaction/set-isolation-level", response_model=dict)
async def set_isolation_level(
    level: str = Query(..., description="Isolation level: READ_UNCOMMITTED, READ_COMMITTED, REPEATABLE_READ, SERIALIZABLE"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Set transaction isolation level (Task 34).
    
    Use Cases:
        - READ_COMMITTED: Default, good for most cases
        - REPEATABLE_READ: For financial calculations that need consistency
        - SERIALIZABLE: Maximum isolation, but can cause deadlocks
    """
    try:
        # Map string to enum
        level_map = {
            "READ_UNCOMMITTED": IsolationLevel.READ_UNCOMMITTED,
            "READ_COMMITTED": IsolationLevel.READ_COMMITTED,
            "REPEATABLE_READ": IsolationLevel.REPEATABLE_READ,
            "SERIALIZABLE": IsolationLevel.SERIALIZABLE
        }
        
        if level.upper() not in level_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid isolation level. Must be one of: {', '.join(level_map.keys())}"
            )
        
        isolation_level = level_map[level.upper()]
        await set_transaction_isolation_level(db, isolation_level)
        
        return {
            "status": "success",
            "isolation_level": isolation_level.value,
            "message": f"Transaction isolation level set to {isolation_level.value}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting isolation level: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error setting isolation level: {str(e)}"
        )


@router.patch("/companies/{ticker}/optimistic", response_model=dict)
async def update_company_optimistic(
    ticker: str,
    company_name: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    market_cap: Optional[int] = Query(None),
    expected_version: int = Query(..., description="Expected version number for optimistic locking"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Update company with optimistic locking (Task 35).
    
    Uses version column to prevent conflicts. If version mismatch occurs,
    returns 409 Conflict error.
    
    This is useful for high-read, low-write scenarios where you want to
    reduce lock contention and improve performance.
    """
    try:
        ticker = ticker.upper()
        
        # Build update values
        update_values = {}
        if company_name is not None:
            update_values['company_name'] = company_name
        if sector is not None:
            update_values['sector'] = sector
        if market_cap is not None:
            update_values['market_cap'] = market_cap
        
        if not update_values:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field must be provided for update"
            )
        
        # Perform optimistic locking update
        result = await update_with_optimistic_locking(
            db,
            Company,
            {'ticker': ticker},
            update_values,
            expected_version,
            {'deleted_at': None}
        )
        
        if not result['success']:
            if result.get('error', '').startswith('Version mismatch'):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Version conflict: {result['error']}. Current version: {result.get('current_version')}"
                )
            elif result.get('error') == 'Record not found':
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Company with ticker {ticker} not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Update failed: {result.get('error')}"
                )
        
        # Commit transaction
        await db.commit()
        
        # Get updated company
        updated_company = await db.execute(
            select(Company).where(Company.ticker == ticker)
        )
        company = updated_company.scalar_one_or_none()
        
        logger.info(f"Updated company {ticker} with optimistic locking: version {expected_version} -> {result['current_version']}")
        
        return {
            "message": f"Company {ticker} updated successfully with optimistic locking",
            "company": {
                "ticker": company.ticker,
                "company_name": company.company_name,
                "sector": company.sector,
                "market_cap": company.market_cap,
                "version": company.version,
                "created_at": company.created_at.isoformat() if company.created_at else None
            },
            "status": "success",
            "version": result['current_version']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating company {ticker} with optimistic locking: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating company: {str(e)}"
        )

