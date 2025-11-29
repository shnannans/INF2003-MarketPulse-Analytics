"""
Transaction Utilities (Tasks 32-35)
Provides functions for batch updates with savepoints, concurrent update protection,
isolation levels, and optimistic locking
"""
import logging
from typing import List, Dict, Any, Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, update
from sqlalchemy.orm import selectinload
from enum import Enum

logger = logging.getLogger(__name__)


class IsolationLevel(Enum):
    """Transaction isolation levels (Task 34)"""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


async def set_transaction_isolation_level(
    session: AsyncSession,
    isolation_level: IsolationLevel
) -> None:
    """
    Set transaction isolation level (Task 34).
    
    Args:
        session: Database session
        isolation_level: Isolation level to set
    
    Use Cases:
        - READ COMMITTED: Default, good for most cases
        - REPEATABLE READ: For financial calculations that need consistency
        - SERIALIZABLE: Maximum isolation, but can cause deadlocks
    """
    try:
        await session.execute(
            text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level.value}")
        )
        logger.info(f"Transaction isolation level set to: {isolation_level.value}")
    except Exception as e:
        logger.error(f"Error setting isolation level: {e}")
        raise


async def get_current_isolation_level(session: AsyncSession) -> Optional[str]:
    """
    Get current transaction isolation level.
    
    Args:
        session: Database session
    
    Returns:
        Current isolation level or None
    """
    try:
        result = await session.execute(
            text("SELECT @@transaction_isolation")
        )
        level = result.scalar()
        return level
    except Exception as e:
        logger.error(f"Error getting isolation level: {e}")
        return None


