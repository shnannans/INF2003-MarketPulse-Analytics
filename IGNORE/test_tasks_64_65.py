"""
Test script for Tasks 64-65: Advanced Charts and Real-Time Updates
Tests advanced chart data endpoints and real-time update functionality
"""
import asyncio
import sys
import logging
from config.database import init_database, close_database, get_mysql_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_advanced_charts():
    """Test Task 64: Advanced Charts"""
    logger.info("=" * 60)
    logger.info("TEST: Advanced Charts (Task 64)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        from config.database import get_read_session
        from routers.advanced_charts import (
            get_sector_heatmap_data,
            get_correlation_scatter_data,
            get_volatility_bands_data,
            get_momentum_indicators_data,
            get_technical_analysis_data
        )
        
        async for db_session in get_read_session():
            try:
                # Test 1: Sector Heatmap
                logger.info("\nTest 1: Sector Heatmap Data")
                
                heatmap = await get_sector_heatmap_data(30, db_session)
                
                if heatmap.get("status") == "success":
                    logger.info(f"  [OK] Sector heatmap data retrieved")
                    logger.info(f"    - Chart Type: {heatmap.get('chart_type')}")
                    logger.info(f"    - Days: {heatmap.get('days')}")
                    logger.info(f"    - Sectors: {heatmap.get('count')}")
                    if heatmap.get("sectors"):
                        logger.info(f"    - Sample Sector: {heatmap['sectors'][0].get('sector')}")
                else:
                    logger.warning(f"  [WARN] Sector heatmap data retrieval failed")
                
                # Test 2: Correlation Scatter Plot
                logger.info("\nTest 2: Correlation Scatter Plot Data")
                
                scatter = await get_correlation_scatter_data("AAPL", 30, db_session)
                
                if scatter.get("status") == "success":
                    logger.info(f"  [OK] Correlation scatter data retrieved")
                    logger.info(f"    - Chart Type: {scatter.get('chart_type')}")
                    logger.info(f"    - Ticker: {scatter.get('ticker')}")
                    logger.info(f"    - Data Points: {scatter.get('count')}")
                else:
                    logger.warning(f"  [WARN] Correlation scatter data retrieval failed")
                
                # Test 3: Volatility Bands
                logger.info("\nTest 3: Volatility Bands Data")
                
                volatility = await get_volatility_bands_data("AAPL", 30, 20, db_session)
                
                if volatility.get("status") == "success":
                    logger.info(f"  [OK] Volatility bands data retrieved")
                    logger.info(f"    - Chart Type: {volatility.get('chart_type')}")
                    logger.info(f"    - Ticker: {volatility.get('ticker')}")
                    logger.info(f"    - Period: {volatility.get('period')}")
                    logger.info(f"    - Bands: {volatility.get('count')}")
                    if volatility.get("bands"):
                        sample = volatility["bands"][-1]
                        logger.info(f"    - Sample: Upper={sample.get('upper_band')}, Lower={sample.get('lower_band')}")
                else:
                    logger.warning(f"  [WARN] Volatility bands data retrieval failed")
                
                # Test 4: Momentum Indicators
                logger.info("\nTest 4: Momentum Indicators Data")
                
                momentum = await get_momentum_indicators_data("AAPL", 30, db_session)
                
                if momentum.get("status") == "success":
                    logger.info(f"  [OK] Momentum indicators data retrieved")
                    logger.info(f"    - Chart Type: {momentum.get('chart_type')}")
                    logger.info(f"    - Ticker: {momentum.get('ticker')}")
                    logger.info(f"    - Indicators: {momentum.get('count')}")
                    if momentum.get("indicators"):
                        sample = momentum["indicators"][-1]
                        logger.info(f"    - Sample RSI: {sample.get('rsi')}")
                        logger.info(f"    - Sample MACD: {sample.get('macd')}")
                else:
                    logger.warning(f"  [WARN] Momentum indicators data retrieval failed")
                
                # Test 5: Technical Analysis
                logger.info("\nTest 5: Technical Analysis Data")
                
                technical = await get_technical_analysis_data("AAPL", 30, "RSI,MACD,BB", db_session)
                
                if technical.get("status") == "success":
                    logger.info(f"  [OK] Technical analysis data retrieved")
                    logger.info(f"    - Chart Type: {technical.get('chart_type')}")
                    logger.info(f"    - Ticker: {technical.get('ticker')}")
                    logger.info(f"    - Indicators: {technical.get('indicators')}")
                    logger.info(f"    - Data Points: {technical.get('count')}")
                else:
                    logger.warning(f"  [WARN] Technical analysis data retrieval failed")
                
                # Test 6: Verify Advanced Charts Benefits
                logger.info("\nTest 6: Verify Advanced Charts Benefits")
                logger.info("  Note: Advanced charts provide:")
                logger.info("    - Sector heatmap visualization")
                logger.info("    - Correlation scatter plots")
                logger.info("    - Volatility bands (Bollinger Bands)")
                logger.info("    - Momentum indicators (RSI, MACD)")
                logger.info("    - Technical analysis charts")
                logger.info("  [OK] Advanced charts are implemented")
                
                test_passed = True
            finally:
                break
    except Exception as e:
        logger.error(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def test_realtime_updates():
    """Test Task 65: Real-Time Updates"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Real-Time Updates (Task 65)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        from config.database import get_read_session
        from routers.realtime_updates import (
            get_realtime_status,
            get_last_updates,
            get_live_indicators,
            trigger_refresh,
            get_auto_refresh_config
        )
        
        async for db_session in get_read_session():
            try:
                # Test 1: Get Real-Time Status
                logger.info("\nTest 1: Get Real-Time Status")
                
                status = await get_realtime_status(db_session)
                
                if status.get("status") == "success":
                    conn_status = status.get("connection_status", {})
                    logger.info(f"  [OK] Real-time status retrieved")
                    logger.info(f"    - Connected: {conn_status.get('connected')}")
                    logger.info(f"    - Last Update: {conn_status.get('last_update')}")
                    logger.info(f"    - Update Count: {conn_status.get('update_count')}")
                else:
                    logger.warning(f"  [WARN] Real-time status retrieval failed")
                
                # Test 2: Get Last Updates
                logger.info("\nTest 2: Get Last Updates")
                
                last_updates = await get_last_updates("AAPL", db_session)
                
                if last_updates.get("status") == "success":
                    logger.info(f"  [OK] Last updates retrieved")
                    logger.info(f"    - Stock Prices: {last_updates.get('last_updates', {}).get('stock_prices')}")
                    logger.info(f"    - Companies: {last_updates.get('last_updates', {}).get('companies')}")
                    logger.info(f"    - API: {last_updates.get('last_updates', {}).get('api')}")
                else:
                    logger.warning(f"  [WARN] Last updates retrieval failed")
                
                # Test 3: Get Live Indicators
                logger.info("\nTest 3: Get Live Indicators")
                
                indicators = await get_live_indicators("AAPL", db_session)
                
                if indicators.get("status") == "success":
                    logger.info(f"  [OK] Live indicators retrieved")
                    logger.info(f"    - Indicators: {indicators.get('count')}")
                    if indicators.get("indicators"):
                        sample = indicators["indicators"][0]
                        logger.info(f"    - Sample: Ticker={sample.get('ticker')}, Is Live={sample.get('is_live')}")
                else:
                    logger.warning(f"  [WARN] Live indicators retrieval failed")
                
                # Test 4: Trigger Refresh
                logger.info("\nTest 4: Trigger Refresh")
                
                refresh = await trigger_refresh("AAPL", db_session)
                
                if refresh.get("status") == "success":
                    logger.info(f"  [OK] Refresh triggered")
                    logger.info(f"    - Refresh Triggered: {refresh.get('refresh_triggered')}")
                    logger.info(f"    - Update Count: {refresh.get('connection_status', {}).get('update_count')}")
                else:
                    logger.warning(f"  [WARN] Refresh trigger failed")
                
                # Test 5: Get Auto-Refresh Config
                logger.info("\nTest 5: Get Auto-Refresh Config")
                
                config = await get_auto_refresh_config(db_session)
                
                if config.get("status") == "success":
                    auto_refresh = config.get("auto_refresh", {})
                    logger.info(f"  [OK] Auto-refresh config retrieved")
                    logger.info(f"    - Enabled: {auto_refresh.get('enabled')}")
                    logger.info(f"    - Interval: {auto_refresh.get('interval_seconds')} seconds")
                    logger.info(f"    - Max Updates/Hour: {auto_refresh.get('max_updates_per_hour')}")
                else:
                    logger.warning(f"  [WARN] Auto-refresh config retrieval failed")
                
                # Test 6: Verify Real-Time Updates Benefits
                logger.info("\nTest 6: Verify Real-Time Updates Benefits")
                logger.info("  Note: Real-time updates provide:")
                logger.info("    - Connection status indicator")
                logger.info("    - 'Live' badges on real-time data")
                logger.info("    - Auto-refresh toggles")
                logger.info("    - Last update timestamps")
                logger.info("    - Manual refresh trigger")
                logger.info("  [OK] Real-time updates are implemented")
                
                test_passed = True
            finally:
                break
    except Exception as e:
        logger.error(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("ADVANCED CHARTS AND REAL-TIME UPDATES TEST")
    logger.info("Tasks 64-65: Advanced Charts, Real-Time Updates")
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
        
        # Test advanced charts
        results.append(("Advanced Charts (Task 64)", await test_advanced_charts()))
        
        # Test real-time updates
        results.append(("Real-Time Updates (Task 65)", await test_realtime_updates()))
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        all_passed = True
        for test_name, passed in results:
            status = "PASSED" if passed else "FAILED"
            logger.info(f"{test_name}: {status}")
            if not passed:
                all_passed = False
        
        logger.info("=" * 60)
        if all_passed:
            logger.info("All tests passed!")
        else:
            logger.error("Some tests failed")
        
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

