from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text, update
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import statistics
import math

from config.database import get_mysql_session
from models.database_models import Company, StockPrice
from models.pydantic_models import StockAnalysisResponse, StockAnalysisQuery
from utils.error_handlers import handle_database_error, InvalidTickerError
from utils.live_stock_service import get_stock_analysis as get_live_stock_analysis

router = APIRouter()
logger = logging.getLogger(__name__)

def calculate_volatility(prices: List[float]) -> float:
    """Calculate annualized volatility from price series"""
    if len(prices) < 2:
        return 0.0
    returns = []

    for i in range(1, len(prices)):
        if prices[i] != 0:
            returns.append((prices[i-1] - prices[i]) / prices[i])

    if not returns:
        return 0.0

    mean_return = statistics.mean(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)

    return math.sqrt(variance) * math.sqrt(252) * 100  # Annualized volatility


@router.get("/stock_analysis", response_model=dict)
async def get_stock_analysis_rest_style(
    ticker: str = Query(..., description="Stock ticker symbol"),
    days: Optional[int] = Query(90, ge=1, le=365, description="Number of days to analyze"),
    live: Optional[bool] = Query(True, description="Use live data (True) or fallback to database (False)"),
    db: AsyncSession = Depends(get_mysql_session)
):

    """
    Get detailed stock analysis with technical indicators (REST-style endpoint).
    Now supports real-time data fetching with yfinance integration.
    """
    return await get_stock_analysis_internal(ticker, days, live, db)

async def get_stock_analysis_internal(
    ticker: str,
    days: int,
    live: bool,
    db: AsyncSession

):

    """
    Internal function for stock analysis with live and database fallback.
    """

    try:
        ticker = ticker.upper()

        # DB-first: try to satisfy from MySQL if possible, regardless of 'live'
        logger.info(f"DB-first: attempting to serve {ticker} for last {days} days from MySQL")
        price_data = []
        try:
            price_stmt = select(
                StockPrice.date,
                StockPrice.open_price,
                StockPrice.high_price,
                StockPrice.low_price,
                StockPrice.close_price,
                StockPrice.adj_close,
                StockPrice.volume,
                StockPrice.ma_5,
                StockPrice.ma_20,
                StockPrice.ma_50,
                StockPrice.ma_200,
                StockPrice.price_change_pct,
                StockPrice.volume_change_pct
            ).where(
                and_(
                    StockPrice.ticker == ticker,
                    StockPrice.date >= text(f"DATE_SUB(CURDATE(), INTERVAL {days} DAY)")
                )
            ).order_by(StockPrice.date.desc()).limit(500)

            price_result = await db.execute(price_stmt)
            price_data = price_result.fetchall()
        except Exception as e:
            logger.warning(f"DB-first: MySQL unavailable or query failed for {ticker}: {e}")
            price_data = []

        if price_data and len(price_data) >= min(days, 5):
            logger.info(f"DB-first: serving {len(price_data)} rows for {ticker} from MySQL")
            company_stmt = select(Company).where(Company.ticker == ticker)
            company_row = await db.execute(company_stmt)
            company = company_row.first()
            company_data = None
            if company:
                c = company[0]
                company_data = {
                    "ticker": c.ticker,
                    "company_name": c.company_name,
                    "sector": c.sector,
                    "market_cap": c.market_cap,
                }

            prices = [float(row.close_price) for row in price_data if row.close_price]
            current_price = prices[0] if prices else None
            volatility = calculate_volatility(prices)

            analysis = []
            for row in price_data:
                analysis.append({
                    "date": row.date,
                    "open_price": row.open_price,
                    "high_price": row.high_price,
                    "low_price": row.low_price,
                    "close_price": row.close_price,
                    "adj_close": row.adj_close,
                    "volume": row.volume,
                    "ma_5": row.ma_5,
                    "ma_20": row.ma_20,
                    "ma_50": row.ma_50,
                    "ma_200": row.ma_200,
                    "price_change_pct": row.price_change_pct,
                    "volume_change_pct": row.volume_change_pct,
                })

            return {
                "ticker": ticker,
                "company": company_data,
                "current_price": current_price,
                "volatility": round(volatility, 4),
                "analysis": analysis,
                "count": len(analysis),
                "data_source": "database_first",
                "status": "success"
            }

        # If DB insufficient or empty, use live
        if live:
            logger.info(f"DB insufficient; fetching live stock analysis for {ticker}, days: {days}")
            result = await get_live_stock_analysis(ticker, days)

            if result and result.get("status") == "success" and result.get("analysis"):
                logger.info(f"Live service returned {len(result.get('analysis', []))} data points for {ticker}")
                try:
                    await upsert_company_and_prices(db, result)
                except Exception as e:
                    logger.error(f"Write-through upsert failed for {ticker}: {e}")
                return result
            else:
                logger.warning(f"Live service failed for {ticker}, falling back to database")

        # Fallback to database if live fails or is disabled
        logger.info(f"Using database fallback for stock analysis: {ticker}")

        # Get stock price data with technical indicators
        price_stmt = select(
            StockPrice.date,
            StockPrice.open_price,
            StockPrice.high_price,
            StockPrice.low_price,
            StockPrice.close_price,
            StockPrice.adj_close,
            StockPrice.volume,
            StockPrice.ma_5,
            StockPrice.ma_20,
            StockPrice.ma_50,
            StockPrice.ma_200,
            StockPrice.price_change_pct,
            StockPrice.volume_change_pct
        ).where(
            and_(

                StockPrice.ticker == ticker,
                StockPrice.date >= text(f"DATE_SUB(CURDATE(), INTERVAL {days} DAY)")
            )
        ).order_by(StockPrice.date.desc()).limit(500)

        price_result = await db.execute(price_stmt)
        price_data = price_result.fetchall()


        if not price_data:
            if live:
                # If database also fails but live was attempted, return live service error
                return await get_live_stock_analysis(ticker, days)
            else:
                raise InvalidTickerError(ticker)

        # Get company information
        company_stmt = select(Company).where(Company.ticker == ticker)
        company_result = await db.execute(company_stmt)
        company_row = company_result.first()
        company = company_row[0] if company_row else None

        # Calculate additional metrics
        prices = [float(row.close_price) for row in price_data if row.close_price]
        current_price = prices[0] if prices else None
        volatility = calculate_volatility(prices)

        # Format price data
        analysis = []
        for row in price_data:
            analysis.append({
                "date": row.date,
                "open_price": row.open_price,
                "high_price": row.high_price,
                "low_price": row.low_price,
                "close_price": row.close_price,
                "adj_close": row.adj_close,
                "volume": row.volume,
                "ma_5": row.ma_5,
                "ma_20": row.ma_20,
                "ma_50": row.ma_50,
                "ma_200": row.ma_200,
                "price_change_pct": row.price_change_pct,
                "volume_change_pct": row.volume_change_pct
            })

        # Format company data
        company_data = None
        if company:
            company_data = {
                "ticker": company.ticker,
                "company_name": company.company_name,
                "sector": company.sector,
                "market_cap": company.market_cap
            }

        return {
            "ticker": ticker,
            "company": company_data,
            "current_price": current_price,
            "volatility": round(volatility, 4),
            "analysis": analysis,
            "count": len(analysis),
            "data_source": "database_fallback",
            "status": "success"
        }


    except InvalidTickerError:
        raise
    except Exception as e:

        logger.error(f"Error in stock analysis for {ticker}: {str(e)}")
        handle_database_error(e)


