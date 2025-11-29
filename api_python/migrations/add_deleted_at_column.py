"""
Migration script to add deleted_at column to companies table
Run this script once to add the soft delete column to the database
"""
import asyncio
import sys
import os
import logging

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from config.database import init_database, close_database, AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_deleted_at_column():
    """Add deleted_at column to companies table if it doesn't exist"""
    await init_database()
    
    # Import again after initialization to get the updated global
    from config.database import AsyncSessionLocal
    
    if not AsyncSessionLocal:
        logger.error("Database session not available")
        await close_database()
        sys.exit(1)
    
    try:
        async with AsyncSessionLocal() as session:
            # Check if column already exists
            check_column_query = text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'companies'
                AND COLUMN_NAME = 'deleted_at'
            """)
            
            result = await session.execute(check_column_query)
            count = result.scalar()
            
            if count > 0:
                logger.info("Column 'deleted_at' already exists in companies table. Skipping migration.")
                return
            
            logger.info("Adding deleted_at column to companies table...")
            
            # Add the column
            alter_table_query = text("""
                ALTER TABLE companies 
                ADD COLUMN deleted_at DATETIME NULL 
                AFTER created_at
            """)
            
            await session.execute(alter_table_query)
            await session.commit()
            
            logger.info("✓ Successfully added deleted_at column to companies table")
            
            # Add index for better query performance
            logger.info("Adding index on deleted_at column...")
            
            try:
                create_index_query = text("""
                    CREATE INDEX idx_companies_deleted_at ON companies(deleted_at)
                """)
                await session.execute(create_index_query)
                await session.commit()
                logger.info("✓ Successfully added index on deleted_at column")
            except Exception as e:
                # Index might already exist, that's okay
                logger.warning(f"Index creation note: {e}")
                await session.rollback()
            
            # Ensure all existing records have deleted_at = NULL
            logger.info("Setting deleted_at = NULL for all existing records...")
            update_query = text("""
                UPDATE companies SET deleted_at = NULL WHERE deleted_at IS NULL
            """)
            await session.execute(update_query)
            await session.commit()
            
            logger.info("✓ Migration completed successfully")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await close_database()

if __name__ == "__main__":
    asyncio.run(add_deleted_at_column())

