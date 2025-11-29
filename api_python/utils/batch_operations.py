"""
Batch Operations Utilities (Task 56: Batch Operations)
Provides utilities for batch processing of database operations
"""
import logging
from typing import List, Dict, Any, Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, text
from datetime import datetime

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Batch processor for database operations (Task 56: Batch Operations).
    Handles bulk inserts, updates, and deletes efficiently.
    """
    
    @staticmethod
    async def batch_insert(
        session: AsyncSession,
        model_class,
        records: List[Dict[str, Any]],
        batch_size: int = 100,
        on_error: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Batch insert records (Task 56: Batch Operations).
        
        Args:
            session: Database session
            model_class: SQLAlchemy model class
            records: List of dictionaries with record data
            batch_size: Number of records to insert per batch
            on_error: Optional callback function for error handling
        
        Returns:
            Dictionary with results: inserted_count, errors
        """
        result = {
            "inserted_count": 0,
            "errors": [],
            "total_records": len(records)
        }
        
        try:
            # Process in batches
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    # Create model instances
                    instances = [model_class(**record) for record in batch]
                    
                    # Add to session
                    session.add_all(instances)
                    
                    # Commit batch
                    await session.commit()
                    
                    result["inserted_count"] += len(batch)
                    logger.info(f"Batch inserted {len(batch)} records (total: {result['inserted_count']})")
                    
                except Exception as e:
                    await session.rollback()
                    error_msg = f"Error inserting batch {i//batch_size + 1}: {str(e)}"
                    result["errors"].append(error_msg)
                    logger.error(error_msg)
                    
                    if on_error:
                        on_error(e, batch)
            
            return result
            
        except Exception as e:
            await session.rollback()
            error_msg = f"Fatal error in batch insert: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
            return result
    
    @staticmethod
    async def batch_update(
        session: AsyncSession,
        model_class,
        updates: List[Dict[str, Any]],
        batch_size: int = 100,
        on_error: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Batch update records (Task 56: Batch Operations).
        
        Args:
            session: Database session
            model_class: SQLAlchemy model class
            updates: List of dictionaries with update data:
                - 'where': WHERE clause conditions (dict)
                - 'values': Values to update (dict)
            batch_size: Number of records to update per batch
            on_error: Optional callback function for error handling
        
        Returns:
            Dictionary with results: updated_count, errors
        """
        result = {
            "updated_count": 0,
            "errors": [],
            "total_updates": len(updates)
        }
        
        try:
            # Process in batches
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                
                try:
                    for update_item in batch:
                        where_conditions = update_item.get("where", {})
                        values = update_item.get("values", {})
                        
                        # Build update query
                        query = update(model_class)
                        for key, value in where_conditions.items():
                            query = query.where(getattr(model_class, key) == value)
                        
                        query = query.values(**values)
                        
                        # Execute update
                        result_obj = await session.execute(query)
                        result["updated_count"] += result_obj.rowcount
                    
                    # Commit batch
                    await session.commit()
                    logger.info(f"Batch updated {len(batch)} records (total: {result['updated_count']})")
                    
                except Exception as e:
                    await session.rollback()
                    error_msg = f"Error updating batch {i//batch_size + 1}: {str(e)}"
                    result["errors"].append(error_msg)
                    logger.error(error_msg)
                    
                    if on_error:
                        on_error(e, batch)
            
            return result
            
        except Exception as e:
            await session.rollback()
            error_msg = f"Fatal error in batch update: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
            return result
    
    @staticmethod
    async def batch_delete(
        session: AsyncSession,
        model_class,
        conditions: List[Dict[str, Any]],
        batch_size: int = 100,
        soft_delete: bool = True,
        on_error: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Batch delete records (Task 56: Batch Operations).
        
        Args:
            session: Database session
            model_class: SQLAlchemy model class
            conditions: List of dictionaries with delete conditions
            batch_size: Number of records to delete per batch
            soft_delete: If True, set deleted_at timestamp instead of hard delete
            on_error: Optional callback function for error handling
        
        Returns:
            Dictionary with results: deleted_count, errors
        """
        result = {
            "deleted_count": 0,
            "errors": [],
            "total_conditions": len(conditions)
        }
        
        try:
            # Process in batches
            for i in range(0, len(conditions), batch_size):
                batch = conditions[i:i + batch_size]
                
                try:
                    if soft_delete and hasattr(model_class, 'deleted_at'):
                        # Soft delete: update deleted_at
                        for condition in batch:
                            query = update(model_class)
                            for key, value in condition.items():
                                query = query.where(getattr(model_class, key) == value)
                            
                            query = query.values(deleted_at=datetime.now())
                            result_obj = await session.execute(query)
                            result["deleted_count"] += result_obj.rowcount
                    else:
                        # Hard delete
                        for condition in batch:
                            query = delete(model_class)
                            for key, value in condition.items():
                                query = query.where(getattr(model_class, key) == value)
                            
                            result_obj = await session.execute(query)
                            result["deleted_count"] += result_obj.rowcount
                    
                    # Commit batch
                    await session.commit()
                    logger.info(f"Batch deleted {len(batch)} records (total: {result['deleted_count']})")
                    
                except Exception as e:
                    await session.rollback()
                    error_msg = f"Error deleting batch {i//batch_size + 1}: {str(e)}"
                    result["errors"].append(error_msg)
                    logger.error(error_msg)
                    
                    if on_error:
                        on_error(e, batch)
            
            return result
            
        except Exception as e:
            await session.rollback()
            error_msg = f"Fatal error in batch delete: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(error_msg)
            return result

