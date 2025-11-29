"""
Migration script to add version column to companies table (Task 35: Optimistic Locking)
"""
import asyncio
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from config.database import init_database, close_database, get_mysql_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_version_column():
    """Add version column to companies table"""
    logger.info("=" * 60)
    logger.info("Adding version column to companies table")
    logger.info("=" * 60)
    
    await init_database()
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Check if column already exists
                check_query = text("""
                    SELECT COUNT(*) as count
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'companies'
                    AND COLUMN_NAME = 'version'
                """)
                
                result = await db_session.execute(check_query)
                count = result.scalar()
                
                if count > 0:
                    logger.info("Version column already exists, skipping migration")
                    return
                
                # Add version column
                logger.info("Adding version column...")
                alter_query = text("""
                    ALTER TABLE companies
                    ADD COLUMN version INT DEFAULT 1 NOT NULL
                """)
                
                await db_session.execute(alter_query)
                await db_session.commit()
                
                logger.info("✓ Version column added successfully")
                
                # Initialize all existing records with version = 1
                logger.info("Initializing existing records with version = 1...")
                init_query = text("""
                    UPDATE companies
                    SET version = 1
                    WHERE version IS NULL OR version = 0
                """)
                
                result = await db_session.execute(init_query)
                await db_session.commit()
                
                logger.info(f"✓ Initialized {result.rowcount} records with version = 1")
                
            finally:
                break
    except Exception as e:
        logger.error(f"Error adding version column: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(add_version_column())

