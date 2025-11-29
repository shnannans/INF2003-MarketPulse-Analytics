"""
Data Warehouse Endpoints (Tasks 40-41)
Provides endpoints for materialized views and ETL pipeline
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from config.database import get_mysql_session
from utils.etl_pipeline import (
    etl_stock_prices_to_warehouse,
    refresh_materialized_view,
    get_last_etl_timestamp
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/warehouse/materialized-view/sector-performance", response_model=dict)
async def get_sector_performance_materialized(
    sector: str = None,
    days: int = 30,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get sector performance from materialized view (Task 40: Materialized Views).
    
    This endpoint uses pre-calculated aggregations for fast dashboard loads.
    """
    try:
        query = text("""
            SELECT 
                sector,
                date,
                company_count,
                avg_price,
                total_volume,
                avg_change_pct,
                sector_high,
                sector_low,
                updated_at
            FROM mv_sector_daily_performance
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
        """)
        
        params = {"days": days}
        
        if sector:
            query = text("""
                SELECT 
                    sector,
                    date,
                    company_count,
                    avg_price,
                    total_volume,
                    avg_change_pct,
                    sector_high,
                    sector_low,
                    updated_at
                FROM mv_sector_daily_performance
                WHERE sector = :sector
                  AND date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
                ORDER BY date DESC
            """)
            params["sector"] = sector
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        data = []
        for row in rows:
            data.append({
                "sector": row[0],
                "date": str(row[1]),
                "company_count": row[2],
                "avg_price": float(row[3]) if row[3] else None,
                "total_volume": int(row[4]) if row[4] else None,
                "avg_change_pct": float(row[5]) if row[5] else None,
                "sector_high": float(row[6]) if row[6] else None,
                "sector_low": float(row[7]) if row[7] else None,
                "updated_at": str(row[8]) if row[8] else None
            })
        
        return {
            "status": "success",
            "data": data,
            "count": len(data),
            "message": "Sector performance from materialized view"
        }
        
    except Exception as e:
        logger.error(f"Error getting sector performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sector performance: {str(e)}"
        )


