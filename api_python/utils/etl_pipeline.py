"""
ETL Pipeline for Data Warehouse (Task 41: ETL Pipeline)
Extract, Transform, Load process for populating data warehouse
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, insert, func
from decimal import Decimal

from models.database_models import Company, StockPrice

logger = logging.getLogger(__name__)

# ETL tracking table name
ETL_TRACKING_TABLE = "etl_tracking"


async def get_last_etl_timestamp(session: AsyncSession, etl_type: str = "stock_prices") -> Optional[datetime]:
    """
    Get last ETL run timestamp (Task 41: ETL Pipeline).
    
    Args:
        session: Database session
        etl_type: Type of ETL process
    
    Returns:
        Last run timestamp or None
    """
    try:
        # Create tracking table if it doesn't exist
        await session.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {ETL_TRACKING_TABLE} (
                id INT PRIMARY KEY AUTO_INCREMENT,
                etl_type VARCHAR(50) UNIQUE,
                last_run TIMESTAMP,
                records_processed INT,
                status VARCHAR(20),
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """))
        await session.commit()
        
        # Get last run timestamp
        result = await session.execute(
            text(f"SELECT last_run FROM {ETL_TRACKING_TABLE} WHERE etl_type = :etl_type"),
            {"etl_type": etl_type}
        )
        row = result.first()
        
        if row and row[0]:
            return row[0]
        
        # Default to 30 days ago if no previous run
        return datetime.now() - timedelta(days=30)
    except Exception as e:
        logger.error(f"Error getting last ETL timestamp: {e}")
        return datetime.now() - timedelta(days=30)


async def update_last_etl_timestamp(
    session: AsyncSession,
    etl_type: str,
    records_processed: int,
    status: str = "success",
    error_message: Optional[str] = None
):
    """
    Update last ETL run timestamp (Task 41: ETL Pipeline).
    
    Args:
        session: Database session
        etl_type: Type of ETL process
        records_processed: Number of records processed
        status: Status of ETL run
        error_message: Error message if failed
    """
    try:
        await session.execute(
            text(f"""
                INSERT INTO {ETL_TRACKING_TABLE} (etl_type, last_run, records_processed, status, error_message)
                VALUES (:etl_type, NOW(), :records_processed, :status, :error_message)
                ON DUPLICATE KEY UPDATE
                    last_run = NOW(),
                    records_processed = :records_processed,
                    status = :status,
                    error_message = :error_message,
                    updated_at = NOW()
            """),
            {
                "etl_type": etl_type,
                "records_processed": records_processed,
                "status": status,
                "error_message": error_message
            }
        )
        await session.commit()
    except Exception as e:
        logger.error(f"Error updating ETL timestamp: {e}")


async def get_or_create_company_dimension(session: AsyncSession, ticker: str) -> Optional[int]:
    """
    Get or create company dimension ID (Task 41: ETL Pipeline).
    
    Args:
        session: Database session
        ticker: Stock ticker symbol
    
    Returns:
        Company dimension ID or None
    """
    try:
        # Get company from operational DB
        result = await session.execute(
            select(Company).where(Company.ticker == ticker).where(Company.deleted_at.is_(None))
        )
        company = result.scalar_one_or_none()
        
        if not company:
            return None
        
        # Get or create in dimension table
        result = await session.execute(
            text("SELECT company_id FROM dim_company WHERE ticker = :ticker AND is_current = TRUE"),
            {"ticker": ticker}
        )
        row = result.first()
        
        if row:
            return row[0]
        
        # Create new dimension record
        await session.execute(
            text("""
                INSERT INTO dim_company (ticker, company_name, sector, market_cap, valid_from, valid_to, is_current)
                VALUES (:ticker, :company_name, :sector, :market_cap, CURDATE(), NULL, TRUE)
            """),
            {
                "ticker": ticker,
                "company_name": company.company_name,
                "sector": company.sector,
                "market_cap": company.market_cap
            }
        )
        await session.commit()
        
        # Get the new ID
        result = await session.execute(
            text("SELECT company_id FROM dim_company WHERE ticker = :ticker AND is_current = TRUE"),
            {"ticker": ticker}
        )
        row = result.first()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Error getting/creating company dimension: {e}")
        return None


