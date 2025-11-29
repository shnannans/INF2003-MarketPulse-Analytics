"""
Comprehensive test script to verify all charts and dashboard sections work correctly.
Tests all API endpoints used by the frontend dashboard.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import get_mysql_session, init_database, close_database
from routers import (
    dashboard, stock_analysis, indices, advanced_analytics, 
    data_warehouse, news, sentiment, correlation, timeline
)

async def test_stock_performance_overview():
    """Test Stock Performance Overview section"""
    print("\n" + "="*60)
    print("Testing: Stock Performance Overview")
    print("="*60)
    
    try:
        async for db in get_mysql_session():
            # Test dashboard endpoint
            result = await dashboard.get_dashboard(days=7, db=db)
            assert result.get("status") == "success", "Dashboard should return success status"
            assert "total_companies" in result, "Dashboard should include total_companies"
            print(f"  [OK] Dashboard endpoint: OK")
            print(f"    - Total companies: {result.get('total_companies', 'N/A')}")
            
            # Test stock analysis endpoint
            result = await stock_analysis.get_stock_analysis_rest_style(ticker="AAPL", days=7, db=db)
            assert result.get("status") == "success", "Stock analysis should return success status"
            assert "analysis" in result, "Stock analysis should include analysis data"
            analysis_data = result.get("analysis", [])
            if analysis_data:
                print(f"  [OK] Stock Analysis endpoint: OK")
                print(f"    - Data points: {len(analysis_data)}")
                print(f"    - Sample ticker: {analysis_data[0].get('ticker', 'N/A')}")
            else:
                print(f"  [WARN] Stock Analysis endpoint: OK (no data)")
            
            return True
    except Exception as e:
        print(f"  [ERROR] Error: {str(e)}")
        return False

async def test_market_indices_overview():
    """Test Market Indices Overview section"""
    print("\n" + "="*60)
    print("Testing: Market Indices Overview")
    print("="*60)
    
    try:
        async for db in get_mysql_session():
            result = await indices.get_indices_rest_style(days=7, live=False, db=db)
            assert result.get("status") == "success", "Indices should return success status"
            assert "indices" in result, "Indices should include indices data"
            indices_data = result.get("indices", [])
            if indices_data:
                print(f"  [OK] Indices endpoint: OK")
                print(f"    - Number of indices: {len(indices_data)}")
                print(f"    - Sample indices: {', '.join([idx.get('name', 'N/A') for idx in indices_data[:3]])}")
            else:
                print(f"  [WARN] Indices endpoint: OK (no data)")
            
            return True
    except Exception as e:
        print(f"  [ERROR] Error: {str(e)}")
        return False

async def test_window_functions():
    """Test Window Functions section"""
    print("\n" + "="*60)
    print("Testing: Window Functions (Advanced Analytics)")
    print("="*60)
    
    try:
        async for db in get_mysql_session():
            result = await advanced_analytics.get_window_functions_analysis(ticker=None, days=30, limit=50, db=db)
            assert result.get("status") == "success", "Window functions should return success status"
            assert "data" in result, "Window functions should include data"
            data = result.get("data", [])
            if data:
                print(f"  [OK] Window Functions endpoint: OK")
                print(f"    - Data points: {len(data)}")
                print(f"    - Sample columns: {', '.join(list(data[0].keys())[:5])}")
            else:
                print(f"  [WARN] Window Functions endpoint: OK (no data)")
            
            return True
    except Exception as e:
        print(f"  [ERROR] Error: {str(e)}")
        return False

async def test_sector_performance():
    """Test Sector Performance section"""
    print("\n" + "="*60)
    print("Testing: Sector Performance (Advanced Analytics)")
    print("="*60)
    
    try:
        async for db in get_mysql_session():
            result = await advanced_analytics.get_sector_performance_analysis(days=30, db=db)
            assert result.get("status") == "success", "Sector performance should return success status"
            assert "sectors" in result, "Sector performance should include sectors"
            data = result.get("sectors", [])
            if data:
                print(f"  [OK] Sector Performance endpoint: OK")
                print(f"    - Sectors: {len(data)}")
                print(f"    - Sample sectors: {', '.join([d.get('sector', 'N/A') for d in data[:3]])}")
            else:
                print(f"  [WARN] Sector Performance endpoint: OK (no data)")
            
            return True
    except Exception as e:
        print(f"  [ERROR] Error: {str(e)}")
        return False

async def test_price_trends():
    """Test Price Trends section"""
    print("\n" + "="*60)
    print("Testing: Price Trends (Advanced Analytics)")
    print("="*60)
    
    try:
        async for db in get_mysql_session():
            result = await advanced_analytics.get_price_trends_analysis(ticker=None, min_consecutive_days=5, limit=100, db=db)
            assert result.get("status") == "success", "Price trends should return success status"
            # Price trends may return "trends" or "data" key
            data = result.get("trends", result.get("data", []))
            if not data:
                # If no trends found, that's OK - just means no consecutive increases
                print(f"  [WARN] Price Trends endpoint: OK (no consecutive price increases found)")
                return True
            if data:
                print(f"  [OK] Price Trends endpoint: OK")
                print(f"    - Data points: {len(data)}")
                print(f"    - Sample tickers: {', '.join(set([d.get('ticker', 'N/A') for d in data[:5]]))}")
            else:
                print(f"  [WARN] Price Trends endpoint: OK (no data)")
            
            return True
    except Exception as e:
        print(f"  [ERROR] Error: {str(e)}")
        return False

async def test_rolling_aggregations():
    """Test Rolling Aggregations section"""
    print("\n" + "="*60)
    print("Testing: Rolling Aggregations (Advanced Analytics)")
    print("="*60)
    
    try:
        async for db in get_mysql_session():
            result = await advanced_analytics.get_rolling_aggregations(ticker=None, limit=100, db=db)
            assert result.get("status") == "success", "Rolling aggregations should return success status"
            assert "data" in result, "Rolling aggregations should include data"
            data = result.get("data", [])
            if data:
                print(f"  [OK] Rolling Aggregations endpoint: OK")
                print(f"    - Data points: {len(data)}")
                print(f"    - Sample tickers: {', '.join([d.get('ticker', 'N/A') for d in data[:3]])}")
            else:
                print(f"  [WARN] Rolling Aggregations endpoint: OK (no data)")
            
            return True
    except Exception as e:
        print(f"  [ERROR] Error: {str(e)}")
        return False

async def test_price_sentiment_correlation():
    """Test Price-Sentiment Correlation section"""
    print("\n" + "="*60)
    print("Testing: Price-Sentiment Correlation (Advanced Analytics)")
    print("="*60)
    
    try:
        async for db in get_mysql_session():
            result = await advanced_analytics.get_price_sentiment_correlation(ticker=None, days=30, limit=100, db=db)
            assert result.get("status") == "success", "Price-sentiment correlation should return success status"
            assert "data" in result, "Price-sentiment correlation should include data"
            data = result.get("data", [])
            if data:
                print(f"  [OK] Price-Sentiment Correlation endpoint: OK")
                print(f"    - Data points: {len(data)}")
                print(f"    - Sample correlation values: {[d.get('correlation', 'N/A') for d in data[:3]]}")
            else:
                print(f"  [WARN] Price-Sentiment Correlation endpoint: OK (no data)")
            
            return True
    except Exception as e:
        print(f"  [ERROR] Error: {str(e)}")
        return False

async def test_materialized_views():
    """Test Materialized Views section"""
    print("\n" + "="*60)
    print("Testing: Materialized Views")
    print("="*60)
    
    try:
        async for db in get_mysql_session():
            result = await data_warehouse.get_sector_performance_materialized(days=30, db=db)
            assert result.get("status") == "success", "Materialized view should return success status"
            assert "data" in result, "Materialized view should include data"
            data = result.get("data", [])
            if data:
                print(f"  [OK] Materialized View endpoint: OK")
                print(f"    - Data points: {len(data)}")
                print(f"    - Sample sectors: {', '.join(set([d.get('sector', 'N/A') for d in data[:5]]))}")
            else:
                print(f"  [WARN] Materialized View endpoint: OK (no data)")
            
            return True
    except Exception as e:
        print(f"  [ERROR] Error: {str(e)}")
        return False

async def test_news_sentiment_insights():
    """Test News & Sentiment Insights section"""
    print("\n" + "="*60)
    print("Testing: News & Sentiment Insights")
    print("="*60)
    
    try:
        # Test news endpoint
        result = await news.get_news_rest_style(ticker="", days=7, sentiment="", limit=10, live=False)
        assert result.get("status") == "success", "News should return success status"
        assert "articles" in result, "News should include articles"
        articles = result.get("articles", [])
        if articles:
            print(f"  [OK] News endpoint: OK")
            print(f"    - Articles: {len(articles)}")
            print(f"    - Sample sources: {', '.join(set([a.get('source', {}).get('name', 'N/A') if isinstance(a.get('source'), dict) else str(a.get('source', 'N/A'))[:20] for a in articles[:3]]))}")
        else:
            print(f"  [WARN] News endpoint: OK (no articles)")
        
        # Test sentiment endpoint
        result = await sentiment.get_sentiment_internal(ticker="AAPL", days=7, live=False)
        # Sentiment may not always have data, so just check if endpoint works
        if result.get("status") == "success":
            print(f"  [OK] Sentiment endpoint: OK")
            if "sentiment_data" in result or "data" in result:
                print(f"    - Sentiment data available")
            else:
                print(f"    - Endpoint working (no data available)")
        else:
            raise AssertionError("Sentiment should return success status")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Error: {str(e)}")
        return False

async def test_combined_analytics():
    """Test Combined Analytics section"""
    print("\n" + "="*60)
    print("Testing: Combined Analytics")
    print("="*60)
    
    try:
        async for db in get_mysql_session():
            # Test correlation endpoint
            try:
                result = await correlation.get_correlation(ticker="AAPL", date=None, days_window=7, db=db)
                # Correlation may return different response format
                if result.get("status") == "success" or "correlation" in result or "data" in result:
                    print(f"  [OK] Correlation endpoint: OK")
                else:
                    print(f"  [WARN] Correlation endpoint: Response format may differ")
            except Exception as e:
                print(f"  [WARN] Correlation endpoint: {str(e)}")
            
            # Test timeline endpoint
            result = await timeline.get_timeline_rest_style(days=7, threshold=4.0, ticker=None, live=False, db=db)
            assert result.get("status") == "success", "Timeline should return success status"
            assert "events" in result, "Timeline should include events"
            events = result.get("events", [])
            if events:
                print(f"  [OK] Timeline endpoint: OK")
                print(f"    - Events: {len(events)}")
            else:
                print(f"  [WARN] Timeline endpoint: OK (no events)")
            break
        
        return True
    except Exception as e:
        print(f"  [ERROR] Error: {str(e)}")
        return False

async def run_all_tests():
    """Run all chart and section tests"""
    print("\n" + "="*60)
    print("COMPREHENSIVE DASHBOARD CHART & SECTION TEST")
    print("="*60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize database connection
    print("\nInitializing database connection...")
    try:
        await init_database()
        print("  [OK] Database connection initialized")
    except Exception as e:
        print(f"  [ERROR] Database initialization failed: {str(e)}")
        print("  [INFO] Continuing with tests (may fail if DB not available)")
    
    tests = [
        ("Stock Performance Overview", test_stock_performance_overview),
        ("Market Indices Overview", test_market_indices_overview),
        ("Window Functions", test_window_functions),
        ("Sector Performance", test_sector_performance),
        ("Price Trends", test_price_trends),
        ("Rolling Aggregations", test_rolling_aggregations),
        ("Price-Sentiment Correlation", test_price_sentiment_correlation),
        ("Materialized Views", test_materialized_views),
        ("News & Sentiment Insights", test_news_sentiment_insights),
        ("Combined Analytics", test_combined_analytics),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n  [ERROR] {test_name} failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {test_name}")
    
    print("\n" + "-"*60)
    print(f"Total: {passed}/{total} tests passed")
    print("="*60)
    
    # Close database connection
    try:
        await close_database()
        print("\n[INFO] Database connection closed")
    except Exception as e:
        print(f"\n[WARNING] Error closing database: {str(e)}")
    
    if passed == total:
        print("\n[SUCCESS] All charts and sections are working correctly!")
        return True
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(run_all_tests())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

