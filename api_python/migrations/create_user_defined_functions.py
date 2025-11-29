"""
Migration script to create user-defined functions (Task 45: User-Defined Functions)
Creates functions for reusable calculations
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


async def create_user_defined_functions():
    """Create user-defined functions (Task 45: User-Defined Functions)"""
    logger.info("=" * 60)
    logger.info("Creating User-Defined Functions")
    logger.info("Task 45: User-Defined Functions for Reusable Calculations")
    logger.info("=" * 60)
    
    await init_database()
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Set log_bin_trust_function_creators to allow function creation
                try:
                    await db_session.execute(text("SET GLOBAL log_bin_trust_function_creators = 1"))
                    logger.info("  ✓ Set log_bin_trust_function_creators = 1")
                except Exception as e:
                    logger.warning(f"  ⚠ Could not set log_bin_trust_function_creators: {e}")
                    logger.info("  Continuing anyway...")
                
                # Drop function if exists (for re-creation)
                logger.info("\nCreating fn_calculate_rsi function...")
                await db_session.execute(text("DROP FUNCTION IF EXISTS fn_calculate_rsi"))
                
                # Create function: Calculate RSI (Relative Strength Index)
                # Note: MySQL functions need to be created with proper syntax
                try:
                    rsi_function_sql = """
                    CREATE FUNCTION fn_calculate_rsi(
                        p_ticker VARCHAR(10),
                        p_date DATE,
                        p_period INT
                    ) RETURNS DECIMAL(5,2)
                    READS SQL DATA
                    DETERMINISTIC
                    BEGIN
                        DECLARE avg_gain DECIMAL(10,4);
                        DECLARE avg_loss DECIMAL(10,4);
                        DECLARE rsi DECIMAL(5,2);
                        
                        SELECT 
                            AVG(CASE WHEN price_change_pct > 0 THEN price_change_pct ELSE 0 END),
                            AVG(CASE WHEN price_change_pct < 0 THEN ABS(price_change_pct) ELSE 0 END)
                        INTO avg_gain, avg_loss
                        FROM stock_prices
                        WHERE ticker = p_ticker
                          AND date <= p_date
                          AND date > DATE_SUB(p_date, INTERVAL p_period DAY)
                        ORDER BY date DESC
                        LIMIT p_period;
                        
                        IF avg_loss = 0 THEN
                            SET rsi = 100;
                        ELSE
                            SET rsi = 100 - (100 / (1 + (avg_gain / avg_loss)));
                        END IF;
                        
                        RETURN rsi;
                    END
                    """
                    await db_session.execute(text(rsi_function_sql))
                    await db_session.commit()
                    logger.info("  ✓ fn_calculate_rsi function created")
                except Exception as e:
                    logger.error(f"  ✗ Error creating fn_calculate_rsi: {e}")
                    await db_session.rollback()
                    raise
                
                # Create function: Calculate Price Change Percentage
                logger.info("\nCreating fn_calculate_price_change_pct function...")
                await db_session.execute(text("DROP FUNCTION IF EXISTS fn_calculate_price_change_pct"))
                
                try:
                    price_change_function_sql = """
                    CREATE FUNCTION fn_calculate_price_change_pct(
                        p_current_price DECIMAL(10,2),
                        p_previous_price DECIMAL(10,2)
                    ) RETURNS DECIMAL(5,2)
                    DETERMINISTIC
                    BEGIN
                        DECLARE change_pct DECIMAL(5,2);
                        
                        IF p_previous_price IS NULL OR p_previous_price = 0 THEN
                            RETURN NULL;
                        END IF;
                        
                        SET change_pct = ((p_current_price - p_previous_price) / p_previous_price) * 100;
                        RETURN change_pct;
                    END
                    """
                    await db_session.execute(text(price_change_function_sql))
                    await db_session.commit()
                    logger.info("  ✓ fn_calculate_price_change_pct function created")
                except Exception as e:
                    logger.error(f"  ✗ Error creating fn_calculate_price_change_pct: {e}")
                    await db_session.rollback()
                    raise
                
                # Create function: Calculate Volatility
                logger.info("\nCreating fn_calculate_volatility function...")
                await db_session.execute(text("DROP FUNCTION IF EXISTS fn_calculate_volatility"))
                
                try:
                    volatility_function_sql = """
                    CREATE FUNCTION fn_calculate_volatility(
                        p_ticker VARCHAR(10),
                        p_date DATE,
                        p_period INT
                    ) RETURNS DECIMAL(10,4)
                    READS SQL DATA
                    DETERMINISTIC
                    BEGIN
                        DECLARE volatility DECIMAL(10,4);
                        DECLARE avg_price DECIMAL(10,2);
                        DECLARE std_dev DECIMAL(10,4);
                        
                        SELECT 
                            AVG(close_price),
                            STDDEV(close_price)
                        INTO avg_price, std_dev
                        FROM stock_prices
                        WHERE ticker = p_ticker
                          AND date <= p_date
                          AND date > DATE_SUB(p_date, INTERVAL p_period DAY)
                        ORDER BY date DESC
                        LIMIT p_period;
                        
                        IF avg_price IS NULL OR avg_price = 0 THEN
                            RETURN NULL;
                        END IF;
                        
                        SET volatility = (std_dev / avg_price) * 100;
                        RETURN volatility;
                    END
                    """
                    await db_session.execute(text(volatility_function_sql))
                    await db_session.commit()
                    logger.info("  ✓ fn_calculate_volatility function created")
                except Exception as e:
                    logger.error(f"  ✗ Error creating fn_calculate_volatility: {e}")
                    await db_session.rollback()
                    raise
                
                await db_session.commit()
                
                logger.info("\n" + "=" * 60)
                logger.info("✓ User-defined functions created successfully!")
                logger.info("=" * 60)
                logger.info("\nCreated functions:")
                logger.info("  1. fn_calculate_rsi - Calculate Relative Strength Index")
                logger.info("  2. fn_calculate_price_change_pct - Calculate price change percentage")
                logger.info("  3. fn_calculate_volatility - Calculate volatility")
                
            finally:
                break
    except Exception as e:
        logger.error(f"Error creating user-defined functions: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(create_user_defined_functions())