@router.post("/warehouse/etl/run", response_model=dict)
async def run_etl_pipeline(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Run ETL pipeline to load data into warehouse (Task 41: ETL Pipeline).
    
    Extract: Get new stock prices from operational DB
    Transform: Calculate metrics, join dimensions
    Load: Insert into data warehouse fact table
    """
    try:
        result = await etl_stock_prices_to_warehouse(db)
        
        return {
            "status": "success",
            "etl_result": result,
            "message": "ETL pipeline executed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error running ETL pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running ETL pipeline: {str(e)}"
        )


@router.post("/warehouse/materialized-view/refresh", response_model=dict)
async def refresh_materialized_view_endpoint(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Refresh materialized view (Task 40: Materialized Views).
    
    Recalculates and updates the materialized view with latest data.
    Should be run daily after market close.
    """
    try:
        result = await refresh_materialized_view(db)
        
        return {
            "status": "success",
            "refresh_result": result,
            "message": "Materialized view refreshed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error refreshing materialized view: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing materialized view: {str(e)}"
        )


@router.get("/warehouse/etl/status", response_model=dict)
async def get_etl_status(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get ETL pipeline status (Task 41: ETL Pipeline).
    
    Returns last run timestamp and status.
    """
    try:
        last_run = await get_last_etl_timestamp(db, "stock_prices")
        
        # Get status from tracking table
        result = await db.execute(
            text("SELECT status, records_processed, error_message FROM etl_tracking WHERE etl_type = 'stock_prices' ORDER BY last_run DESC LIMIT 1")
        )
        row = result.first()
        
        # Handle the case where no row exists or row has fewer columns than expected
        status_info = {
            "last_run": str(last_run) if last_run else None,
            "status": row[0] if row and len(row) > 0 else "unknown",
            "records_processed": row[1] if row and len(row) > 1 else 0,
            "error_message": row[2] if row and len(row) > 2 and row[2] else None
        }
        
        return {
            "status": "success",
            "etl_status": status_info,
            "message": "ETL status retrieved"
        }
        
    except Exception as e:
        logger.error(f"Error getting ETL status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting ETL status: {str(e)}"
        )


@router.get("/warehouse/olap/sector-time-analysis", response_model=dict)
async def get_olap_sector_time_analysis(
    year: int = None,
    quarter: int = None,
    sector: str = None,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    OLAP query: Analyze performance by sector and time period (Task 42: OLAP Queries).
    
    Multi-dimensional analysis using data warehouse fact and dimension tables.
    """
    try:
        # Build query with optional filters
        query = text("""
            SELECT 
                d.year,
                d.quarter,
                s.sector_name,
                COUNT(DISTINCT f.ticker_id) AS company_count,
                AVG(f.close_price) AS avg_price,
                SUM(f.volume) AS total_volume,
                AVG(f.price_change_pct) AS avg_change_pct
            FROM stock_price_facts f
            JOIN dim_date d ON f.date_id = d.date_id
            LEFT JOIN dim_sector s ON f.sector_id = s.sector_id
            WHERE f.deleted_at IS NULL
        """)
        
        params = {}
        conditions = []
        
        if year:
            conditions.append("d.year = :year")
            params["year"] = year
        
        if quarter:
            conditions.append("d.quarter = :quarter")
            params["quarter"] = quarter
        
        if sector:
            conditions.append("s.sector_name = :sector")
            params["sector"] = sector
        
        if conditions:
            query = text(str(query).replace("WHERE f.deleted_at IS NULL", 
                "WHERE f.deleted_at IS NULL AND " + " AND ".join(conditions)))
        
        query = text(str(query) + """
            GROUP BY d.year, d.quarter, s.sector_name
            ORDER BY d.year DESC, d.quarter DESC, s.sector_name
        """)
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        data = []
        for row in rows:
            data.append({
                "year": row[0],
                "quarter": row[1],
                "sector": row[2],
                "company_count": row[3],
                "avg_price": float(row[4]) if row[4] else None,
                "total_volume": int(row[5]) if row[5] else None,
                "avg_change_pct": float(row[6]) if row[6] else None
            })
        
        return {
            "status": "success",
            "data": data,
            "count": len(data),
            "filters": {
                "year": year,
                "quarter": quarter,
                "sector": sector
            },
            "message": "OLAP sector-time analysis"
        }
        
    except Exception as e:
        logger.error(f"Error executing OLAP query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing OLAP query: {str(e)}"
        )


@router.get("/warehouse/olap/trend-analysis", response_model=dict)
async def get_olap_trend_analysis(
    sector: str = None,
    start_year: int = None,
    end_year: int = None,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    OLAP query: Trend analysis by sector over time (Task 42: OLAP Queries).
    
    Year-over-year comparisons and trend identification.
    """
    try:
        query = text("""
            SELECT 
                d.year,
                s.sector_name,
                COUNT(DISTINCT f.ticker_id) AS company_count,
                AVG(f.close_price) AS avg_price,
                SUM(f.volume) AS total_volume,
                AVG(f.price_change_pct) AS avg_change_pct,
                MAX(f.high_price) AS max_price,
                MIN(f.low_price) AS min_price
            FROM stock_price_facts f
            JOIN dim_date d ON f.date_id = d.date_id
            LEFT JOIN dim_sector s ON f.sector_id = s.sector_id
            WHERE f.deleted_at IS NULL
        """)
        
        params = {}
        conditions = []
        
        if sector:
            conditions.append("s.sector_name = :sector")
            params["sector"] = sector
        
        if start_year:
            conditions.append("d.year >= :start_year")
            params["start_year"] = start_year
        
        if end_year:
            conditions.append("d.year <= :end_year")
            params["end_year"] = end_year
        
        if conditions:
            query = text(str(query).replace("WHERE f.deleted_at IS NULL", 
                "WHERE f.deleted_at IS NULL AND " + " AND ".join(conditions)))
        
        query = text(str(query) + """
            GROUP BY d.year, s.sector_name
            ORDER BY d.year DESC, s.sector_name
        """)
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        data = []
        for row in rows:
            data.append({
                "year": row[0],
                "sector": row[1],
                "company_count": row[2],
                "avg_price": float(row[3]) if row[3] else None,
                "total_volume": int(row[4]) if row[4] else None,
                "avg_change_pct": float(row[5]) if row[5] else None,
                "max_price": float(row[6]) if row[6] else None,
                "min_price": float(row[7]) if row[7] else None
            })
        
        return {
            "status": "success",
            "data": data,
            "count": len(data),
            "filters": {
                "sector": sector,
                "start_year": start_year,
                "end_year": end_year
            },
            "message": "OLAP trend analysis"
        }
        
    except Exception as e:
        logger.error(f"Error executing OLAP trend analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing OLAP trend analysis: {str(e)}"
        )


@router.get("/views/company-latest-price", response_model=dict)
async def get_company_latest_price_view(
    sector: str = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get latest company prices from view (Task 43: Database Views).
    
    Uses v_company_latest_price view for simplified querying.
    """
    try:
        query = text("""
            SELECT * FROM v_company_latest_price
        """)
        
        params = {}
        conditions = []
        
        if sector:
            conditions.append("sector = :sector")
            params["sector"] = sector
        
        if conditions:
            query = text(str(query) + " WHERE " + " AND ".join(conditions))
        
        query = text(str(query) + " ORDER BY latest_price DESC LIMIT :limit")
        params["limit"] = limit
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        data = []
        for row in rows:
            data.append({
                "ticker": row[0],
                "company_name": row[1],
                "sector": row[2],
                "latest_date": str(row[3]),
                "latest_price": float(row[4]) if row[4] else None,
                "latest_change": float(row[5]) if row[5] else None,
                "latest_volume": int(row[6]) if row[6] else None,
                "ma_5": float(row[7]) if row[7] else None,
                "ma_20": float(row[8]) if row[8] else None,
                "ma_50": float(row[9]) if row[9] else None,
                "ma_200": float(row[10]) if row[10] else None
            })
        
        return {
            "status": "success",
            "data": data,
            "count": len(data),
            "filters": {
                "sector": sector,
                "limit": limit
            },
            "message": "Latest company prices from view"
        }
        
    except Exception as e:
        logger.error(f"Error querying view: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying view: {str(e)}"
        )


@router.get("/views/company-performance", response_model=dict)
async def get_company_performance_view(
    sector: str = None,
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get company performance summary from view (Task 43: Database Views).
    
    Uses v_company_performance_summary view.
    """
    try:
        query = text("""
            SELECT * FROM v_company_performance_summary
        """)
        
        params = {}
        if sector:
            query = text(str(query) + " WHERE sector = :sector")
            params["sector"] = sector
        
        query = text(str(query) + " ORDER BY avg_price DESC")
        
        result = await db.execute(query, params)
        rows = result.fetchall()
        
        data = []
        for row in rows:
            data.append({
                "ticker": row[0],
                "company_name": row[1],
                "sector": row[2],
                "price_records_count": row[3],
                "first_date": str(row[4]) if row[4] else None,
                "last_date": str(row[5]) if row[5] else None,
                "avg_price": float(row[6]) if row[6] else None,
                "max_price": float(row[7]) if row[7] else None,
                "min_price": float(row[8]) if row[8] else None,
                "avg_volume": float(row[9]) if row[9] else None,
                "total_volume": int(row[10]) if row[10] else None
            })
        
        return {
            "status": "success",
            "data": data,
            "count": len(data),
            "filters": {
                "sector": sector
            },
            "message": "Company performance summary from view"
        }
        
    except Exception as e:
        logger.error(f"Error querying view: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying view: {str(e)}"
        )

