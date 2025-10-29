from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import logging

from config.database import get_mysql_session
from models.database_models import Company, FinancialMetrics, StockPrice
from models.pydantic_models import CompanyResponse, CompanyQuery
from utils.error_handlers import handle_database_error
from utils.live_stock_service import get_company_info as get_live_company_info

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/companies", response_model=dict)
async def get_companies_rest_style(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Maximum number of companies"),
    live: Optional[bool] = Query(True, description="Use live data (True) or fallback to database (False)"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get list of companies with financial metrics and stock data (REST-style endpoint).
    Now supports live company information fetching.
    """
    return await get_companies_internal(sector, limit, live, db)

@router.get("/company/{ticker}", response_model=dict)
async def get_company_info(
    ticker: str,
    live: Optional[bool] = Query(True, description="Use live data (True) or fallback to database (False)"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get detailed information for a specific company.
    """
    try:
        ticker = ticker.upper()

        if live:
            # Use live company info service
            logger.info(f"Fetching live company info for {ticker}")
            company_info = await get_live_company_info(ticker)

            if company_info:
                return {
                    "company": company_info,
                    "data_source": "yfinance_live",
                    "status": "success"
                }

        # Fallback to database
        logger.info(f"Using database fallback for company info: {ticker}")

        stmt = select(
            Company.ticker,
            Company.company_name,
            Company.sector,
            Company.market_cap,
            FinancialMetrics.pe_ratio,
            FinancialMetrics.dividend_yield,
            FinancialMetrics.beta
        ).select_from(
            Company.__table__.outerjoin(FinancialMetrics, Company.ticker == FinancialMetrics.ticker)
        ).where(Company.ticker == ticker)

        result = await db.execute(stmt)
        company_row = result.first()

        if not company_row:
            if live:
                # Return live service result if database fails
                company_info = await get_live_company_info(ticker)
                return {
                    "company": company_info,
                    "data_source": "yfinance_fallback",
                    "status": "success"
                }
            else:
                raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

        company_dict = {
            "ticker": company_row.ticker,
            "company_name": company_row.company_name,
            "sector": company_row.sector,
            "market_cap": company_row.market_cap,
            "pe_ratio": company_row.pe_ratio,
            "dividend_yield": company_row.dividend_yield,
            "beta": company_row.beta,
            "currency": "USD",  # Assuming USD for database entries
            "exchange": "UNKNOWN"  # Not stored in current schema
        }

        return {
            "company": company_dict,
            "data_source": "database",
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error fetching company info for {ticker}: {str(e)}")
        handle_database_error(e)

async def get_companies_internal(
    sector: Optional[str],
    limit: int,
    live: bool,
    db: AsyncSession
):
    """
    Internal function for companies listing with live and database fallback.
    """
    try:
        if live:
            # For live mode, get popular tickers and fetch their info
            popular_tickers = [
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX",
                "AMD", "INTC", "BABA", "DIS", "PYPL", "ADBE", "CRM", "ORCL",
                "IBM", "WMT", "JNJ", "PG", "KO", "PEP", "MCD", "NKE",
                "V", "MA", "JPM", "BAC", "GS", "MS"
            ][:limit]  # Limit to requested number

            logger.info(f"Fetching live company info for {len(popular_tickers)} companies")
            companies = []

            import asyncio
            # Fetch company info for popular tickers
            tasks = []
            for ticker in popular_tickers:
                task = get_live_company_info(ticker)
                tasks.append(task)

            # Execute in batches to avoid overwhelming the API
            batch_size = 10
            for i in range(0, len(tasks), batch_size):
                batch_tasks = tasks[i:i+batch_size]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                for ticker_idx, result in enumerate(batch_results):
                    if not isinstance(result, Exception) and result:
                        # Filter by sector if specified
                        if sector and result.get("sector", "").lower() != sector.lower():
                            continue
                        companies.append(result)

                # Small delay between batches
                if i + batch_size < len(tasks):
                    await asyncio.sleep(0.5)

            if companies:
                # Sort by market cap (descending)
                companies.sort(key=lambda x: x.get("market_cap", 0) or 0, reverse=True)
                logger.info(f"Live company service returned {len(companies)} companies")
                return {
                    "companies": companies,
                    "count": len(companies),
                    "filters": {
                        "sector": sector,
                        "limit": limit,
                        "live_mode": True
                    },
                    "data_source": "yfinance_live",
                    "status": "success"
                }
            else:
                logger.warning("Live company service failed, falling back to database")

        # Fallback to database if live fails or is disabled
        logger.info("Using database fallback for companies listing")

        # Build the query with joins - matching actual database schema
        stmt = select(
            Company.ticker,
            Company.company_name,
            Company.sector,
            Company.market_cap,
            FinancialMetrics.pe_ratio,
            FinancialMetrics.dividend_yield,
            FinancialMetrics.market_cap.label('current_market_cap'),
            FinancialMetrics.beta,
            func.count(StockPrice.id).label('price_records_count'),
            func.max(StockPrice.date).label('latest_price_date')
        ).select_from(
            Company.__table__.outerjoin(FinancialMetrics, Company.ticker == FinancialMetrics.ticker)
                              .outerjoin(StockPrice, Company.ticker == StockPrice.ticker)
        ).group_by(
            Company.id,
            Company.ticker,
            Company.company_name,
            Company.sector,
            Company.market_cap,
            FinancialMetrics.pe_ratio,
            FinancialMetrics.dividend_yield,
            FinancialMetrics.market_cap,
            FinancialMetrics.beta
        ).order_by(Company.market_cap.desc())

        # Apply filters
        if sector:
            stmt = stmt.where(Company.sector == sector)

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        companies_raw = result.fetchall()

        if not companies_raw and live:
            # If database also fails but live was attempted, try live service again
            return await get_companies_internal(sector, limit, True, db)

        # Convert to response format
        companies = []
        for row in companies_raw:
            company_dict = {
                "ticker": row.ticker,
                "company_name": row.company_name,
                "sector": row.sector,
                "market_cap": row.market_cap,
                "pe_ratio": row.pe_ratio,
                "dividend_yield": row.dividend_yield,
                "current_market_cap": row.current_market_cap,
                "beta": row.beta,
                "price_records_count": row.price_records_count or 0,
                "latest_price_date": row.latest_price_date,
                "currency": "USD",
                "exchange": "UNKNOWN"
            }
            companies.append(company_dict)

        return {
            "companies": companies,
            "count": len(companies),
            "filters": {
                "sector": sector,
                "limit": limit,
                "live_mode": live
            },
            "data_source": "database_fallback",
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error fetching companies: {str(e)}")
        handle_database_error(e)

# Keep the old function name for backward compatibility
get_companies = get_companies_internal