"""
Performance Optimization Endpoints (Tasks 46-47)
Provides endpoints for query optimization and database maintenance
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List
import logging

from config.database import get_mysql_session
from utils.query_optimization import (
    get_companies_with_prices_optimized,
    get_stock_prices_optimized,
    analyze_query_performance
)
from utils.database_maintenance import (
    analyze_table,
    optimize_table,
    get_table_sizes,
    analyze_all_tables,
    optimize_all_tables
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/performance/companies-with-prices", response_model=dict)
async def get_companies_with_prices_optimized_endpoint(
    ticker: Optional[str] = Query(None, description="Stock ticker symbol (optional)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get companies with prices using optimized query (Task 46: Query Optimization).
    
    Avoids N+1 query problem by using JOIN instead of separate queries.
    Uses pagination for better performance.
    """
    try:
        companies = await get_companies_with_prices_optimized(db, ticker, limit, offset)
        
        return {
            "status": "success",
            "data": companies,
            "count": len(companies),
            "limit": limit,
            "offset": offset,
            "message": "Companies with prices (optimized query)"
        }
        
    except Exception as e:
        logger.error(f"Error getting companies with prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting companies with prices: {str(e)}"
        )


@router.get("/performance/stock-prices-optimized", response_model=dict)
async def get_stock_prices_optimized_endpoint(
    ticker: str = Query(..., description="Stock ticker symbol"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    columns: Optional[str] = Query(None, description="Comma-separated list of columns to select"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get stock prices with optimized query (Task 46: Query Optimization).
    
    Uses pagination and selects only needed columns for better performance.
    """
    try:
        column_list = None
        if columns:
            column_list = [col.strip() for col in columns.split(",")]
        
        prices = await get_stock_prices_optimized(db, ticker, limit, offset, column_list)
        
        return {
            "status": "success",
            "data": prices,
            "count": len(prices),
            "ticker": ticker.upper(),
            "limit": limit,
            "offset": offset,
            "columns": column_list if column_list else "default",
            "message": "Stock prices (optimized query)"
        }
        
    except Exception as e:
        logger.error(f"Error getting stock prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stock prices: {str(e)}"
        )


@router.post("/performance/analyze-query", response_model=dict)
async def analyze_query_performance_endpoint(
    query: str = Query(..., description="SQL query to analyze"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Analyze query performance using EXPLAIN (Task 46: Query Optimization).
    
    Returns query execution plan and performance metrics.
    """
    try:
        analysis = await analyze_query_performance(db, query)
        
        return {
            "status": "success",
            "analysis": analysis,
            "message": "Query performance analysis"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing query: {str(e)}"
        )


@router.post("/maintenance/analyze-table", response_model=dict)
async def analyze_table_endpoint(
    table_name: str = Query(..., description="Name of the table to analyze"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Analyze table for query optimization (Task 47: Database Maintenance).
    
    Updates table statistics to help query optimizer make better decisions.
    Should be run weekly.
    """
    try:
        result = await analyze_table(db, table_name)
        
        return {
            "status": "success",
            "result": result,
            "message": f"Table {table_name} analyzed"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing table: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing table: {str(e)}"
        )


@router.post("/maintenance/optimize-table", response_model=dict)
async def optimize_table_endpoint(
    table_name: str = Query(..., description="Name of the table to optimize"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Optimize table (defragment) (Task 47: Database Maintenance).
    
    Reorganizes table data and indexes to improve performance.
    Should be run monthly.
    """
    try:
        result = await optimize_table(db, table_name)
        
        return {
            "status": "success",
            "result": result,
            "message": f"Table {table_name} optimized"
        }
        
    except Exception as e:
        logger.error(f"Error optimizing table: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error optimizing table: {str(e)}"
        )


@router.get("/maintenance/table-sizes", response_model=dict)
async def get_table_sizes_endpoint(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get table sizes (Task 47: Database Maintenance).
    
    Returns size information for all tables in the database.
    """
    try:
        tables = await get_table_sizes(db)
        
        total_size = sum(t["size_mb"] for t in tables)
        
        return {
            "status": "success",
            "tables": tables,
            "count": len(tables),
            "total_size_mb": total_size,
            "message": "Table sizes retrieved"
        }
        
    except Exception as e:
        logger.error(f"Error getting table sizes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting table sizes: {str(e)}"
        )


@router.post("/maintenance/analyze-all", response_model=dict)
async def analyze_all_tables_endpoint(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Analyze all tables (Task 47: Database Maintenance).
    
    Analyzes all tables in the database for query optimization.
    Should be run weekly.
    """
    try:
        result = await analyze_all_tables(db)
        
        return {
            "status": "success",
            "result": result,
            "message": f"Analyzed {len(result['tables_analyzed'])} tables"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing all tables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing all tables: {str(e)}"
        )


@router.post("/maintenance/optimize-all", response_model=dict)
async def optimize_all_tables_endpoint(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Optimize all tables (Task 47: Database Maintenance).
    
    Optimizes all tables in the database.
    Should be run monthly.
    """
    try:
        result = await optimize_all_tables(db)
        
        return {
            "status": "success",
            "result": result,
            "message": f"Optimized {len(result['tables_optimized'])} tables"
        }
        
    except Exception as e:
        logger.error(f"Error optimizing all tables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error optimizing all tables: {str(e)}"
        )

