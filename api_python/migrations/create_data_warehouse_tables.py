"""
Migration script to create data warehouse tables (Task 39: Star Schema Design)
Creates fact and dimension tables for OLAP queries
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


async def create_data_warehouse_tables():
    """Create data warehouse tables (Task 39: Star Schema Design)"""
    logger.info("=" * 60)
    logger.info("Creating Data Warehouse Tables (Star Schema)")
    logger.info("Task 39: Fact and Dimension Tables")
    logger.info("=" * 60)
    
    await init_database()
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Create dimension tables first
                logger.info("\nCreating dimension tables...")
                
                # 1. Company dimension (SCD Type 2 for historical tracking)
                logger.info("Creating dim_company table...")
                await db_session.execute(text("""
                    CREATE TABLE IF NOT EXISTS dim_company (
                        company_id INT PRIMARY KEY AUTO_INCREMENT,
                        ticker VARCHAR(10) UNIQUE,
                        company_name VARCHAR(255),
                        sector VARCHAR(100),
                        market_cap BIGINT,
                        -- SCD Type 2 fields for historical tracking
                        valid_from DATE,
                        valid_to DATE,
                        is_current BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_ticker (ticker),
                        INDEX idx_current (is_current),
                        INDEX idx_valid_dates (valid_from, valid_to)
                    )
                """))
                logger.info("  ✓ dim_company table created")
                
                # 2. Date dimension (pre-populated)
                logger.info("Creating dim_date table...")
                await db_session.execute(text("""
                    CREATE TABLE IF NOT EXISTS dim_date (
                        date_id INT PRIMARY KEY,
                        date DATE UNIQUE,
                        year INT,
                        quarter INT,
                        month INT,
                        week INT,
                        day_of_week INT,
                        is_weekend BOOLEAN,
                        is_trading_day BOOLEAN,
                        INDEX idx_date (date),
                        INDEX idx_year_month (year, month),
                        INDEX idx_year_quarter (year, quarter)
                    )
                """))
                logger.info("  ✓ dim_date table created")
                
                # 3. Sector dimension
                logger.info("Creating dim_sector table...")
                await db_session.execute(text("""
                    CREATE TABLE IF NOT EXISTS dim_sector (
                        sector_id INT PRIMARY KEY AUTO_INCREMENT,
                        sector_name VARCHAR(100) UNIQUE,
                        sector_description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_sector_name (sector_name)
                    )
                """))
                logger.info("  ✓ dim_sector table created")
                
                # Create fact table
                logger.info("\nCreating fact table...")
                logger.info("Creating stock_price_facts table...")
                await db_session.execute(text("""
                    CREATE TABLE IF NOT EXISTS stock_price_facts (
                        fact_id BIGINT PRIMARY KEY AUTO_INCREMENT,
                        ticker_id INT,
                        date_id INT,
                        sector_id INT,
                        open_price DECIMAL(12,4),
                        high_price DECIMAL(12,4),
                        low_price DECIMAL(12,4),
                        close_price DECIMAL(12,4),
                        volume BIGINT,
                        price_change_pct DECIMAL(5,2),
                        ma_5 DECIMAL(12,4),
                        ma_20 DECIMAL(12,4),
                        ma_50 DECIMAL(12,4),
                        ma_200 DECIMAL(12,4),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        deleted_at TIMESTAMP NULL,
                        INDEX idx_ticker_date (ticker_id, date_id),
                        INDEX idx_date_sector (date_id, sector_id),
                        INDEX idx_deleted (deleted_at),
                        INDEX idx_date (date_id),
                        INDEX idx_sector (sector_id),
                        FOREIGN KEY (ticker_id) REFERENCES dim_company(company_id),
                        FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
                        FOREIGN KEY (sector_id) REFERENCES dim_sector(sector_id)
                    )
                """))
                logger.info("  ✓ stock_price_facts table created")
                
                await db_session.commit()
                
                # Populate sector dimension from existing companies
                logger.info("\nPopulating dimension tables...")
                logger.info("Populating dim_sector from companies table...")
                await db_session.execute(text("""
                    INSERT IGNORE INTO dim_sector (sector_name, sector_description)
                    SELECT DISTINCT 
                        sector,
                        CONCAT('Sector: ', sector) as sector_description
                    FROM companies
                    WHERE sector IS NOT NULL
                      AND deleted_at IS NULL
                """))
                await db_session.commit()
                logger.info("  ✓ dim_sector populated")
                
                # Populate date dimension (last 5 years)
                logger.info("Populating dim_date (last 5 years)...")
                await db_session.execute(text("""
                    INSERT IGNORE INTO dim_date (date_id, date, year, quarter, month, week, day_of_week, is_weekend, is_trading_day)
                    SELECT 
                        DATE_FORMAT(d.date, '%Y%m%d') as date_id,
                        d.date,
                        YEAR(d.date) as year,
                        QUARTER(d.date) as quarter,
                        MONTH(d.date) as month,
                        WEEK(d.date) as week,
                        DAYOFWEEK(d.date) as day_of_week,
                        DAYOFWEEK(d.date) IN (1, 7) as is_weekend,
                        DAYOFWEEK(d.date) NOT IN (1, 7) as is_trading_day
                    FROM (
                        SELECT DATE_ADD('2020-01-01', INTERVAL seq.seq DAY) as date
                        FROM (
                            SELECT @row := @row + 1 as seq
                            FROM (SELECT 0 UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t1,
                                 (SELECT 0 UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t2,
                                 (SELECT 0 UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) t3,
                                 (SELECT @row := -1) r
                        ) seq
                        WHERE DATE_ADD('2020-01-01', INTERVAL seq.seq DAY) <= CURDATE()
                    ) d
                """))
                await db_session.commit()
                logger.info("  ✓ dim_date populated")
                
                logger.info("\n" + "=" * 60)
                logger.info("✓ Data warehouse tables created successfully!")
                logger.info("=" * 60)
                logger.info("\nNext steps:")
                logger.info("  1. Populate dim_company from companies table")
                logger.info("  2. Populate stock_price_facts from stock_prices table")
                logger.info("  3. Set up ETL pipeline for regular updates")
                
            finally:
                break
    except Exception as e:
        logger.error(f"Error creating data warehouse tables: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(create_data_warehouse_tables())

