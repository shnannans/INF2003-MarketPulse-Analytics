"""
Migration script to create materialized views (Task 40: Materialized Views)
Creates pre-calculated aggregations for fast dashboard loads
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


async def create_materialized_views():
    """Create materialized views (Task 40: Materialized Views)"""
    logger.info("=" * 60)
    logger.info("Creating Materialized Views")
    logger.info("Task 40: Materialized Views for Dashboards")
    logger.info("=" * 60)
    
    await init_database()
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Create materialized view table for daily sector performance
                logger.info("\nCreating mv_sector_daily_performance table...")
                await db_session.execute(text("""
                    CREATE TABLE IF NOT EXISTS mv_sector_daily_performance (
                        sector VARCHAR(100),
                        date DATE,
                        company_count INT,
                        avg_price DECIMAL(12,4),
                        total_volume BIGINT,
                        avg_change_pct DECIMAL(5,2),
                        sector_high DECIMAL(12,4),
                        sector_low DECIMAL(12,4),
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (sector, date),
                        INDEX idx_date (date),
                        INDEX idx_sector (sector),
                        INDEX idx_updated_at (updated_at)
                    )
                """))
                logger.info("  ✓ mv_sector_daily_performance table created")
                
                await db_session.commit()
                
                # Populate materialized view
                logger.info("\nPopulating materialized view...")
                await db_session.execute(text("""
                    INSERT INTO mv_sector_daily_performance
                    SELECT 
                        c.sector,
                        sp.date,
                        COUNT(DISTINCT sp.ticker) AS company_count,
                        AVG(sp.close_price) AS avg_price,
                        SUM(sp.volume) AS total_volume,
                        AVG(sp.price_change_pct) AS avg_change_pct,
                        MAX(sp.high_price) AS sector_high,
                        MIN(sp.low_price) AS sector_low,
                        NOW() AS updated_at
                    FROM stock_prices sp
                    JOIN companies c ON sp.ticker = c.ticker
                    WHERE c.deleted_at IS NULL
                    GROUP BY c.sector, sp.date
                    ON DUPLICATE KEY UPDATE
                        company_count = VALUES(company_count),
                        avg_price = VALUES(avg_price),
                        total_volume = VALUES(total_volume),
                        avg_change_pct = VALUES(avg_change_pct),
                        sector_high = VALUES(sector_high),
                        sector_low = VALUES(sector_low),
                        updated_at = NOW()
                """))
                await db_session.commit()
                
                result = await db_session.execute(text("SELECT COUNT(*) FROM mv_sector_daily_performance"))
                count = result.scalar()
                logger.info(f"  ✓ Materialized view populated with {count} records")
                
                logger.info("\n" + "=" * 60)
                logger.info("✓ Materialized views created successfully!")
                logger.info("=" * 60)
                logger.info("\nNext steps:")
                logger.info("  1. Set up scheduled job to refresh materialized view")
                logger.info("  2. Run daily after market close")
                logger.info("  3. Can be triggered via cron job or scheduled task")
                
            finally:
                break
    except Exception as e:
        logger.error(f"Error creating materialized views: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(create_materialized_views())

