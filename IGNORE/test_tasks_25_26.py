"""
Test script for advanced analytics endpoints (Tasks 25-26)
Tests rolling aggregations and price-sentiment correlation endpoints
"""
import asyncio
import sys
import logging
from datetime import datetime
from config.database import AsyncSessionLocal, init_database, close_database
from routers.advanced_analytics import get_rolling_aggregations, get_price_sentiment_correlation
from config.database import get_mysql_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_rolling_aggregations():
    """Test GET /api/analytics/rolling-aggregations"""
    logger.info("=" * 60)
    logger.info("TEST: Rolling Aggregations Endpoint (Task 25)")
    logger.info("=" * 60)
    
    test_passed = False
    try:
        async for db_session in get_mysql_session():
            try:
                # Test with specific ticker
                logger.info("Testing with ticker=AAPL...")
                result = await get_rolling_aggregations("AAPL", 10, db_session)
                
                logger.info(f"✓ Status: {result.get('status')}")
                logger.info(f"✓ Query Type: {result.get('query_type')}")
                logger.info(f"✓ Count: {result.get('count')}")
                logger.info(f"✓ Ticker: {result.get('ticker')}")
                
                if result.get('data') and len(result['data']) > 0:
                    first_item = result['data'][0]
                    logger.info(f"✓ Sample data: ticker={first_item.get('ticker')}, date={first_item.get('date')}")
                    logger.info(f"  - close_price: {first_item.get('close_price')}")
                    logger.info(f"  - volume_7day_sum: {first_item.get('volume_7day_sum')}")
                    logger.info(f"  - ma_20: {first_item.get('ma_20')}")
                    logger.info(f"  - high_20d: {first_item.get('high_20d')}")
                    logger.info(f"  - low_20d: {first_item.get('low_20d')}")
                    logger.info(f"  - stoch_oscillator: {first_item.get('stoch_oscillator')}")
                else:
                    logger.warning("⚠ No data returned")
                    return False
                
                # Test without ticker (all tickers)
                logger.info("\nTesting without ticker (all tickers)...")
                result_all = await get_rolling_aggregations(None, 5, db_session)
                
                logger.info(f"✓ Status: {result_all.get('status')}")
                logger.info(f"✓ Count: {result_all.get('count')}")
                logger.info(f"✓ Returned {len(result_all.get('data', []))} records")
                
                # Both tests passed
                test_passed = True
            finally:
                break
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def test_price_sentiment_correlation():
    """Test GET /api/analytics/price-sentiment-correlation"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Price-Sentiment Correlation Endpoint (Task 26)")
    logger.info("=" * 60)
    
    test_passed = False
    try:
        async for db_session in get_mysql_session():
            try:
                # Test with specific ticker
                logger.info("Testing with ticker=AAPL...")
                result = await get_price_sentiment_correlation("AAPL", 30, 10, db_session)
                
                logger.info(f"✓ Status: {result.get('status')}")
                logger.info(f"✓ Query Type: {result.get('query_type')}")
                logger.info(f"✓ Ticker: {result.get('ticker')}")
                logger.info(f"✓ Days: {result.get('days')}")
                logger.info(f"✓ Count: {result.get('count')}")
                logger.info(f"✓ Note: {result.get('note', '')}")
                
                if result.get('data') and len(result['data']) > 0:
                    first_item = result['data'][0]
                    logger.info(f"✓ Sample data: ticker={first_item.get('ticker')}, date={first_item.get('date')}")
                    logger.info(f"  - close_price: {first_item.get('close_price')}")
                    logger.info(f"  - price_change_pct: {first_item.get('price_change_pct')}")
                    logger.info(f"  - volume: {first_item.get('volume')}")
                    logger.info(f"  - avg_price_change_7d: {first_item.get('avg_price_change_7d')}")
                    logger.info(f"  - volatility_7d: {first_item.get('volatility_7d')}")
                else:
                    logger.warning("⚠ No data returned")
                    return False
                
                # Test without ticker
                logger.info("\nTesting without ticker (all tickers)...")
                result_all = await get_price_sentiment_correlation(None, 30, 5, db_session)
                
                logger.info(f"✓ Status: {result_all.get('status')}")
                logger.info(f"✓ Count: {result_all.get('count')}")
                logger.info(f"✓ Returned {len(result_all.get('data', []))} records")
                
                # Both tests passed
                test_passed = True
            finally:
                break
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("ADVANCED ANALYTICS ENDPOINTS TEST")
    logger.info("Tasks 25-26: Rolling Aggregations, Price-Sentiment Correlation")
    logger.info("=" * 60)
    
    # Initialize database
    await init_database()
    
    # Import again after initialization
    from config.database import AsyncSessionLocal
    
    if not AsyncSessionLocal:
        logger.error("Database session not available")
        await close_database()
        sys.exit(1)
    
    try:
        results = []
        
        # Test rolling aggregations
        results.append(("Rolling Aggregations (Task 25)", await test_rolling_aggregations()))
        
        # Test price-sentiment correlation
        results.append(("Price-Sentiment Correlation (Task 26)", await test_price_sentiment_correlation()))
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        all_passed = True
        for test_name, passed in results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            logger.info(f"{test_name}: {status}")
            if not passed:
                all_passed = False
        
        logger.info("=" * 60)
        if all_passed:
            logger.info("✓ All tests passed!")
        else:
            logger.error("✗ Some tests failed")
        
        return 0 if all_passed else 1
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await close_database()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

