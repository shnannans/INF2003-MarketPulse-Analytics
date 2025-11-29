"""
Migration script to create covering indexes and full-text indexes (Tasks 28-29)
Run this script once to add covering indexes for dashboard queries and full-text indexes for search
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

async def create_covering_and_fulltext_indexes():
    """Create covering indexes and full-text indexes"""
    await init_database()
    
    # Import again after initialization to get the updated global
    from config.database import AsyncSessionLocal
    
    if not AsyncSessionLocal:
        logger.error("Database session not available")
        await close_database()
        sys.exit(1)
    
    try:
        async with AsyncSessionLocal() as session:
            logger.info("=" * 60)
            logger.info("TASK 28: Creating Covering Indexes")
            logger.info("=" * 60)
            
            # Task 28: Covering Index for companies table
            logger.info("\nCreating covering index: idx_companies_listing...")
            try:
                create_index1_query = text("""
                    CREATE INDEX idx_companies_listing 
                    ON companies(sector, market_cap DESC, deleted_at, ticker, company_name)
                """)
                await session.execute(create_index1_query)
                await session.commit()
                logger.info("✓ Successfully created idx_companies_listing")
            except Exception as e:
                if "Duplicate key name" in str(e) or "already exists" in str(e).lower():
                    logger.info("  Index idx_companies_listing already exists, skipping")
                else:
                    logger.warning(f"  Note: {e}")
                    await session.rollback()
            
            # Task 28: Covering Index for financial_metrics table
            logger.info("\nCreating covering index: idx_metrics_ticker...")
            try:
                # Check if financial_metrics table exists and has these columns
                check_table_query = text("""
                    SELECT COUNT(*) as count
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'financial_metrics'
                """)
                result = await session.execute(check_table_query)
                table_exists = result.scalar() > 0
                
                if table_exists:
                    create_index2_query = text("""
                        CREATE INDEX idx_metrics_ticker 
                        ON financial_metrics(ticker, last_updated, pe_ratio, dividend_yield, beta, market_cap)
                    """)
                    await session.execute(create_index2_query)
                    await session.commit()
                    logger.info("✓ Successfully created idx_metrics_ticker")
                else:
                    logger.warning("  financial_metrics table does not exist, skipping")
            except Exception as e:
                if "Duplicate key name" in str(e) or "already exists" in str(e).lower():
                    logger.info("  Index idx_metrics_ticker already exists, skipping")
                else:
                    logger.warning(f"  Note: {e}")
                    await session.rollback()
            
            logger.info("\n" + "=" * 60)
            logger.info("TASK 29: Creating Full-Text Indexes")
            logger.info("=" * 60)
            
            # Task 29: Full-Text Index for companies table
            logger.info("\nCreating full-text index: idx_company_name_ft...")
            try:
                # Check if company_name column exists and is suitable for full-text index
                check_column_query = text("""
                    SELECT COUNT(*) as count
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'companies'
                      AND COLUMN_NAME = 'company_name'
                """)
                result = await session.execute(check_column_query)
                column_exists = result.scalar() > 0
                
                if column_exists:
                    # Check table engine - full-text indexes require MyISAM or InnoDB (MySQL 5.6+)
                    check_engine_query = text("""
                        SELECT ENGINE
                        FROM INFORMATION_SCHEMA.TABLES
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = 'companies'
                    """)
                    result = await session.execute(check_engine_query)
                    engine = result.scalar()
                    
                    if engine and engine.upper() in ['INNODB', 'MYISAM']:
                        create_ft_index_query = text("""
                            CREATE FULLTEXT INDEX idx_company_name_ft 
                            ON companies(company_name)
                        """)
                        await session.execute(create_ft_index_query)
                        await session.commit()
                        logger.info("✓ Successfully created idx_company_name_ft")
                    else:
                        logger.warning(f"  Table engine is {engine}, full-text index may not be supported")
                else:
                    logger.warning("  company_name column does not exist, skipping")
            except Exception as e:
                if "Duplicate key name" in str(e) or "already exists" in str(e).lower():
                    logger.info("  Index idx_company_name_ft already exists, skipping")
                elif "doesn't support" in str(e).lower() or "not supported" in str(e).lower():
                    logger.warning(f"  Full-text index not supported: {e}")
                else:
                    logger.warning(f"  Note: {e}")
                    await session.rollback()
            
            # Verify indexes were created
            logger.info("\n" + "=" * 60)
            logger.info("Verifying Indexes")
            logger.info("=" * 60)
            
            # Verify covering indexes
            logger.info("\nVerifying covering indexes...")
            verify_covering_query = text("""
                SELECT INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as columns
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME IN ('companies', 'financial_metrics')
                  AND INDEX_NAME IN ('idx_companies_listing', 'idx_metrics_ticker')
                GROUP BY TABLE_NAME, INDEX_NAME
            """)
            verify_result = await session.execute(verify_covering_query)
            verified_covering = verify_result.fetchall()
            
            if verified_covering:
                logger.info("✓ Verified covering indexes:")
                for idx in verified_covering:
                    logger.info(f"  - {idx[0]}: {idx[1]}")
            else:
                logger.warning("⚠ Could not verify all covering indexes")
            
            # Verify full-text indexes
            logger.info("\nVerifying full-text indexes...")
            verify_ft_query = text("""
                SELECT INDEX_NAME, COLUMN_NAME
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'companies'
                  AND INDEX_NAME = 'idx_company_name_ft'
            """)
            verify_ft_result = await session.execute(verify_ft_query)
            verified_ft = verify_ft_result.fetchall()
            
            if verified_ft:
                logger.info("✓ Verified full-text indexes:")
                for idx in verified_ft:
                    logger.info(f"  - {idx[0]}: {idx[1]}")
            else:
                logger.warning("⚠ Could not verify full-text index (may not be supported or not created)")
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ Migration completed successfully")
            logger.info("=" * 60)
            
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        await session.rollback()
        sys.exit(1)
    finally:
        await close_database()

if __name__ == "__main__":
    asyncio.run(create_covering_and_fulltext_indexes())

