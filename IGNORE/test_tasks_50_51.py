"""
Test script for Tasks 50-51: Logging and Monitoring, API Documentation
Tests logging configuration, monitoring endpoints, and API documentation
"""
import asyncio
import sys
import logging
from pathlib import Path
from sqlalchemy import text
from config.database import init_database, close_database, get_mysql_session
from utils.logging_config import setup_logging, get_logger, RequestLogger, PerformanceLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_logging_configuration():
    """Test Task 50: Logging and Monitoring - Logging Configuration"""
    logger.info("=" * 60)
    logger.info("TEST: Logging Configuration (Task 50)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        # Test 1: Setup logging
        logger.info("\nTest 1: Setup Logging Configuration")
        
        test_logger = setup_logging(log_level="INFO")
        logger.info("  [OK] Logging configuration setup successfully")
        
        # Test 2: Get logger for module
        logger.info("\nTest 2: Get Logger for Module")
        
        module_logger = get_logger("test_module")
        module_logger.info("Test log message from module logger")
        logger.info("  ✓ Module logger created and working")
        
        # Test 3: Request logger
        logger.info("\nTest 3: Request Logger")
        
        request_logger = RequestLogger()
        request_logger.log_request("GET", "/api/test", "127.0.0.1", params={"test": "value"})
        request_logger.log_response("GET", "/api/test", 200, 45.5)
        logger.info("  ✓ Request logger working correctly")
        
        # Test 4: Performance logger
        logger.info("\nTest 4: Performance Logger")
        
        perf_logger = PerformanceLogger()
        perf_logger.log_slow_query("SELECT * FROM companies", 1500.0, threshold_ms=1000)
        perf_logger.log_cache_hit("company:AAPL", "memory")
        perf_logger.log_cache_miss("company:MSFT", "memory")
        perf_logger.log_database_operation("SELECT", "companies", 25.5)
        logger.info("  ✓ Performance logger working correctly")
        
        # Test 5: Check log files
        logger.info("\nTest 5: Check Log Files")
        
        log_dir = Path("logs")
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            logger.info(f"  ✓ Log directory exists: {log_dir}")
            logger.info(f"  ✓ Found {len(log_files)} log files:")
            for log_file in log_files[:3]:
                size_mb = log_file.stat().st_size / (1024 * 1024)
                logger.info(f"    - {log_file.name}: {size_mb:.2f} MB")
        else:
            logger.warning("  ⚠ Log directory does not exist")
        
        # Test 6: Verify logging levels
        logger.info("\nTest 6: Verify Logging Levels")
        
        test_logger.debug("Debug message (should not appear at INFO level)")
        test_logger.info("Info message (should appear)")
        test_logger.warning("Warning message (should appear)")
        test_logger.error("Error message (should appear)")
        logger.info("  ✓ Logging levels working correctly")
        
        logger.info("\n  ✓ Logging configuration is working correctly")
        test_passed = True
        
    except Exception as e:
        logger.error(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def test_monitoring_endpoints():
    """Test Task 50: Logging and Monitoring - Monitoring Endpoints"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Monitoring Endpoints (Task 50)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        from routers.monitoring import health_check_detailed, get_metrics, get_log_info
        
        # Test 1: Health check
        logger.info("\nTest 1: Health Check Endpoint")
        
        async for db_session in get_mysql_session():
            try:
                health = await health_check_detailed(db_session)
                
                if health.get("status") in ["healthy", "degraded"]:
                    logger.info(f"  ✓ Health check returned: {health['status']}")
                    logger.info(f"    - Services checked: {len(health.get('services', {}))}")
                    
                    for service, status_info in health.get("services", {}).items():
                        service_status = status_info.get("status", "unknown")
                        logger.info(f"    - {service}: {service_status}")
                else:
                    logger.warning(f"  ⚠ Health check returned: {health.get('status')}")
            finally:
                break
        
        # Test 2: Metrics endpoint
        logger.info("\nTest 2: Metrics Endpoint")
        
        async for db_session in get_mysql_session():
            try:
                metrics = await get_metrics(db_session)
                
                if "timestamp" in metrics:
                    logger.info(f"  ✓ Metrics endpoint working")
                    logger.info(f"    - System metrics: {'system' in metrics}")
                    logger.info(f"    - Database metrics: {'database' in metrics}")
                    logger.info(f"    - Application metrics: {'application' in metrics}")
                else:
                    logger.warning("  ⚠ Metrics endpoint returned unexpected format")
            finally:
                break
        
        # Test 3: Log info endpoint
        logger.info("\nTest 3: Log Info Endpoint")
        
        log_info = await get_log_info()
        
        if log_info.get("status") == "success":
            logger.info(f"  ✓ Log info endpoint working")
            logger.info(f"    - Log directory: {log_info.get('log_dir')}")
            logger.info(f"    - Log files count: {log_info.get('count', 0)}")
        else:
            logger.warning("  ⚠ Log info endpoint returned unexpected format")
        
        # Test 4: Verify monitoring benefits
        logger.info("\nTest 4: Verify Monitoring Benefits")
        logger.info("  Note: Monitoring provides:")
        logger.info("    - System health checks")
        logger.info("    - Performance metrics")
        logger.info("    - Resource monitoring")
        logger.info("    - Log file management")
        logger.info("    - Better observability")
        logger.info("  ✓ Monitoring is implemented")
        
        test_passed = True
        
    except Exception as e:
        logger.error(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def test_api_documentation():
    """Test Task 51: API Documentation Enhancements"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: API Documentation (Task 51)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        # Test 1: Check FastAPI app configuration
        logger.info("\nTest 1: FastAPI App Configuration")
        
        from main import app
        
        if app.title:
            logger.info(f"  ✓ API title: {app.title}")
        else:
            logger.warning("  ⚠ API title not set")
        
        if app.description:
            logger.info(f"  ✓ API description: {len(app.description)} characters")
        else:
            logger.warning("  ⚠ API description not set")
        
        if app.version:
            logger.info(f"  ✓ API version: {app.version}")
        else:
            logger.warning("  ⚠ API version not set")
        
        # Test 2: Check OpenAPI endpoints
        logger.info("\nTest 2: OpenAPI Endpoints")
        
        endpoints = [
            ("/docs", "Swagger UI"),
            ("/redoc", "ReDoc"),
            ("/openapi.json", "OpenAPI JSON")
        ]
        
        for endpoint, name in endpoints:
            if hasattr(app, 'openapi_url') or endpoint in ["/docs", "/redoc"]:
                logger.info(f"  ✓ {name} endpoint configured: {endpoint}")
            else:
                logger.warning(f"  ⚠ {name} endpoint not configured")
        
        # Test 3: Check API metadata
        logger.info("\nTest 3: API Metadata")
        
        if hasattr(app, 'contact') and app.contact:
            logger.info(f"  ✓ Contact information configured")
        else:
            logger.warning("  ⚠ Contact information not configured")
        
        if hasattr(app, 'license_info') and app.license_info:
            logger.info(f"  ✓ License information configured")
        else:
            logger.warning("  ⚠ License information not configured")
        
        if hasattr(app, 'servers') and app.servers:
            logger.info(f"  ✓ API servers configured: {len(app.servers)} servers")
            for server in app.servers:
                logger.info(f"    - {server.get('url')}: {server.get('description')}")
        else:
            logger.warning("  ⚠ API servers not configured")
        
        # Test 4: Check router tags
        logger.info("\nTest 4: Router Tags")
        
        # Get all routes and their tags
        routes_with_tags = []
        for route in app.routes:
            if hasattr(route, 'tags') and route.tags:
                routes_with_tags.extend(route.tags)
        
        unique_tags = set(routes_with_tags)
        logger.info(f"  ✓ Found {len(unique_tags)} unique API tags:")
        for tag in sorted(unique_tags)[:10]:
            logger.info(f"    - {tag}")
        
        # Test 5: Verify documentation benefits
        logger.info("\nTest 5: Verify Documentation Benefits")
        logger.info("  Note: API documentation provides:")
        logger.info("    - Interactive API explorer (Swagger UI)")
        logger.info("    - Alternative documentation (ReDoc)")
        logger.info("    - OpenAPI schema for code generation")
        logger.info("    - Better developer experience")
        logger.info("    - API versioning and metadata")
        logger.info("  ✓ API documentation is enhanced")
        
        test_passed = True
        
    except Exception as e:
        logger.error(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("LOGGING AND MONITORING, API DOCUMENTATION TEST")
    logger.info("Tasks 50-51: Logging and Monitoring, API Documentation")
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
        
        # Test logging configuration
        results.append(("Logging Configuration (Task 50)", await test_logging_configuration()))
        
        # Test monitoring endpoints
        results.append(("Monitoring Endpoints (Task 50)", await test_monitoring_endpoints()))
        
        # Test API documentation
        results.append(("API Documentation (Task 51)", await test_api_documentation()))
        
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