# Keep the old function name for backward compatibility
get_stock_analysis = get_stock_analysis_internal 


async def upsert_company_and_prices(db: AsyncSession, live_result: Dict[str, Any]) -> None:
    """Upsert company and OHLCV rows into MySQL after a successful live fetch.

    Expects live_result shape from utils.live_stock_service.get_stock_analysis.
    """
    from models.database_models import Company, StockPrice  # Local import to avoid cycles

    ticker: str = live_result.get("ticker", "").upper()
    company: Dict[str, Any] = live_result.get("company") or {}
    analysis: List[Dict[str, Any]] = live_result.get("analysis") or []

    # Upsert company
    if ticker:
        company_stmt = select(Company).where(Company.ticker == ticker)
        company_row = (await db.execute(company_stmt)).first()

        if company_row:
            comp: Company = company_row[0]
            comp.company_name = company.get("company_name") or comp.company_name
            comp.sector = company.get("sector") or comp.sector
            # best-effort market cap if available
            try:
                mc = company.get("market_cap")
                if mc is not None:
                    comp.market_cap = int(mc)
            except Exception:
                pass
        else:
            comp = Company(
                ticker=ticker,
                company_name=company.get("company_name", ticker),
                sector=company.get("sector"),
                market_cap=(int(company.get("market_cap")) if company.get("market_cap") else None),
                created_at=datetime.utcnow(),
            )
            db.add(comp)

    # Upsert OHLCV rows
    for row in analysis:
        try:
            date_str = row.get("date")
            if not date_str:
                continue
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

            existing_stmt = select(StockPrice).where(
                and_(StockPrice.ticker == ticker, StockPrice.date == date_obj)
            )
            existing = (await db.execute(existing_stmt)).first()

            fields = {
                "open_price": row.get("open_price"),
                "high_price": row.get("high_price"),
                "low_price": row.get("low_price"),
                "close_price": row.get("close_price"),
                "volume": row.get("volume"),
                "ma_5": row.get("ma_5"),
                "ma_20": row.get("ma_20"),
                "ma_50": row.get("ma_50"),
                "ma_200": row.get("ma_200"),
                "price_change_pct": row.get("price_change_pct"),
                "volume_change_pct": row.get("volume_change_pct"),
            }

            if existing:
                # Update existing row
                await db.execute(
                    update(StockPrice)
                    .where(and_(StockPrice.ticker == ticker, StockPrice.date == date_obj))
                    .values(**{k: v for k, v in fields.items() if v is not None})
                )
            else:
                # Insert new row
                sp = StockPrice(ticker=ticker, date=date_obj, **fields)
                db.add(sp)
        except Exception as e:
            # Continue with best-effort persistence
            logger.error(f"Upsert error for {ticker} {row.get('date')}: {e}")

    # Commit once
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e