async def get_date_dimension_id(session: AsyncSession, date_value: date) -> Optional[int]:
    """
    Get date dimension ID (Task 41: ETL Pipeline).
    
    Args:
        session: Database session
        date_value: Date value
    
    Returns:
        Date dimension ID or None
    """
    try:
        date_id = int(date_value.strftime("%Y%m%d"))
        
        # Verify date exists in dimension
        result = await session.execute(
            text("SELECT date_id FROM dim_date WHERE date_id = :date_id"),
            {"date_id": date_id}
        )
        row = result.first()
        
        if row:
            return row[0]
        
        # Create date dimension if it doesn't exist
        await session.execute(
            text("""
                INSERT INTO dim_date (date_id, date, year, quarter, month, week, day_of_week, is_weekend, is_trading_day)
                VALUES (
                    :date_id,
                    :date,
                    YEAR(:date),
                    QUARTER(:date),
                    MONTH(:date),
                    WEEK(:date),
                    DAYOFWEEK(:date),
                    DAYOFWEEK(:date) IN (1, 7),
                    DAYOFWEEK(:date) NOT IN (1, 7)
                )
            """),
            {
                "date_id": date_id,
                "date": date_value
            }
        )
        await session.commit()
        
        return date_id
    except Exception as e:
        logger.error(f"Error getting date dimension ID: {e}")
        return None


async def get_sector_dimension_id(session: AsyncSession, sector: Optional[str]) -> Optional[int]:
    """
    Get sector dimension ID (Task 41: ETL Pipeline).
    
    Args:
        session: Database session
        sector: Sector name
    
    Returns:
        Sector dimension ID or None
    """
    try:
        if not sector:
            return None
        
        # Get sector dimension
        result = await session.execute(
            text("SELECT sector_id FROM dim_sector WHERE sector_name = :sector_name"),
            {"sector_name": sector}
        )
        row = result.first()
        
        if row:
            return row[0]
        
        # Create sector dimension if it doesn't exist
        await session.execute(
            text("""
                INSERT INTO dim_sector (sector_name, sector_description)
                VALUES (:sector_name, CONCAT('Sector: ', :sector_name))
            """),
            {"sector_name": sector}
        )
        await session.commit()
        
        # Get the new ID
        result = await session.execute(
            text("SELECT sector_id FROM dim_sector WHERE sector_name = :sector_name"),
            {"sector_name": sector}
        )
        row = result.first()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Error getting sector dimension ID: {e}")
        return None


