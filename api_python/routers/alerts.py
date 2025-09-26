from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from typing import Optional
import logging

from config.database import get_mysql_session
from models.database_models import StockPrice, Company
from models.pydantic_models import AlertsQuery, AlertsResponse
from utils.error_handlers import handle_database_error

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/alerts", response_model=dict)
async def get_alerts(
    limit: Optional[int] = Query(10, ge=1, le=50, description="Maximum number of alerts"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Generate alerts based on price movements and sentiment.
    """
    try:
        alerts = []

        # Get significant price movements from database
        alert_sql = text("""
            SELECT
                sp1.ticker,
                sp1.close_price as current_price,
                sp2.close_price as prev_price,
                ((sp1.close_price - sp2.close_price) / sp2.close_price * 100) as price_change_pct,
                c.company_name
            FROM stock_prices sp1
            JOIN stock_prices sp2 ON sp1.ticker = sp2.ticker
            JOIN companies c ON sp1.ticker = c.ticker
            WHERE sp1.date = CURDATE() - INTERVAL 1 DAY
            AND sp2.date = CURDATE() - INTERVAL 2 DAY
            AND ABS((sp1.close_price - sp2.close_price) / sp2.close_price * 100) > 3
            ORDER BY ABS((sp1.close_price - sp2.close_price) / sp2.close_price * 100) DESC
            LIMIT 5
        """)

        result = await db.execute(alert_sql)
        price_alerts = result.fetchall()

        # Process price alerts
        for alert in price_alerts:
            direction = 'increased' if alert.price_change_pct > 0 else 'decreased'
            severity = 'high' if abs(alert.price_change_pct) > 5 else 'medium'

            alerts.append({
                'ticker': alert.ticker,
                'type': 'price_movement',
                'message': f"{alert.company_name} ({alert.ticker}) {direction} by {abs(round(alert.price_change_pct, 2))}% in last 24 hours",
                'severity': severity
            })

        # Add some sentiment-based alerts (mock for now)
        if len(alerts) < limit:
            alerts.append({
                'ticker': 'AAPL',
                'type': 'sentiment',
                'message': 'High positive sentiment spike detected with recent news coverage',
                'severity': 'medium'
            })

        return {
            "alerts": alerts,
            "count": len(alerts),
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error generating alerts: {str(e)}")
        handle_database_error(e)

