"""
Migration script to create stored procedures (Task 44: Stored Procedures)
Creates stored procedures for complex operations
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


async def create_stored_procedures():
    """Create stored procedures (Task 44: Stored Procedures)"""
    logger.info("=" * 60)
    logger.info("Creating Stored Procedures")
    logger.info("Task 44: Stored Procedures for Complex Operations")
    logger.info("=" * 60)
    
    await init_database()
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Drop procedure if exists (for re-creation)
                logger.info("\nCreating sp_update_company_with_prices procedure...")
                await db_session.execute(text("DROP PROCEDURE IF EXISTS sp_update_company_with_prices"))
                
                # Create procedure: Update Company with Recalculated Metrics
                await db_session.execute(text("""
                    CREATE PROCEDURE sp_update_company_with_prices(
                        IN p_ticker VARCHAR(10),
                        IN p_company_name VARCHAR(255),
                        IN p_sector VARCHAR(100)
                    )
                    BEGIN
                        DECLARE EXIT HANDLER FOR SQLEXCEPTION
                        BEGIN
                            ROLLBACK;
                            RESIGNAL;
                        END;
                        
                        START TRANSACTION;
                        
                        -- Update company
                        UPDATE companies 
                        SET company_name = p_company_name,
                            sector = p_sector
                        WHERE ticker = p_ticker
                          AND deleted_at IS NULL;
                        
                        -- Recalculate moving averages for recent prices (last 30 days)
                        -- Using JOIN to avoid MySQL limitation with subqueries in UPDATE
                        -- Recalculate MA_5
                        UPDATE stock_prices sp1
                        INNER JOIN (
                            SELECT 
                                sp2.ticker,
                                sp2.date,
                                AVG(sp3.close_price) AS ma_5
                            FROM stock_prices sp2
                            INNER JOIN stock_prices sp3 ON sp3.ticker = sp2.ticker
                                AND sp3.date <= sp2.date
                                AND sp3.date > DATE_SUB(sp2.date, INTERVAL 5 DAY)
                            WHERE sp2.ticker = p_ticker
                              AND sp2.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                            GROUP BY sp2.ticker, sp2.date
                        ) ma5_calc ON sp1.ticker = ma5_calc.ticker AND sp1.date = ma5_calc.date
                        SET sp1.ma_5 = ma5_calc.ma_5
                        WHERE sp1.ticker = p_ticker
                          AND sp1.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);
                        
                        -- Recalculate MA_20
                        UPDATE stock_prices sp1
                        INNER JOIN (
                            SELECT 
                                sp2.ticker,
                                sp2.date,
                                AVG(sp3.close_price) AS ma_20
                            FROM stock_prices sp2
                            INNER JOIN stock_prices sp3 ON sp3.ticker = sp2.ticker
                                AND sp3.date <= sp2.date
                                AND sp3.date > DATE_SUB(sp2.date, INTERVAL 20 DAY)
                            WHERE sp2.ticker = p_ticker
                              AND sp2.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                            GROUP BY sp2.ticker, sp2.date
                        ) ma20_calc ON sp1.ticker = ma20_calc.ticker AND sp1.date = ma20_calc.date
                        SET sp1.ma_20 = ma20_calc.ma_20
                        WHERE sp1.ticker = p_ticker
                          AND sp1.date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);
                        
                        COMMIT;
                    END
                """))
                logger.info("  ✓ sp_update_company_with_prices procedure created")
                
                # Create procedure: Recalculate Moving Averages
                logger.info("\nCreating sp_recalculate_moving_averages procedure...")
                await db_session.execute(text("DROP PROCEDURE IF EXISTS sp_recalculate_moving_averages"))
                
                await db_session.execute(text("""
                    CREATE PROCEDURE sp_recalculate_moving_averages(
                        IN p_ticker VARCHAR(10),
                        IN p_days INT
                    )
                    BEGIN
                        DECLARE EXIT HANDLER FOR SQLEXCEPTION
                        BEGIN
                            ROLLBACK;
                            RESIGNAL;
                        END;
                        
                        START TRANSACTION;
                        
                        -- Recalculate MA_5 using JOIN to avoid MySQL limitation
                        UPDATE stock_prices sp1
                        INNER JOIN (
                            SELECT 
                                sp2.ticker,
                                sp2.date,
                                AVG(sp3.close_price) AS ma_5
                            FROM stock_prices sp2
                            INNER JOIN stock_prices sp3 ON sp3.ticker = sp2.ticker
                                AND sp3.date <= sp2.date
                                AND sp3.date > DATE_SUB(sp2.date, INTERVAL 5 DAY)
                            WHERE sp2.ticker = p_ticker
                              AND sp2.date >= DATE_SUB(CURDATE(), INTERVAL p_days DAY)
                            GROUP BY sp2.ticker, sp2.date
                        ) ma5_calc ON sp1.ticker = ma5_calc.ticker AND sp1.date = ma5_calc.date
                        SET sp1.ma_5 = ma5_calc.ma_5
                        WHERE sp1.ticker = p_ticker
                          AND sp1.date >= DATE_SUB(CURDATE(), INTERVAL p_days DAY);
                        
                        -- Recalculate MA_20
                        UPDATE stock_prices sp1
                        INNER JOIN (
                            SELECT 
                                sp2.ticker,
                                sp2.date,
                                AVG(sp3.close_price) AS ma_20
                            FROM stock_prices sp2
                            INNER JOIN stock_prices sp3 ON sp3.ticker = sp2.ticker
                                AND sp3.date <= sp2.date
                                AND sp3.date > DATE_SUB(sp2.date, INTERVAL 20 DAY)
                            WHERE sp2.ticker = p_ticker
                              AND sp2.date >= DATE_SUB(CURDATE(), INTERVAL p_days DAY)
                            GROUP BY sp2.ticker, sp2.date
                        ) ma20_calc ON sp1.ticker = ma20_calc.ticker AND sp1.date = ma20_calc.date
                        SET sp1.ma_20 = ma20_calc.ma_20
                        WHERE sp1.ticker = p_ticker
                          AND sp1.date >= DATE_SUB(CURDATE(), INTERVAL p_days DAY);
                        
                        -- Recalculate MA_50
                        UPDATE stock_prices sp1
                        INNER JOIN (
                            SELECT 
                                sp2.ticker,
                                sp2.date,
                                AVG(sp3.close_price) AS ma_50
                            FROM stock_prices sp2
                            INNER JOIN stock_prices sp3 ON sp3.ticker = sp2.ticker
                                AND sp3.date <= sp2.date
                                AND sp3.date > DATE_SUB(sp2.date, INTERVAL 50 DAY)
                            WHERE sp2.ticker = p_ticker
                              AND sp2.date >= DATE_SUB(CURDATE(), INTERVAL p_days DAY)
                            GROUP BY sp2.ticker, sp2.date
                        ) ma50_calc ON sp1.ticker = ma50_calc.ticker AND sp1.date = ma50_calc.date
                        SET sp1.ma_50 = ma50_calc.ma_50
                        WHERE sp1.ticker = p_ticker
                          AND sp1.date >= DATE_SUB(CURDATE(), INTERVAL p_days DAY);
                        
                        -- Recalculate MA_200
                        UPDATE stock_prices sp1
                        INNER JOIN (
                            SELECT 
                                sp2.ticker,
                                sp2.date,
                                AVG(sp3.close_price) AS ma_200
                            FROM stock_prices sp2
                            INNER JOIN stock_prices sp3 ON sp3.ticker = sp2.ticker
                                AND sp3.date <= sp2.date
                                AND sp3.date > DATE_SUB(sp2.date, INTERVAL 200 DAY)
                            WHERE sp2.ticker = p_ticker
                              AND sp2.date >= DATE_SUB(CURDATE(), INTERVAL p_days DAY)
                            GROUP BY sp2.ticker, sp2.date
                        ) ma200_calc ON sp1.ticker = ma200_calc.ticker AND sp1.date = ma200_calc.date
                        SET sp1.ma_200 = ma200_calc.ma_200
                        WHERE sp1.ticker = p_ticker
                          AND sp1.date >= DATE_SUB(CURDATE(), INTERVAL p_days DAY);
                        
                        COMMIT;
                    END
                """))
                logger.info("  ✓ sp_recalculate_moving_averages procedure created")
                
                await db_session.commit()
                
                logger.info("\n" + "=" * 60)
                logger.info("✓ Stored procedures created successfully!")
                logger.info("=" * 60)
                logger.info("\nCreated procedures:")
                logger.info("  1. sp_update_company_with_prices - Update company and recalculate metrics")
                logger.info("  2. sp_recalculate_moving_averages - Recalculate moving averages for a ticker")
                
            finally:
                break
    except Exception as e:
        logger.error(f"Error creating stored procedures: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(create_stored_procedures())

