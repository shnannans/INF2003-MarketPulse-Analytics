"""
Test script for advanced analytics endpoints (Tasks 22-24)
Tests window functions, CTEs, and recursive CTEs endpoints
"""
import asyncio
import sys
import logging
import requests
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api"

def test_window_functions():
    """Test GET /api/analytics/window-functions"""
    logger.info("=" * 60)
    logger.info("TEST: Window Functions Endpoint")
    logger.info("=" * 60)
    
    try:
        # Test with specific ticker
        logger.info("Testing with ticker=AAPL...")
        response = requests.get(f"{BASE_URL}/analytics/window-functions", params={
            "ticker": "AAPL",
            "days": 30,
            "limit": 10
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Status: {data.get('status')}")
            logger.info(f"✓ Query Type: {data.get('query_type')}")
            logger.info(f"✓ Count: {data.get('count')}")
            logger.info(f"✓ Ticker: {data.get('ticker')}")
            
            if data.get('data') and len(data['data']) > 0:
                first_item = data['data'][0]
                logger.info(f"✓ Sample data: ticker={first_item.get('ticker')}, date={first_item.get('date')}")
                logger.info(f"  - close_price: {first_item.get('close_price')}")
                logger.info(f"  - ma_30: {first_item.get('ma_30')}")
                logger.info(f"  - momentum_pct: {first_item.get('momentum_pct')}")
                logger.info(f"  - price_rank_today: {first_item.get('price_rank_today')}")
            else:
                logger.warning("⚠ No data returned")
        else:
            logger.error(f"✗ Request failed with status {response.status_code}: {response.text}")
            return False
        
        # Test without ticker (all tickers)
        logger.info("\nTesting without ticker (all tickers)...")
        response = requests.get(f"{BASE_URL}/analytics/window-functions", params={
            "days": 30,
            "limit": 5
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Status: {data.get('status')}")
            logger.info(f"✓ Count: {data.get('count')}")
            logger.info(f"✓ Returned {len(data.get('data', []))} records")
        else:
            logger.error(f"✗ Request failed with status {response.status_code}: {response.text}")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        logger.error("✗ Cannot connect to API server. Is it running?")
        return False
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False


def test_sector_performance():
    """Test GET /api/analytics/sector-performance"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Sector Performance (CTEs) Endpoint")
    logger.info("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/analytics/sector-performance", params={
            "days": 30
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Status: {data.get('status')}")
            logger.info(f"✓ Query Type: {data.get('query_type')}")
            logger.info(f"✓ Days: {data.get('days')}")
            logger.info(f"✓ Count: {data.get('count')} sectors")
            
            sectors = data.get('sectors', [])
            if sectors:
                logger.info(f"\n✓ Found {len(sectors)} sectors:")
                for sector in sectors[:5]:  # Show first 5
                    logger.info(f"  - {sector.get('sector')}: "
                              f"avg_price={sector.get('avg_price'):.2f}, "
                              f"volatility_pct={sector.get('volatility_pct'):.2f}%, "
                              f"companies={sector.get('company_count')}")
            else:
                logger.warning("⚠ No sectors returned")
        else:
            logger.error(f"✗ Request failed with status {response.status_code}: {response.text}")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        logger.error("✗ Cannot connect to API server. Is it running?")
        return False
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False


def test_price_trends():
    """Test GET /api/analytics/price-trends"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Price Trends (Recursive CTEs) Endpoint")
    logger.info("=" * 60)
    
    try:
        # Test with specific ticker
        logger.info("Testing with ticker=AAPL...")
        response = requests.get(f"{BASE_URL}/analytics/price-trends", params={
            "ticker": "AAPL",
            "min_consecutive_days": 3,
            "limit": 10
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Status: {data.get('status')}")
            logger.info(f"✓ Query Type: {data.get('query_type')}")
            logger.info(f"✓ Ticker: {data.get('ticker')}")
            logger.info(f"✓ Count: {data.get('count')}")
            
            trends = data.get('trends', [])
            if trends:
                logger.info(f"\n✓ Found {len(trends)} trend records:")
                for trend in trends[:5]:  # Show first 5
                    logger.info(f"  - {trend.get('ticker')} on {trend.get('date')}: "
                              f"price={trend.get('close_price')}, "
                              f"consecutive_days={trend.get('consecutive_days')}")
            else:
                logger.warning("⚠ No trends returned (may need more data)")
        else:
            logger.error(f"✗ Request failed with status {response.status_code}: {response.text}")
            return False
        
        # Test without ticker
        logger.info("\nTesting without ticker (all tickers)...")
        response = requests.get(f"{BASE_URL}/analytics/price-trends", params={
            "limit": 10
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Status: {data.get('status')}")
            logger.info(f"✓ Count: {data.get('count')}")
            logger.info(f"✓ Note: {data.get('note', '')}")
        else:
            logger.error(f"✗ Request failed with status {response.status_code}: {response.text}")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError:
        logger.error("✗ Cannot connect to API server. Is it running?")
        return False
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("ADVANCED ANALYTICS ENDPOINTS TEST")
    logger.info("Tasks 22-24: Window Functions, CTEs, Recursive CTEs")
    logger.info("=" * 60)
    
    results = []
    
    # Test window functions
    results.append(("Window Functions", test_window_functions()))
    
    # Test sector performance
    results.append(("Sector Performance (CTEs)", test_sector_performance()))
    
    # Test price trends
    results.append(("Price Trends (Recursive CTEs)", test_price_trends()))
    
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


if __name__ == "__main__":
    sys.exit(main())