async def etl_stock_prices_to_warehouse(session: AsyncSession) -> Dict[str, Any]:
    """
    ETL process to load stock prices into data warehouse (Task 41: ETL Pipeline).
    
    Extract: Get new stock prices from operational DB
    Transform: Calculate metrics, join dimensions
    Load: Insert into data warehouse fact table
    
    Args:
        session: Database session
    
    Returns:
        Dictionary with ETL results
    """
    logger.info("Starting ETL process for stock prices to data warehouse...")
    
    try:
        # Extract: Get new prices since last run
        last_run = await get_last_etl_timestamp(session, "stock_prices")
        logger.info(f"Last ETL run: {last_run}")
        
        # Get new stock prices
        # Since StockPrice doesn't have created_at, we'll use date to filter
        # Get prices from the last 30 days or since last run date (whichever is more recent)
        last_run_date = last_run.date() if isinstance(last_run, datetime) else last_run
        
        result = await session.execute(
            select(StockPrice)
            .where(StockPrice.date >= last_run_date)
            .where(StockPrice.ticker.in_(
                select(Company.ticker).where(Company.deleted_at.is_(None))
            ))
        )
        new_prices = result.scalars().all()
        
        logger.info(f"Found {len(new_prices)} new stock prices to process")
        
        if not new_prices:
            await update_last_etl_timestamp(session, "stock_prices", 0, "success")
            return {
                "status": "success",
                "records_processed": 0,
                "message": "No new records to process"
            }
        
        # Transform: Calculate and join dimensions
        facts = []
        processed = 0
        errors = 0
        
        for price in new_prices:
            try:
                # Get or create dimension IDs
                ticker_id = await get_or_create_company_dimension(session, price.ticker)
                if not ticker_id:
                    logger.warning(f"Skipping {price.ticker}: company dimension not found")
                    errors += 1
                    continue
                
                date_id = await get_date_dimension_id(session, price.date)
                if not date_id:
                    logger.warning(f"Skipping {price.ticker} {price.date}: date dimension not found")
                    errors += 1
                    continue
                
                # Get sector dimension ID
                company_result = await session.execute(
                    select(Company).where(Company.ticker == price.ticker)
                )
                company = company_result.scalar_one_or_none()
                sector_id = None
                if company and company.sector:
                    sector_id = await get_sector_dimension_id(session, company.sector)
                
                # Create fact record
                fact = {
                    'ticker_id': ticker_id,
                    'date_id': date_id,
                    'sector_id': sector_id,
                    'open_price': float(price.open_price) if price.open_price else None,
                    'high_price': float(price.high_price) if price.high_price else None,
                    'low_price': float(price.low_price) if price.low_price else None,
                    'close_price': float(price.close_price) if price.close_price else None,
                    'volume': int(price.volume) if price.volume else None,
                    'price_change_pct': float(price.price_change_pct) if price.price_change_pct else None,
                    'ma_5': float(price.ma_5) if price.ma_5 else None,
                    'ma_20': float(price.ma_20) if price.ma_20 else None,
                    'ma_50': float(price.ma_50) if price.ma_50 else None,
                    'ma_200': float(price.ma_200) if price.ma_200 else None,
                }
                
                facts.append(fact)
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing stock price {price.ticker} {price.date}: {e}")
                errors += 1
                continue
        
        # Load: Bulk insert into warehouse
        if facts:
            logger.info(f"Inserting {len(facts)} fact records into data warehouse...")
            
            # Use bulk insert
            for fact in facts:
                await session.execute(
                    text("""
                        INSERT INTO stock_price_facts (
                            ticker_id, date_id, sector_id,
                            open_price, high_price, low_price, close_price,
                            volume, price_change_pct,
                            ma_5, ma_20, ma_50, ma_200
                        )
                        VALUES (
                            :ticker_id, :date_id, :sector_id,
                            :open_price, :high_price, :low_price, :close_price,
                            :volume, :price_change_pct,
                            :ma_5, :ma_20, :ma_50, :ma_200
                        )
                        ON DUPLICATE KEY UPDATE
                            open_price = VALUES(open_price),
                            high_price = VALUES(high_price),
                            low_price = VALUES(low_price),
                            close_price = VALUES(close_price),
                            volume = VALUES(volume),
                            price_change_pct = VALUES(price_change_pct),
                            ma_5 = VALUES(ma_5),
                            ma_20 = VALUES(ma_20),
                            ma_50 = VALUES(ma_50),
                            ma_200 = VALUES(ma_200)
                    """),
                    fact
                )
            
            await session.commit()
            logger.info(f"Successfully inserted {len(facts)} fact records")
        
        # Update last run timestamp
        await update_last_etl_timestamp(session, "stock_prices", processed, "success" if errors == 0 else "partial")
        
        return {
            "status": "success" if errors == 0 else "partial",
            "records_processed": processed,
            "records_inserted": len(facts),
            "errors": errors,
            "message": f"ETL completed: {processed} processed, {len(facts)} inserted, {errors} errors"
        }
        
    except Exception as e:
        logger.error(f"Error in ETL process: {e}")
        await update_last_etl_timestamp(session, "stock_prices", 0, "error", str(e))
        raise


async def refresh_materialized_view(session: AsyncSession) -> Dict[str, Any]:
    """
    Refresh materialized view (Task 40: Materialized Views).
    
    Args:
        session: Database session
    
    Returns:
        Dictionary with refresh results
    """
    logger.info("Refreshing materialized view...")
    
    try:
        result = await session.execute(text("""
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
        await session.commit()
        
        # Get count
        count_result = await session.execute(text("SELECT COUNT(*) FROM mv_sector_daily_performance"))
        count = count_result.scalar()
        
        logger.info(f"Materialized view refreshed: {count} records")
        
        return {
            "status": "success",
            "records_count": count,
            "message": f"Materialized view refreshed with {count} records"
        }
        
    except Exception as e:
        logger.error(f"Error refreshing materialized view: {e}")
        raise

