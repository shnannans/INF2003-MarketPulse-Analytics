"""
Migration script to create composite indexes for time-series queries (Task 27)
Run this script once to add composite indexes to improve query performance
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

async def create_composite_indexes():
    """Create composite indexes for time-series queries"""
    await init_database()
    
    # Import again after initialization to get the updated global
    from config.database import AsyncSessionLocal
    
    if not AsyncSessionLocal:
        logger.error("Database session not available")
        await close_database()
        sys.exit(1)
    
    try:
        async with AsyncSessionLocal() as session:
            # Check existing indexes
            logger.info("Checking existing indexes on stock_prices table...")
            check_indexes_query = text("""
                SELECT INDEX_NAME, COLUMN_NAME, SEQ_IN_INDEX, COLLATION
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'stock_prices'
                ORDER BY INDEX_NAME, SEQ_IN_INDEX
            """)
            result = await session.execute(check_indexes_query)
            existing_indexes = result.fetchall()
            
            if existing_indexes:
                logger.info(f"Found {len(existing_indexes)} existing indexes:")
                for idx in existing_indexes:
                    logger.info(f"  - {idx[0]}: {idx[1]} (seq: {idx[2]})")
            
            # Index 1: Primary index for ticker + date queries
            logger.info("\nCreating index: idx_ticker_date_deleted...")
            try:
                create_index1_query = text("""
                    CREATE INDEX idx_ticker_date_deleted 
                    ON stock_prices(ticker, date DESC)
                """)
                await session.execute(create_index1_query)
                await session.commit()
                logger.info("✓ Successfully created idx_ticker_date_deleted")
            except Exception as e:
                if "Duplicate key name" in str(e) or "already exists" in str(e).lower():
                    logger.info("  Index idx_ticker_date_deleted already exists, skipping")
                else:
                    logger.warning(f"  Note: {e}")
                    await session.rollback()
            
            # Index 2: Index for date-first queries (market-wide analysis)
            logger.info("\nCreating index: idx_date_ticker_deleted...")
            try:
                create_index2_query = text("""
                    CREATE INDEX idx_date_ticker_deleted 
                    ON stock_prices(date DESC, ticker)
                """)
                await session.execute(create_index2_query)
                await session.commit()
                logger.info("✓ Successfully created idx_date_ticker_deleted")
            except Exception as e:
                if "Duplicate key name" in str(e) or "already exists" in str(e).lower():
                    logger.info("  Index idx_date_ticker_deleted already exists, skipping")
                else:
                    logger.warning(f"  Note: {e}")
                    await session.rollback()
            
            # Verify indexes were created
            logger.info("\nVerifying indexes...")
            verify_query = text("""
                SELECT INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as columns
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'stock_prices'
                  AND INDEX_NAME IN ('idx_ticker_date_deleted', 'idx_date_ticker_deleted')
                GROUP BY INDEX_NAME
            """)
            verify_result = await session.execute(verify_query)
            verified_indexes = verify_result.fetchall()
            
            if verified_indexes:
                logger.info("✓ Verified indexes:")
                for idx in verified_indexes:
                    logger.info(f"  - {idx[0]}: {idx[1]}")
            else:
                logger.warning("⚠ Could not verify all indexes")
            
            logger.info("\n✓ Composite indexes migration completed successfully")
            
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        await session.rollback()
        sys.exit(1)
    finally:
        await close_database()

if __name__ == "__main__":
    asyncio.run(create_composite_indexes())

