from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import logging

from config.database import get_mysql_session
from models.database_models import Company, FinancialMetrics, StockPrice
from models.pydantic_models import CompanyResponse, CompanyQuery, CompanyCreateRequest, CompanyUpdateRequest
from utils.error_handlers import handle_database_error
from utils.live_stock_service import get_company_info as get_live_company_info, YFINANCE_AVAILABLE
from utils.startup_sync import create_company_with_full_data
from utils.transaction_utils import update_with_lock, update_with_optimistic_locking, IsolationLevel, set_transaction_isolation_level, get_current_isolation_level

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/companies", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_company(
    request: CompanyCreateRequest,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Create a new company with automated data fetching from yfinance.
    
    Only the ticker is required. The system automatically fetches:
    - Company information (name, sector, market cap)
    - Financial metrics (PE ratio, dividend yield, beta)
    - Complete historical stock prices (from earliest available date to current)
    
    Returns the created company with summary of inserted records.
    """
    try:
        ticker = request.ticker.upper()
        
        # Check if company already exists
        existing_company = await db.execute(
            select(Company).where(Company.ticker == ticker)
        )
        if existing_company.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Company with ticker {ticker} already exists"
            )
        
        # Check if yfinance is available
        if not YFINANCE_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="yfinance service is not available"
            )
        
        # Create company with full data
        try:
            result = await create_company_with_full_data(db, ticker)
            
            return {
                "message": f"Company {ticker} created successfully",
                "company": result["company"],
                "financial_metrics": result["financial_metrics"],
                "stock_prices": result["stock_prices"],
                "summary": {
                    "stock_price_records_inserted": result["stock_prices"]["records_inserted"],
                    "date_range": result["stock_prices"]["date_range"]
                },
                "status": "success"
            }
            
        except ValueError as e:
            # Handle cases where ticker not found in yfinance
            error_msg = str(e)
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ticker {ticker} not found in yfinance"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Error fetching data from yfinance: {error_msg}"
                )
        except Exception as e:
            logger.error(f"Error creating company {ticker}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating company: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_company: {e}")
        handle_database_error(e)


@router.put("/companies/{ticker}", response_model=dict)
async def update_company(
    ticker: str,
    request: CompanyUpdateRequest,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Full update (PUT) - Replace entire company record.
    
    Replaces ALL fields of the company with the provided values.
    Fields not provided will be set to null.
    The ticker in the request body must match the URL parameter (or can be omitted).
    
    Returns 404 if company does not exist.
    """
    try:
        ticker = ticker.upper()
        
        # Validate that ticker in body matches URL parameter (if provided)
        if request.ticker and request.ticker.upper() != ticker:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticker in request body ({request.ticker}) must match URL parameter ({ticker})"
            )
        
        # Check if company exists and lock it for update (Task 33: Concurrent Update Protection)
        existing_company = await db.execute(
            select(Company)
            .where(Company.ticker == ticker)
            .where(Company.deleted_at.is_(None))
            .with_for_update()  # Lock row to prevent concurrent updates
        )
        company = existing_company.scalar_one_or_none()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker {ticker} not found"
            )
        
        # Update all fields (PUT behavior - replace entire record)
        # If a field is provided, update it; if None, set to None
        if request.company_name is not None:
            company.company_name = request.company_name
        else:
            company.company_name = None  # Set to null if not provided (PUT behavior)
        
        if request.sector is not None:
            company.sector = request.sector
        else:
            company.sector = None  # Set to null if not provided (PUT behavior)
        
        if request.market_cap is not None:
            company.market_cap = request.market_cap
        else:
            company.market_cap = None  # Set to null if not provided (PUT behavior)
        
        # Note: ticker and created_at are not updated (ticker is primary key, created_at is immutable)
        
        await db.commit()
        await db.refresh(company)
        
        logger.info(f"Updated company {ticker}: name={company.company_name}, sector={company.sector}, market_cap={company.market_cap}")
        
        return {
            "message": f"Company {ticker} updated successfully",
            "company": {
                "ticker": company.ticker,
                "company_name": company.company_name,
                "sector": company.sector,
                "market_cap": company.market_cap,
                "created_at": company.created_at.isoformat() if company.created_at else None
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating company {ticker}: {e}")
        await db.rollback()
        handle_database_error(e)


@router.patch("/companies/{ticker}", response_model=dict)
async def patch_company(
    ticker: str,
    request: CompanyUpdateRequest,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Partial update (PATCH) - Update only provided fields.
    
    Only updates the fields that are provided in the request.
    Fields not provided will remain unchanged.
    The ticker in the request body must match the URL parameter (or can be omitted).
    
    Returns 404 if company does not exist.
    """
    try:
        ticker = ticker.upper()
        
        # Validate that ticker in body matches URL parameter (if provided)
        if request.ticker and request.ticker.upper() != ticker:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ticker in request body ({request.ticker}) must match URL parameter ({ticker})"
            )
        
        # Check if company exists and lock it for update (Task 33: Concurrent Update Protection)
        existing_company = await db.execute(
            select(Company)
            .where(Company.ticker == ticker)
            .where(Company.deleted_at.is_(None))
            .with_for_update()  # Lock row to prevent concurrent updates
        )
        company = existing_company.scalar_one_or_none()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker {ticker} not found"
            )
        
        # Update only provided fields (PATCH behavior - partial update)
        # Only update fields that are explicitly provided (not None)
        updated_fields = []
        
        if request.company_name is not None:
            company.company_name = request.company_name
            updated_fields.append("company_name")
        
        if request.sector is not None:
            company.sector = request.sector
            updated_fields.append("sector")
        
        if request.market_cap is not None:
            company.market_cap = request.market_cap
            updated_fields.append("market_cap")
        
        # Note: ticker and created_at are not updated (ticker is primary key, created_at is immutable)
        
        if not updated_fields:
            # No fields were provided to update
            logger.info(f"No fields provided for update for company {ticker}")
            return {
                "message": f"No fields provided for update. Company {ticker} unchanged.",
                "company": {
                    "ticker": company.ticker,
                    "company_name": company.company_name,
                    "sector": company.sector,
                    "market_cap": company.market_cap,
                    "created_at": company.created_at.isoformat() if company.created_at else None
                },
                "status": "success"
            }
        
        await db.commit()
        await db.refresh(company)
        
        logger.info(f"Patched company {ticker}: updated fields={updated_fields}")
        
        return {
            "message": f"Company {ticker} updated successfully",
            "updated_fields": updated_fields,
            "company": {
                "ticker": company.ticker,
                "company_name": company.company_name,
                "sector": company.sector,
                "market_cap": company.market_cap,
                "created_at": company.created_at.isoformat() if company.created_at else None
            },
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error patching company {ticker}: {e}")
        await db.rollback()
        handle_database_error(e)


@router.delete("/companies/{ticker}", response_model=dict)
async def delete_company(
    ticker: str,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Soft delete a company.
    
    Marks the company as deleted by setting the `deleted_at` timestamp.
    The company record remains in the database but will be excluded from GET queries.
    Related data (stock_prices, financial_metrics) remains intact.
    
    Returns 404 if company does not exist or is already deleted.
    """
    try:
        from datetime import datetime
        
        ticker = ticker.upper()
        
        # Check if company exists and is not already deleted
        existing_company = await db.execute(
            select(Company).where(Company.ticker == ticker)
        )
        company = existing_company.scalar_one_or_none()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker {ticker} not found"
            )
        
        # Check if already deleted
        if company.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker {ticker} is already deleted"
            )
        
        # Soft delete: set deleted_at timestamp
        company.deleted_at = datetime.now()
        
        await db.commit()
        await db.refresh(company)
        
        logger.info(f"Soft deleted company {ticker} at {company.deleted_at}")
        
        return {
            "message": f"Company {ticker} has been soft deleted",
            "ticker": company.ticker,
            "deleted_at": company.deleted_at.isoformat() if company.deleted_at else None,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error soft deleting company {ticker}: {e}")
        await db.rollback()
        handle_database_error(e)


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

@router.get("/companies/{ticker}", response_model=dict)
async def get_company_by_ticker(
    ticker: str,
    live: Optional[bool] = Query(True, description="Use live data (True) or fallback to database (False)"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get detailed information for a specific company by ticker (REST-style endpoint).
    """
    return await get_company_info(ticker, live, db)

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
        ).where(Company.ticker == ticker).where(Company.deleted_at.is_(None))

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
        # Exclude soft-deleted companies
        stmt = stmt.where(Company.deleted_at.is_(None))
        
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