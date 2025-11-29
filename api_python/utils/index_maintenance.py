"""
Index Maintenance Utilities (Task 30)
Provides functions to analyze index usage, check for unused indexes, and maintain database indexes
"""
import logging
from sqlalchemy import text
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_index_usage_stats(session: AsyncSession, table_name: str = None) -> List[Dict[str, Any]]:
    """
    Get index usage statistics for tables
    
    Args:
        session: Database session
        table_name: Optional table name to filter by
    
    Returns:
        List of dictionaries with index information
    """
    try:
        if table_name:
            query = text("""
                SELECT 
                    TABLE_NAME,
                    INDEX_NAME,
                    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as columns,
                    NON_UNIQUE,
                    INDEX_TYPE
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table_name
                GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE, INDEX_TYPE
                ORDER BY TABLE_NAME, INDEX_NAME
            """)
            result = await session.execute(query, {"table_name": table_name})
        else:
            query = text("""
                SELECT 
                    TABLE_NAME,
                    INDEX_NAME,
                    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as columns,
                    NON_UNIQUE,
                    INDEX_TYPE
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME IN ('companies', 'stock_prices', 'financial_metrics', 'market_indices', 'sector_performance')
                GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE, INDEX_TYPE
                ORDER BY TABLE_NAME, INDEX_NAME
            """)
            result = await session.execute(query)
        
        indexes = []
        for row in result.fetchall():
            indexes.append({
                "table_name": row[0],
                "index_name": row[1],
                "columns": row[2],
                "non_unique": bool(row[3]),
                "index_type": row[4]
            })
        
        return indexes
    except Exception as e:
        logger.error(f"Error getting index usage stats: {e}")
        raise


async def analyze_query_execution_plan(session: AsyncSession, query: str, params: Dict = None) -> List[Dict[str, Any]]:
    """
    Analyze query execution plan using EXPLAIN
    
    Args:
        session: Database session
        query: SQL query to analyze
        params: Optional query parameters
    
    Returns:
        List of dictionaries with execution plan information
    """
    try:
        explain_query = text(f"EXPLAIN {query}")
        result = await session.execute(explain_query, params or {})
        
        plan = []
        for row in result.fetchall():
            plan.append({
                "id": row[0] if len(row) > 0 else None,
                "select_type": row[1] if len(row) > 1 else None,
                "table": row[2] if len(row) > 2 else None,
                "type": row[3] if len(row) > 3 else None,
                "possible_keys": row[4] if len(row) > 4 else None,
                "key": row[5] if len(row) > 5 else None,
                "key_len": row[6] if len(row) > 6 else None,
                "ref": row[7] if len(row) > 7 else None,
                "rows": row[8] if len(row) > 8 else None,
                "extra": row[9] if len(row) > 9 else None
            })
        
        return plan
    except Exception as e:
        logger.error(f"Error analyzing query execution plan: {e}")
        raise


async def check_unused_indexes(session: AsyncSession, table_name: str = None) -> List[Dict[str, Any]]:
    """
    Check for potentially unused indexes
    Note: This is a heuristic check - actual usage requires monitoring query logs
    
    Args:
        session: Database session
        table_name: Optional table name to filter by
    
    Returns:
        List of potentially unused indexes
    """
    try:
        # Get all indexes
        indexes = await get_index_usage_stats(session, table_name)
        
        # For now, we'll just return all indexes with a note that actual usage
        # requires monitoring query logs or using performance_schema
        unused_candidates = []
        
        for idx in indexes:
            # Heuristic: Single-column indexes that might be redundant
            if idx['index_type'] != 'FULLTEXT' and ',' not in idx['columns']:
                # Check if there's a composite index that covers this column
                composite_covering = False
                for other_idx in indexes:
                    if (other_idx['table_name'] == idx['table_name'] and 
                        other_idx['index_name'] != idx['index_name'] and
                        idx['columns'] in other_idx['columns']):
                        composite_covering = True
                        break
                
                if composite_covering:
                    unused_candidates.append({
                        "table_name": idx['table_name'],
                        "index_name": idx['index_name'],
                        "columns": idx['columns'],
                        "reason": "Potentially redundant - covered by composite index"
                    })
        
        return unused_candidates
    except Exception as e:
        logger.error(f"Error checking unused indexes: {e}")
        raise


async def analyze_table(session: AsyncSession, table_name: str) -> Dict[str, Any]:
    """
    Analyze table for query optimization
    
    Args:
        session: Database session
        table_name: Table name to analyze
    
    Returns:
        Dictionary with analysis results
    """
    try:
        # Run ANALYZE TABLE
        analyze_query = text(f"ANALYZE TABLE {table_name}")
        result = await session.execute(analyze_query)
        analyze_result = result.fetchall()
        
        # Get table statistics
        stats_query = text("""
            SELECT 
                TABLE_NAME,
                ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'Size (MB)',
                TABLE_ROWS
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
        """)
        stats_result = await session.execute(stats_query, {"table_name": table_name})
        stats = stats_result.fetchone()
        
        return {
            "table_name": table_name,
            "analyze_result": analyze_result[0] if analyze_result else None,
            "size_mb": float(stats[1]) if stats and stats[1] else 0,
            "estimated_rows": int(stats[2]) if stats and stats[2] else 0
        }
    except Exception as e:
        logger.error(f"Error analyzing table: {e}")
        raise


async def get_index_maintenance_report(session: AsyncSession) -> Dict[str, Any]:
    """
    Generate comprehensive index maintenance report
    
    Args:
        session: Database session
    
    Returns:
        Dictionary with maintenance report
    """
    try:
        report = {
            "indexes": [],
            "unused_candidates": [],
            "table_analysis": []
        }
        
        # Get all indexes
        report["indexes"] = await get_index_usage_stats(session)
        
        # Check for unused indexes
        report["unused_candidates"] = await check_unused_indexes(session)
        
        # Analyze main tables
        main_tables = ['companies', 'stock_prices', 'financial_metrics']
        for table in main_tables:
            try:
                analysis = await analyze_table(session, table)
                report["table_analysis"].append(analysis)
            except Exception as e:
                logger.warning(f"Could not analyze table {table}: {e}")
        
        return report
    except Exception as e:
        logger.error(f"Error generating maintenance report: {e}")
        raise

