"""
Migration script to create database views (Task 43: Database Views)
Creates views for common queries to simplify data access
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


async def create_database_views():
    """Create database views (Task 43: Database Views)"""
    logger.info("=" * 60)
    logger.info("Creating Database Views")
    logger.info("Task 43: Database Views for Common Queries")
    logger.info("=" * 60)
    
    await init_database()
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Create view: Latest Company Prices
                logger.info("\nCreating v_company_latest_price view...")
                await db_session.execute(text("""
                    CREATE OR REPLACE VIEW v_company_latest_price AS
                    SELECT 
                        c.ticker,
                        c.company_name,
                        c.sector,
                        sp.date AS latest_date,
                        sp.close_price AS latest_price,
                        sp.price_change_pct AS latest_change,
                        sp.volume AS latest_volume,
                        sp.ma_5,
                        sp.ma_20,
                        sp.ma_50,
                        sp.ma_200
                    FROM companies c
                    JOIN stock_prices sp ON c.ticker = sp.ticker
                    WHERE sp.date = (
                        SELECT MAX(date) 
                        FROM stock_prices sp2 
                        WHERE sp2.ticker = c.ticker
                    )
                    AND c.deleted_at IS NULL
                """))
                logger.info("  ✓ v_company_latest_price view created")
                
                # Create view: Company Performance Summary
                logger.info("\nCreating v_company_performance_summary view...")
                await db_session.execute(text("""
                    CREATE OR REPLACE VIEW v_company_performance_summary AS
                    SELECT 
                        c.ticker,
                        c.company_name,
                        c.sector,
                        COUNT(sp.id) AS price_records_count,
                        MIN(sp.date) AS first_date,
                        MAX(sp.date) AS last_date,
                        AVG(sp.close_price) AS avg_price,
                        MAX(sp.close_price) AS max_price,
                        MIN(sp.close_price) AS min_price,
                        AVG(sp.volume) AS avg_volume,
                        SUM(sp.volume) AS total_volume
                    FROM companies c
                    LEFT JOIN stock_prices sp ON c.ticker = sp.ticker
                    WHERE c.deleted_at IS NULL
                    GROUP BY c.ticker, c.company_name, c.sector
                """))
                logger.info("  ✓ v_company_performance_summary view created")
                
                # Create view: Sector Performance Summary
                logger.info("\nCreating v_sector_performance_summary view...")
                await db_session.execute(text("""
                    CREATE OR REPLACE VIEW v_sector_performance_summary AS
                    SELECT 
                        c.sector,
                        COUNT(DISTINCT c.ticker) AS company_count,
                        COUNT(sp.id) AS total_price_records,
                        AVG(sp.close_price) AS avg_price,
                        MAX(sp.close_price) AS max_price,
                        MIN(sp.close_price) AS min_price,
                        AVG(sp.price_change_pct) AS avg_change_pct,
                        SUM(sp.volume) AS total_volume
                    FROM companies c
                    LEFT JOIN stock_prices sp ON c.ticker = sp.ticker
                    WHERE c.deleted_at IS NULL
                    GROUP BY c.sector
                """))
                logger.info("  ✓ v_sector_performance_summary view created")
                
                await db_session.commit()
                
                logger.info("\n" + "=" * 60)
                logger.info("✓ Database views created successfully!")
                logger.info("=" * 60)
                logger.info("\nCreated views:")
                logger.info("  1. v_company_latest_price - Latest price for each company")
                logger.info("  2. v_company_performance_summary - Performance summary per company")
                logger.info("  3. v_sector_performance_summary - Performance summary per sector")
                
            finally:
                break
    except Exception as e:
        logger.error(f"Error creating database views: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(create_database_views())

