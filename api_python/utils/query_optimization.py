"""
Query Optimization Utilities (Task 46: Query Optimization)
Provides utilities to optimize database queries and avoid common pitfalls
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from sqlalchemy.orm import selectinload, joinedload

logger = logging.getLogger(__name__)


async def get_companies_with_prices_optimized(
    session: AsyncSession,
    ticker: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get companies with prices using optimized query (Task 46: Query Optimization).
    
    Avoids N+1 query problem by using JOIN instead of separate queries.
    
    Args:
        session: Database session
        ticker: Optional ticker filter
        limit: Maximum number of results
        offset: Offset for pagination
    
    Returns:
        List of companies with their latest prices
    """
    from models.database_models import Company, StockPrice
    
    # Optimized query: Single JOIN instead of N+1 queries
    query = select(
        Company.ticker,
        Company.company_name,
        Company.sector,
        StockPrice.date,
        StockPrice.close_price,
        StockPrice.volume
    ).select_from(
        Company.__table__.join(
            StockPrice.__table__,
            Company.ticker == StockPrice.ticker
        )
    ).where(
        Company.deleted_at.is_(None)
    )
    
    if ticker:
        query = query.where(Company.ticker == ticker.upper())
    
    # Get latest price for each company using subquery
    # This is more efficient than N+1 queries
    subquery = select(
        StockPrice.ticker,
        func.max(StockPrice.date).label('max_date')
    ).group_by(StockPrice.ticker).subquery()
    
    query = select(
        Company.ticker,
        Company.company_name,
        Company.sector,
        StockPrice.date,
        StockPrice.close_price,
        StockPrice.volume
    ).select_from(
        Company.__table__.join(
            StockPrice.__table__,
            Company.ticker == StockPrice.ticker
        ).join(
            subquery,
            (StockPrice.ticker == subquery.c.ticker) &
            (StockPrice.date == subquery.c.max_date)
        )
    ).where(
        Company.deleted_at.is_(None)
    )
    
    if ticker:
        query = query.where(Company.ticker == ticker.upper())
    
    query = query.limit(limit).offset(offset)
    
    result = await session.execute(query)
    rows = result.fetchall()
    
    # Group by company
    companies_dict = {}
    for row in rows:
        ticker_key = row[0]
        if ticker_key not in companies_dict:
            companies_dict[ticker_key] = {
                "ticker": row[0],
                "company_name": row[1],
                "sector": row[2],
                "latest_price": {
                    "date": str(row[3]),
                    "close_price": float(row[4]) if row[4] else None,
                    "volume": int(row[5]) if row[5] else None
                }
            }
    
    return list(companies_dict.values())


async def get_stock_prices_optimized(
    session: AsyncSession,
    ticker: str,
    limit: int = 100,
    offset: int = 0,
    columns: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get stock prices with optimized query (Task 46: Query Optimization).
    
    Uses pagination and selects only needed columns.
    
    Args:
        session: Database session
        ticker: Stock ticker symbol
        limit: Maximum number of results
        offset: Offset for pagination
        columns: List of columns to select (None = all)
    
    Returns:
        List of stock prices
    """
    from models.database_models import StockPrice
    
    # Select only needed columns (Task 46: Select only needed columns)
    if columns:
        selected_columns = []
        for col in columns:
            if hasattr(StockPrice, col):
                selected_columns.append(getattr(StockPrice, col))
        if not selected_columns:
            selected_columns = [StockPrice.ticker, StockPrice.date, StockPrice.close_price]
    else:
        # Default: select commonly used columns
        selected_columns = [
            StockPrice.ticker,
            StockPrice.date,
            StockPrice.open_price,
            StockPrice.high_price,
            StockPrice.low_price,
            StockPrice.close_price,
            StockPrice.volume
        ]
    
    query = select(*selected_columns).where(
        StockPrice.ticker == ticker.upper()
    ).order_by(
        StockPrice.date.desc()
    ).limit(limit).offset(offset)  # Task 46: Use pagination
    
    result = await session.execute(query)
    rows = result.fetchall()
    
    # Convert to dictionaries
    data = []
    for row in rows:
        row_dict = {}
        for i, col in enumerate(selected_columns):
            col_name = col.key if hasattr(col, 'key') else str(col)
            row_dict[col_name] = row[i]
        data.append(row_dict)
    
    return data


async def analyze_query_performance(
    session: AsyncSession,
    query_sql: str,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze query performance using EXPLAIN (Task 46: Query Optimization).
    
    Args:
        session: Database session
        query_sql: SQL query to analyze
        params: Query parameters
    
    Returns:
        Dictionary with query analysis results
    """
    try:
        # Use EXPLAIN to analyze query
        explain_query = f"EXPLAIN {query_sql}"
        result = await session.execute(text(explain_query), params or {})
        explain_rows = result.fetchall()
        
        # Parse EXPLAIN results
        analysis = {
            "query": query_sql,
            "explain_results": [],
            "summary": {
                "rows_examined": 0,
                "uses_index": False,
                "uses_full_scan": False
            }
        }
        
        for row in explain_rows:
            row_dict = {
                "select_type": row[1] if len(row) > 1 else None,
                "table": row[2] if len(row) > 2 else None,
                "type": row[3] if len(row) > 3 else None,
                "possible_keys": row[4] if len(row) > 4 else None,
                "key": row[5] if len(row) > 5 else None,
                "rows": row[8] if len(row) > 8 else None,
                "extra": row[9] if len(row) > 9 else None
            }
            analysis["explain_results"].append(row_dict)
            
            # Update summary
            if row_dict.get("rows"):
                try:
                    rows_value = int(row_dict["rows"]) if row_dict["rows"] else 0
                    analysis["summary"]["rows_examined"] += rows_value
                except (ValueError, TypeError):
                    pass
            if row_dict.get("key"):
                analysis["summary"]["uses_index"] = True
            if row_dict.get("type") == "ALL":
                analysis["summary"]["uses_full_scan"] = True
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        return {
            "query": query_sql,
            "error": str(e)
        }

