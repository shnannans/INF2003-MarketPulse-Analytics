"""
Database Maintenance Utilities (Task 47: Database Maintenance)
Provides utilities for database maintenance tasks
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def analyze_table(
    session: AsyncSession,
    table_name: str
) -> Dict[str, Any]:
    """
    Analyze table for query optimization (Task 47: Database Maintenance).
    
    Updates table statistics to help query optimizer make better decisions.
    
    Args:
        session: Database session
        table_name: Name of the table to analyze
    
    Returns:
        Dictionary with analysis results
    """
    try:
        await session.execute(text(f"ANALYZE TABLE {table_name}"))
        await session.commit()
        
        logger.info(f"Table {table_name} analyzed successfully")
        
        return {
            "status": "success",
            "table": table_name,
            "message": f"Table {table_name} analyzed successfully"
        }
    except Exception as e:
        logger.error(f"Error analyzing table {table_name}: {e}")
        await session.rollback()
        return {
            "status": "error",
            "table": table_name,
            "error": str(e)
        }


async def optimize_table(
    session: AsyncSession,
    table_name: str
) -> Dict[str, Any]:
    """
    Optimize table (defragment) (Task 47: Database Maintenance).
    
    Reorganizes table data and indexes to improve performance.
    
    Args:
        session: Database session
        table_name: Name of the table to optimize
    
    Returns:
        Dictionary with optimization results
    """
    try:
        await session.execute(text(f"OPTIMIZE TABLE {table_name}"))
        await session.commit()
        
        logger.info(f"Table {table_name} optimized successfully")
        
        return {
            "status": "success",
            "table": table_name,
            "message": f"Table {table_name} optimized successfully"
        }
    except Exception as e:
        logger.error(f"Error optimizing table {table_name}: {e}")
        await session.rollback()
        return {
            "status": "error",
            "table": table_name,
            "error": str(e)
        }


async def get_table_sizes(
    session: AsyncSession,
    database_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get table sizes (Task 47: Database Maintenance).
    
    Returns size information for all tables in the database.
    
    Args:
        session: Database session
        database_name: Database name (defaults to current database)
    
    Returns:
        List of dictionaries with table size information
    """
    try:
        if not database_name:
            # Get current database name
            result = await session.execute(text("SELECT DATABASE()"))
            database_name = result.scalar()
        
        query = text("""
            SELECT 
                TABLE_NAME,
                ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'Size_MB',
                ROUND((DATA_LENGTH / 1024 / 1024), 2) AS 'Data_MB',
                ROUND((INDEX_LENGTH / 1024 / 1024), 2) AS 'Index_MB',
                TABLE_ROWS
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = :db_name
            ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC
        """)
        
        result = await session.execute(query, {"db_name": database_name})
        rows = result.fetchall()
        
        tables = []
        for row in rows:
            tables.append({
                "table_name": row[0],
                "size_mb": float(row[1]) if row[1] else 0,
                "data_mb": float(row[2]) if row[2] else 0,
                "index_mb": float(row[3]) if row[3] else 0,
                "table_rows": int(row[4]) if row[4] else 0
            })
        
        return tables
        
    except Exception as e:
        logger.error(f"Error getting table sizes: {e}")
        return []


async def analyze_all_tables(
    session: AsyncSession,
    table_names: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Analyze multiple tables (Task 47: Database Maintenance).
    
    Args:
        session: Database session
        table_names: List of table names (None = analyze all tables)
    
    Returns:
        Dictionary with analysis results for all tables
    """
    results = {
        "status": "success",
        "tables_analyzed": [],
        "errors": []
    }
    
    if not table_names:
        # Get all table names
        result = await session.execute(text("""
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_TYPE = 'BASE TABLE'
        """))
        table_names = [row[0] for row in result.fetchall()]
    
    for table_name in table_names:
        result = await analyze_table(session, table_name)
        if result["status"] == "success":
            results["tables_analyzed"].append(table_name)
        else:
            results["errors"].append({
                "table": table_name,
                "error": result.get("error", "Unknown error")
            })
    
    return results


async def optimize_all_tables(
    session: AsyncSession,
    table_names: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Optimize multiple tables (Task 47: Database Maintenance).
    
    Args:
        session: Database session
        table_names: List of table names (None = optimize all tables)
    
    Returns:
        Dictionary with optimization results for all tables
    """
    results = {
        "status": "success",
        "tables_optimized": [],
        "errors": []
    }
    
    if not table_names:
        # Get all table names
        result = await session.execute(text("""
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_TYPE = 'BASE TABLE'
        """))
        table_names = [row[0] for row in result.fetchall()]
    
    for table_name in table_names:
        result = await optimize_table(session, table_name)
        if result["status"] == "success":
            results["tables_optimized"].append(table_name)
        else:
            results["errors"].append({
                "table": table_name,
                "error": result.get("error", "Unknown error")
            })
    
    return results

