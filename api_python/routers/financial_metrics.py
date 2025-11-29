"""
Financial Metrics Management Endpoints (Task 58: Financial Metrics Management)
Provides endpoints for managing financial metrics
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from decimal import Decimal
import logging

from config.database import get_mysql_session
from models.database_models import FinancialMetrics, Company

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/companies/{ticker}/metrics", response_model=dict)
async def get_financial_metrics(
    ticker: str,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get financial metrics for a company (Task 58: Financial Metrics Management).
    """
    try:
        async for db_session in db:
            # Check if company exists
            company_result = await db_session.execute(
                select(Company).where(
                    Company.ticker == ticker.upper(),
                    Company.deleted_at.is_(None)
                )
            )
            company = company_result.scalar_one_or_none()
            
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Company with ticker {ticker} not found"
                )
            
            # Get financial metrics
            result = await db_session.execute(
                select(FinancialMetrics).where(FinancialMetrics.ticker == ticker.upper())
            )
            metrics = result.scalar_one_or_none()
            
            if not metrics:
                return {
                    "status": "success",
                    "ticker": ticker.upper(),
                    "metrics": None,
                    "message": "No financial metrics found for this company"
                }
            
            return {
                "status": "success",
                "ticker": ticker.upper(),
                "metrics": {
                    "pe_ratio": float(metrics.pe_ratio) if metrics.pe_ratio else None,
                    "dividend_yield": float(metrics.dividend_yield) if metrics.dividend_yield else None,
                    "market_cap": int(metrics.market_cap) if metrics.market_cap else None,
                    "beta": float(metrics.beta) if metrics.beta else None,
                    "last_updated": metrics.last_updated.isoformat() if metrics.last_updated else None
                },
                "message": "Financial metrics retrieved successfully"
            }
            break
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting financial metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting financial metrics: {str(e)}"
        )


@router.patch("/companies/{ticker}/metrics", response_model=dict)
async def update_financial_metrics(
    ticker: str,
    pe_ratio: Optional[float] = Body(None, description="PE ratio"),
    dividend_yield: Optional[float] = Body(None, description="Dividend yield"),
    beta: Optional[float] = Body(None, description="Beta"),
    market_cap: Optional[int] = Body(None, description="Market cap"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Update financial metrics for a company (Task 58: Financial Metrics Management).
    Partial update - only provided fields will be updated.
    """
    try:
        async for db_session in db:
            # Check if company exists
            company_result = await db_session.execute(
                select(Company).where(
                    Company.ticker == ticker.upper(),
                    Company.deleted_at.is_(None)
                )
            )
            company = company_result.scalar_one_or_none()
            
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Company with ticker {ticker} not found"
                )
            
            # Get existing metrics or create new
            result = await db_session.execute(
                select(FinancialMetrics).where(FinancialMetrics.ticker == ticker.upper())
            )
            metrics = result.scalar_one_or_none()
            
            if not metrics:
                # Create new metrics record
                metrics = FinancialMetrics(
                    ticker=ticker.upper(),
                    pe_ratio=Decimal(str(pe_ratio)) if pe_ratio is not None else None,
                    dividend_yield=Decimal(str(dividend_yield)) if dividend_yield is not None else None,
                    beta=Decimal(str(beta)) if beta is not None else None,
                    market_cap=market_cap,
                    last_updated=datetime.now()
                )
                db_session.add(metrics)
                logger.info(f"Created new financial metrics for {ticker}")
            else:
                # Update existing metrics
                if pe_ratio is not None:
                    metrics.pe_ratio = Decimal(str(pe_ratio))
                if dividend_yield is not None:
                    metrics.dividend_yield = Decimal(str(dividend_yield))
                if beta is not None:
                    metrics.beta = Decimal(str(beta))
                if market_cap is not None:
                    metrics.market_cap = market_cap
                metrics.last_updated = datetime.now()
                logger.info(f"Updated financial metrics for {ticker}")
            
            await db_session.commit()
            
            return {
                "status": "success",
                "ticker": ticker.upper(),
                "metrics": {
                    "pe_ratio": float(metrics.pe_ratio) if metrics.pe_ratio else None,
                    "dividend_yield": float(metrics.dividend_yield) if metrics.dividend_yield else None,
                    "market_cap": int(metrics.market_cap) if metrics.market_cap else None,
                    "beta": float(metrics.beta) if metrics.beta else None,
                    "last_updated": metrics.last_updated.isoformat() if metrics.last_updated else None
                },
                "message": "Financial metrics updated successfully"
            }
            break
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating financial metrics: {e}")
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating financial metrics: {str(e)}"
        )


@router.get("/companies/{ticker}/metrics/history", response_model=dict)
async def get_financial_metrics_history(
    ticker: str,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get financial metrics update history (Task 58: Financial Metrics Management).
    Returns current metrics with last updated timestamp.
    """
    try:
        async for db_session in db:
            # Check if company exists
            company_result = await db_session.execute(
                select(Company).where(
                    Company.ticker == ticker.upper(),
                    Company.deleted_at.is_(None)
                )
            )
            company = company_result.scalar_one_or_none()
            
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Company with ticker {ticker} not found"
                )
            
            # Get financial metrics
            result = await db_session.execute(
                select(FinancialMetrics).where(FinancialMetrics.ticker == ticker.upper())
            )
            metrics = result.scalar_one_or_none()
            
            if not metrics:
                return {
                    "status": "success",
                    "ticker": ticker.upper(),
                    "history": [],
                    "message": "No financial metrics found"
                }
            
            return {
                "status": "success",
                "ticker": ticker.upper(),
                "current_metrics": {
                    "pe_ratio": float(metrics.pe_ratio) if metrics.pe_ratio else None,
                    "dividend_yield": float(metrics.dividend_yield) if metrics.dividend_yield else None,
                    "market_cap": int(metrics.market_cap) if metrics.market_cap else None,
                    "beta": float(metrics.beta) if metrics.beta else None,
                    "last_updated": metrics.last_updated.isoformat() if metrics.last_updated else None
                },
                "message": "Financial metrics history retrieved"
            }
            break
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting financial metrics history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting financial metrics history: {str(e)}"
        )

