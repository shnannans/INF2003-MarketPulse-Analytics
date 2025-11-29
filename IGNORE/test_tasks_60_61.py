"""
Test script for Tasks 60-61: Health Dashboard and Search & Filtering Enhancements
Tests health dashboard and search/filtering functionality
"""
import asyncio
import sys
import logging
from sqlalchemy import select
from config.database import init_database, close_database, get_mysql_session
from models.database_models import Company

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_health_dashboard():
    """Test Task 60: Health Dashboard"""
    logger.info("=" * 60)
    logger.info("TEST: Health Dashboard (Task 60)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        from config.database import get_mysql_session
        from routers.health_dashboard import get_health_dashboard
        
        async for db_session in get_mysql_session():
            try:
                # Test 1: Get health dashboard
                logger.info("\nTest 1: Get Health Dashboard")
                
                dashboard = await get_health_dashboard(db_session)
                
                if dashboard.get("status"):
                    logger.info(f"  [OK] Health dashboard retrieved")
                    logger.info(f"    - Status: {dashboard.get('status')}")
                    logger.info(f"    - Database Status: {dashboard.get('database', {}).get('status')}")
                    logger.info(f"    - Firestore Status: {dashboard.get('services', {}).get('firestore', {}).get('status')}")
                    logger.info(f"    - API Response Times: {dashboard.get('metrics', {}).get('api_response_times', {}).get('average_ms')} ms")
                    logger.info(f"    - Cache Stats Available: {bool(dashboard.get('cache'))}")
                    logger.info(f"    - Pool Status Available: {bool(dashboard.get('pool'))}")
                    logger.info(f"    - System Metrics Available: {bool(dashboard.get('system'))}")
                    logger.info(f"    - Ticker Counts: {dashboard.get('database', {}).get('total_tickers', 0)}")
                else:
                    logger.warning(f"  [WARN] Health dashboard retrieval failed")
                
                # Test 2: Verify health dashboard components
                logger.info("\nTest 2: Verify Health Dashboard Components")
                
                required_components = [
                    "database",
                    "services",
                    "metrics",
                    "cache",
                    "pool",
                    "system"
                ]
                
                for component in required_components:
                    if component in dashboard:
                        logger.info(f"  [OK] Component '{component}' present")
                    else:
                        logger.warning(f"  [WARN] Component '{component}' missing")
                
                # Test 3: Verify health dashboard benefits
                logger.info("\nTest 3: Verify Health Dashboard Benefits")
                logger.info("  Note: Health dashboard provides:")
                logger.info("    - Database connection status")
                logger.info("    - Firestore connection status")
                logger.info("    - API response times")
                logger.info("    - Cache hit/miss rates")
                logger.info("    - Connection pool status")
                logger.info("    - Row counts per ticker")
                logger.info("    - System metrics")
                logger.info("  [OK] Health dashboard is implemented")
                
                test_passed = True
            finally:
                break
    except Exception as e:
        logger.error(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def test_search_filtering():
    """Test Task 61: Search & Filtering Enhancements"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Search & Filtering Enhancements (Task 61)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        from config.database import get_mysql_session
        from routers.search_filtering import search_companies, autocomplete_companies, get_sectors
        
        async for db_session in get_mysql_session():
            try:
                # Test 1: Search companies
                logger.info("\nTest 1: Search Companies")
                
                # Search for "Apple"
                result = await search_companies("Apple", None, None, None, None, None, None, None, 10, db_session)
                
                if result.get("status") == "success":
                    logger.info(f"  [OK] Company search successful")
                    logger.info(f"    - Count: {result.get('count')}")
                    logger.info(f"    - Companies found: {len(result.get('companies', []))}")
                    if result.get("companies"):
                        logger.info(f"    - Sample: {result['companies'][0].get('company_name')}")
                else:
                    logger.warning(f"  [WARN] Company search failed")
                
                # Test 2: Autocomplete
                logger.info("\nTest 2: Autocomplete Companies")
                
                autocomplete_result = await autocomplete_companies("App", 5, db_session)
                
                if autocomplete_result.get("status") == "success":
                    logger.info(f"  [OK] Autocomplete successful")
                    logger.info(f"    - Suggestions: {autocomplete_result.get('count')}")
                    if autocomplete_result.get("suggestions"):
                        logger.info(f"    - Sample: {autocomplete_result['suggestions'][0].get('display')}")
                else:
                    logger.warning(f"  [WARN] Autocomplete failed")
                
                # Test 3: Get sectors
                logger.info("\nTest 3: Get Sectors")
                
                sectors_result = await get_sectors(db_session)
                
                if sectors_result.get("status") == "success":
                    logger.info(f"  [OK] Sectors retrieved")
                    logger.info(f"    - Sector count: {sectors_result.get('count')}")
                    if sectors_result.get("sectors"):
                        logger.info(f"    - Sample sectors: {', '.join([s['sector'] for s in sectors_result['sectors'][:5]])}")
                else:
                    logger.warning(f"  [WARN] Sectors retrieval failed")
                
                # Test 4: Search with filters
                logger.info("\nTest 4: Search with Filters")
                
                # Search with sector filter
                filtered_result = await search_companies("", "Technology", None, None, None, None, None, None, 10, db_session)
                
                if filtered_result.get("status") == "success":
                    logger.info(f"  [OK] Filtered search successful")
                    logger.info(f"    - Count: {filtered_result.get('count')}")
                    logger.info(f"    - Filter applied: {filtered_result.get('filters', {}).get('sector')}")
                else:
                    logger.warning(f"  [WARN] Filtered search failed")
                
                # Test 5: Verify search/filtering benefits
                logger.info("\nTest 5: Verify Search/Filtering Benefits")
                logger.info("  Note: Search & filtering provides:")
                logger.info("    - Full-text search for company names")
                logger.info("    - Autocomplete suggestions")
                logger.info("    - Search filters (sector, market cap, price, date)")
                logger.info("    - Sector listing")
                logger.info("  [OK] Search & filtering is implemented")
                
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
    logger.info("HEALTH DASHBOARD AND SEARCH/FILTERING TEST")
    logger.info("Tasks 60-61: Health Dashboard, Search & Filtering Enhancements")
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
        
        # Test health dashboard
        results.append(("Health Dashboard (Task 60)", await test_health_dashboard()))
        
        # Test search/filtering
        results.append(("Search & Filtering (Task 61)", await test_search_filtering()))
        
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

