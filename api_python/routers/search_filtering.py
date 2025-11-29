"""
Search & Filtering Enhancements (Task 61: Search & Filtering Enhancements)
Provides advanced search and filtering capabilities for companies
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging

from config.database import get_mysql_session
from models.database_models import Company, StockPrice, FinancialMetrics

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/companies/search", response_model=dict)
async def search_companies(
    search: str = Query(..., description="Search query for company names (full-text search)"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    market_cap_min: Optional[int] = Query(None, description="Minimum market cap"),
    market_cap_max: Optional[int] = Query(None, description="Maximum market cap"),
    price_min: Optional[float] = Query(None, description="Minimum stock price"),
    price_max: Optional[float] = Query(None, description="Maximum stock price"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Advanced search and filtering for companies (Task 61: Search & Filtering Enhancements).
    Supports full-text search, sector filtering, market cap range, price range, and date range.
    """
    try:
        db_session = db
        
        # Base query
        query = select(
            Company.ticker,
            Company.company_name,
            Company.sector,
            Company.market_cap,
            FinancialMetrics.pe_ratio,
            FinancialMetrics.dividend_yield,
            FinancialMetrics.beta
        ).select_from(
            Company.__table__.outerjoin(
                FinancialMetrics, Company.ticker == FinancialMetrics.ticker
            )
        ).where(Company.deleted_at.is_(None))
        
        # Full-text search for company names
        if search:
            # Try full-text search first (if full-text index exists)
            # Note: Full-text search requires FULLTEXT index on company_name
            # Fallback to LIKE if full-text index doesn't exist or search fails
            try:
                # Check if full-text index exists by attempting full-text search
                # If it fails, fall back to LIKE
                query = query.where(
                    text("MATCH(company_name) AGAINST(:search IN NATURAL LANGUAGE MODE)")
                ).params(search=search)
            except Exception as e:
                # Fallback to LIKE if full-text index doesn't exist
                logger.debug(f"Full-text search not available, using LIKE: {e}")
                query = query.where(
                    or_(
                        Company.company_name.like(f"%{search}%"),
                        Company.ticker.like(f"%{search.upper()}%")
                    )
                )
        
        # Sector filter
        if sector:
            query = query.where(Company.sector == sector)
        
        # Market cap range filter
        if market_cap_min is not None:
            query = query.where(Company.market_cap >= market_cap_min)
        if market_cap_max is not None:
            query = query.where(Company.market_cap <= market_cap_max)
        
        # Price range filter (using latest stock price)
        if price_min is not None or price_max is not None:
            # Get latest prices for each ticker
            latest_prices_subquery = select(
                StockPrice.ticker,
                func.max(StockPrice.date).label("latest_date")
            ).group_by(StockPrice.ticker).subquery()
            
            latest_prices = select(
                StockPrice.ticker,
                StockPrice.close_price
            ).select_from(
                StockPrice.__table__.join(
                    latest_prices_subquery,
                    and_(
                        StockPrice.ticker == latest_prices_subquery.c.ticker,
                        StockPrice.date == latest_prices_subquery.c.latest_date
                    )
                )
            ).subquery()
            
            query = query.join(
                latest_prices,
                Company.ticker == latest_prices.c.ticker
            )
            
            if price_min is not None:
                query = query.where(latest_prices.c.close_price >= price_min)
            if price_max is not None:
                query = query.where(latest_prices.c.close_price <= price_max)
        
        # Date range filter (using stock prices)
        if date_from or date_to:
            # Parse dates
            date_from_obj = None
            date_to_obj = None
            
            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid date_from format: {date_from}. Use YYYY-MM-DD"
                    )
            
            if date_to:
                try:
                    date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid date_to format: {date_to}. Use YYYY-MM-DD"
                    )
            
            # Filter by companies that have stock prices in the date range
            price_date_subquery = select(
                StockPrice.ticker
            ).where(
                and_(
                    (StockPrice.date >= date_from_obj) if date_from_obj else True,
                    (StockPrice.date <= date_to_obj) if date_to_obj else True
                )
            ).distinct().subquery()
            
            query = query.join(
                price_date_subquery,
                Company.ticker == price_date_subquery.c.ticker
            )
        
        # Apply limit
        query = query.limit(limit)
        
        # Execute query
        result = await db_session.execute(query)
        rows = result.fetchall()
        
        companies = []
        for row in rows:
            companies.append({
                "ticker": row.ticker,
                "company_name": row.company_name,
                "sector": row.sector,
                "market_cap": int(row.market_cap) if row.market_cap else None,
                "pe_ratio": float(row.pe_ratio) if row.pe_ratio else None,
                "dividend_yield": float(row.dividend_yield) if row.dividend_yield else None,
                "beta": float(row.beta) if row.beta else None
            })
        
        return {
            "status": "success",
            "count": len(companies),
            "companies": companies,
            "filters": {
                "search": search,
                "sector": sector,
                "market_cap_min": market_cap_min,
                "market_cap_max": market_cap_max,
                "price_min": price_min,
                "price_max": price_max,
                "date_from": date_from,
                "date_to": date_to
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in company search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in company search: {str(e)}"
        )


@router.get("/companies/autocomplete", response_model=dict)
async def autocomplete_companies(
    query: str = Query(..., min_length=1, description="Search query for autocomplete"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Autocomplete suggestions for company search (Task 61: Search & Filtering Enhancements).
    Returns matching company names and tickers for autocomplete functionality.
    """
    try:
        db_session = db
        
        # Search for companies matching the query
        search_query = select(
            Company.ticker,
            Company.company_name,
            Company.sector
        ).where(
            and_(
                Company.deleted_at.is_(None),
                or_(
                    Company.company_name.like(f"%{query}%"),
                    Company.ticker.like(f"%{query.upper()}%")
                )
            )
        ).limit(limit)
        
        result = await db_session.execute(search_query)
        rows = result.fetchall()
        
        suggestions = []
        for row in rows:
            suggestions.append({
                "ticker": row.ticker,
                "company_name": row.company_name,
                "sector": row.sector,
                "display": f"{row.company_name} ({row.ticker})"
            })
        
        return {
            "status": "success",
            "query": query,
            "suggestions": suggestions,
            "count": len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"Error in autocomplete: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in autocomplete: {str(e)}"
        )


@router.get("/companies/sectors", response_model=dict)
async def get_sectors(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get list of all sectors for filtering (Task 61: Search & Filtering Enhancements).
    """
    try:
        db_session = db
        
        sectors_query = select(
            Company.sector,
            func.count(Company.ticker).label("count")
        ).where(
            Company.deleted_at.is_(None)
        ).group_by(Company.sector).order_by(Company.sector)
        
        result = await db_session.execute(sectors_query)
        rows = result.fetchall()
        
        sectors = [
            {"sector": row.sector, "count": row.count}
            for row in rows
        ]
        
        return {
            "status": "success",
            "sectors": sectors,
            "count": len(sectors)
        }
        
    except Exception as e:
        logger.error(f"Error getting sectors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sectors: {str(e)}"
        )