async def batch_update_with_savepoint(
    session: AsyncSession,
    updates: List[Dict[str, Any]],
    savepoint_name: str = "before_update",
    on_error: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Perform batch updates with savepoint support for partial rollback.
    
    Args:
        session: Database session
        updates: List of update dictionaries, each containing:
            - 'table': Table name
            - 'where': WHERE clause conditions (dict)
            - 'values': Values to update (dict)
        savepoint_name: Name for the savepoint
        on_error: Optional callback function to call on error
    
    Returns:
        Dictionary with results:
            - 'success': Boolean
            - 'updated_count': Number of records updated
            - 'errors': List of errors
    """
    result = {
        "success": False,
        "updated_count": 0,
        "errors": []
    }
    
    try:
        # Create savepoint
        await session.execute(text(f"SAVEPOINT {savepoint_name}"))
        logger.info(f"Created savepoint: {savepoint_name}")
        
        # Perform updates
        for i, update_item in enumerate(updates):
            try:
                table = update_item['table']
                where_clause = update_item.get('where', {})
                values = update_item.get('values', {})
                
                # Build UPDATE query
                set_clause = ", ".join([f"{k} = :{k}" for k in values.keys()])
                where_clause_sql = " AND ".join([f"{k} = :where_{k}" for k in where_clause.keys()])
                
                # Combine parameters
                params = {**values}
                for k, v in where_clause.items():
                    params[f"where_{k}"] = v
                
                query = text(f"""
                    UPDATE {table}
                    SET {set_clause}
                    WHERE {where_clause_sql}
                """)
                
                result_query = await session.execute(query, params)
                updated = result_query.rowcount
                result["updated_count"] += updated
                
                logger.info(f"Updated {updated} rows in {table} (update {i+1}/{len(updates)})")
                
            except Exception as e:
                error_msg = f"Error in update {i+1}: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
                
                # Rollback to savepoint
                await session.execute(text(f"ROLLBACK TO SAVEPOINT {savepoint_name}"))
                logger.info(f"Rolled back to savepoint: {savepoint_name}")
                
                if on_error:
                    on_error(i, e)
                
                return result
        
        # All updates successful
        await session.commit()
        result["success"] = True
        logger.info(f"Batch update completed successfully: {result['updated_count']} rows updated")
        
    except Exception as e:
        logger.error(f"Error in batch update: {e}")
        result["errors"].append(str(e))
        
        # Rollback to savepoint
        try:
            await session.execute(text(f"ROLLBACK TO SAVEPOINT {savepoint_name}"))
            logger.info(f"Rolled back to savepoint: {savepoint_name}")
        except Exception as rollback_error:
            logger.error(f"Error rolling back to savepoint: {rollback_error}")
            await session.rollback()
    
    return result


async def update_with_lock(
    session: AsyncSession,
    model_class,
    identifier: Dict[str, Any],
    update_values: Dict[str, Any],
    additional_filters: Optional[Dict[str, Any]] = None
) -> Optional[Any]:
    """
    Update a record with row-level locking (SELECT FOR UPDATE).
    Prevents concurrent updates and race conditions.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        identifier: Dictionary of identifier fields (e.g., {'ticker': 'AAPL'})
        update_values: Dictionary of values to update
        additional_filters: Optional additional filters (e.g., {'deleted_at': None})
    
    Returns:
        Updated model instance or None if not found
    """
    try:
        # Start transaction (if not already in one)
        # Build query with FOR UPDATE lock
        query = select(model_class)
        
        # Add identifier filters
        for key, value in identifier.items():
            query = query.where(getattr(model_class, key) == value)
        
        # Add additional filters
        if additional_filters:
            for key, value in additional_filters.items():
                attr = getattr(model_class, key)
                if value is None:
                    query = query.where(attr.is_(None))
                else:
                    query = query.where(attr == value)
        
        # Lock the row for update
        query = query.with_for_update()
        
        # Execute query to lock row
        result = await session.execute(query)
        instance = result.scalar_one_or_none()
        
        if not instance:
            logger.warning(f"Record not found for update: {identifier}")
            return None
        
        # Update the instance
        for key, value in update_values.items():
            setattr(instance, key, value)
        
        # Flush to apply changes (but don't commit yet - caller should commit)
        await session.flush()
        
        logger.info(f"Updated record with lock: {identifier}")
        return instance
        
    except Exception as e:
        logger.error(f"Error in update_with_lock: {e}")
        await session.rollback()
        raise


async def update_with_optimistic_locking(
    session: AsyncSession,
    model_class,
    identifier: Dict[str, Any],
    update_values: Dict[str, Any],
    expected_version: int,
    additional_filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Update a record with optimistic locking using version column (Task 35).
    Prevents conflicts by checking version before update.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class (must have 'version' column)
        identifier: Dictionary of identifier fields (e.g., {'ticker': 'AAPL'})
        update_values: Dictionary of values to update
        expected_version: Expected version number (must match current version)
        additional_filters: Optional additional filters (e.g., {'deleted_at': None})
    
    Returns:
        Dictionary with:
            - 'success': Boolean indicating if update succeeded
            - 'updated': Boolean indicating if row was updated
            - 'current_version': Current version of the record (if found)
            - 'error': Error message if update failed
    
    Raises:
        HTTPException(409) if version mismatch (conflict)
    """
    try:
        # Build query to get current version
        query = select(model_class)
        
        # Add identifier filters
        for key, value in identifier.items():
            query = query.where(getattr(model_class, key) == value)
        
        # Add additional filters
        if additional_filters:
            for key, value in additional_filters.items():
                attr = getattr(model_class, key)
                if value is None:
                    query = query.where(attr.is_(None))
                else:
                    query = query.where(attr == value)
        
        # Get current record
        result = await session.execute(query)
        instance = result.scalar_one_or_none()
        
        if not instance:
            return {
                'success': False,
                'updated': False,
                'current_version': None,
                'error': 'Record not found'
            }
        
        current_version = getattr(instance, 'version', None)
        
        # Check version match
        if current_version != expected_version:
            return {
                'success': False,
                'updated': False,
                'current_version': current_version,
                'error': f'Version mismatch: expected {expected_version}, got {current_version}'
            }
        
        # Build update query with version increment
        update_query = update(model_class)
        
        # Add identifier filters
        for key, value in identifier.items():
            update_query = update_query.where(getattr(model_class, key) == value)
        
        # Add version check
        update_query = update_query.where(getattr(model_class, 'version') == expected_version)
        
        # Add additional filters
        if additional_filters:
            for key, value in additional_filters.items():
                attr = getattr(model_class, key)
                if value is None:
                    update_query = update_query.where(attr.is_(None))
                else:
                    update_query = update_query.where(attr == value)
        
        # Add version increment to update values
        update_values_with_version = {**update_values}
        update_values_with_version['version'] = getattr(model_class, 'version') + 1
        
        # Execute update
        update_query = update_query.values(**update_values_with_version)
        result = await session.execute(update_query)
        
        if result.rowcount == 0:
            # Version mismatch or record not found
            return {
                'success': False,
                'updated': False,
                'current_version': current_version,
                'error': 'Update failed: version mismatch or record not found'
            }
        
        # Flush to apply changes (but don't commit yet - caller should commit)
        await session.flush()
        
        logger.info(f"Updated record with optimistic locking: {identifier}, version {expected_version} -> {expected_version + 1}")
        
        return {
            'success': True,
            'updated': True,
            'current_version': expected_version + 1,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error in update_with_optimistic_locking: {e}")
        await session.rollback()
        return {
            'success': False,
            'updated': False,
            'current_version': None,
            'error': str(e)
        }


async def batch_update_stock_prices_with_savepoint(
    session: AsyncSession,
    ticker: str,
    price_updates: List[Dict[str, Any]],
    savepoint_name: str = "before_price_update"
) -> Dict[str, Any]:
    """
    Convenience function for batch updating stock prices with savepoint.
    
    Args:
        session: Database session
        ticker: Stock ticker symbol
        price_updates: List of price update dictionaries, each containing:
            - 'date': Date string or date object
            - 'close_price': Optional close price
            - 'volume': Optional volume
            - Other price fields as needed
        savepoint_name: Name for the savepoint
    
    Returns:
        Dictionary with results
    """
    updates = []
    
    for price_update in price_updates:
        date = price_update.get('date')
        if not date:
            continue
        
        # Build update values
        values = {}
        for key in ['close_price', 'open_price', 'high_price', 'low_price', 'volume']:
            if key in price_update:
                values[key] = price_update[key]
        
        if not values:
            continue
        
        updates.append({
            'table': 'stock_prices',
            'where': {
                'ticker': ticker,
                'date': date
            },
            'values': values
        })
    
    if not updates:
        return {
            "success": False,
            "updated_count": 0,
            "errors": ["No valid updates provided"]
        }
    
    return await batch_update_with_savepoint(session, updates, savepoint_name)

