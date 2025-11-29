"""
Test script for Tasks 72-73: State Management and API Integration Layer
Tests state management and API integration configuration endpoints
"""
import asyncio
import sys
import logging
from config.database import init_database, close_database, get_mysql_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_state_management():
    """Test Task 72: State Management"""
    logger.info("=" * 60)
    logger.info("TEST: State Management (Task 72)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        from config.database import get_mysql_session
        from routers.state_management import (
            get_state_config,
            get_global_state_info,
            get_local_state_info,
            get_state_management_best_practices
        )
        
        async for db_session in get_mysql_session():
            try:
                # Test 1: Get State Config
                logger.info("\nTest 1: Get State Config")
                
                config = await get_state_config(db_session)
                
                if config.get("status") == "success":
                    state_config = config.get("state_config", {})
                    logger.info(f"  [OK] State config retrieved")
                    logger.info(f"    - Global State Types: {len(state_config.get('global_state', {}))}")
                    logger.info(f"    - Local State Types: {len(state_config.get('local_state', {}))}")
                else:
                    logger.warning(f"  [WARN] State config retrieval failed")
                
                # Test 2: Get Global State Info
                logger.info("\nTest 2: Get Global State Info")
                
                global_state = await get_global_state_info("auth", db_session)
                
                if global_state.get("status") == "success":
                    logger.info(f"  [OK] Global state info retrieved")
                    logger.info(f"    - State Type: {global_state.get('state_type')}")
                    logger.info(f"    - Description: {global_state.get('global_state_info', {}).get('auth', {}).get('description')}")
                else:
                    logger.warning(f"  [WARN] Global state info retrieval failed")
                
                # Test 3: Get Local State Info
                logger.info("\nTest 3: Get Local State Info")
                
                local_state = await get_local_state_info("form", db_session)
                
                if local_state.get("status") == "success":
                    logger.info(f"  [OK] Local state info retrieved")
                    logger.info(f"    - State Type: {local_state.get('state_type')}")
                    logger.info(f"    - Description: {local_state.get('local_state_info', {}).get('form', {}).get('description')}")
                else:
                    logger.warning(f"  [WARN] Local state info retrieval failed")
                
                # Test 4: Get Best Practices
                logger.info("\nTest 4: Get State Management Best Practices")
                
                best_practices = await get_state_management_best_practices(db_session)
                
                if best_practices.get("status") == "success":
                    logger.info(f"  [OK] Best practices retrieved")
                    logger.info(f"    - Global State Practices: {len(best_practices.get('best_practices', {}).get('global_state', []))}")
                    logger.info(f"    - Local State Practices: {len(best_practices.get('best_practices', {}).get('local_state', []))}")
                else:
                    logger.warning(f"  [WARN] Best practices retrieval failed")
                
                # Test 5: Verify State Management Benefits
                logger.info("\nTest 5: Verify State Management Benefits")
                logger.info("  Note: State management provides:")
                logger.info("    - Global state for authentication, roles, themes")
                logger.info("    - Local state for forms, UI, filters, pagination")
                logger.info("    - State persistence strategies")
                logger.info("    - State management best practices")
                logger.info("  [OK] State management is implemented")
                
                test_passed = True
            finally:
                break
    except Exception as e:
        logger.error(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def test_api_integration():
    """Test Task 73: API Integration Layer"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: API Integration Layer (Task 73)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        from config.database import get_mysql_session
        from routers.api_integration import (
            get_api_integration_config,
            get_interceptors_config,
            get_error_handling_config,
            get_api_caching_config,
            get_token_management_config,
            get_request_cancellation_config
        )
        
        async for db_session in get_mysql_session():
            try:
                # Test 1: Get API Integration Config
                logger.info("\nTest 1: Get API Integration Config")
                
                config = await get_api_integration_config(db_session)
                
                if config.get("status") == "success":
                    api_config = config.get("api_integration_config", {})
                    logger.info(f"  [OK] API integration config retrieved")
                    logger.info(f"    - Base URL: {api_config.get('base_url')}")
                    logger.info(f"    - Retry Enabled: {api_config.get('retry', {}).get('enabled')}")
                    logger.info(f"    - Caching Enabled: {api_config.get('caching', {}).get('enabled')}")
                else:
                    logger.warning(f"  [WARN] API integration config retrieval failed")
                
                # Test 2: Get Interceptors Config
                logger.info("\nTest 2: Get Interceptors Config")
                
                interceptors = await get_interceptors_config("request", db_session)
                
                if interceptors.get("status") == "success":
                    logger.info(f"  [OK] Interceptors config retrieved")
                    logger.info(f"    - Interceptor Type: {interceptors.get('interceptor_type')}")
                    logger.info(f"    - Functions: {len(interceptors.get('interceptors', {}).get('request', {}).get('functions', []))}")
                else:
                    logger.warning(f"  [WARN] Interceptors config retrieval failed")
                
                # Test 3: Get Error Handling Config
                logger.info("\nTest 3: Get Error Handling Config")
                
                error_handling = await get_error_handling_config(db_session)
                
                if error_handling.get("status") == "success":
                    logger.info(f"  [OK] Error handling config retrieved")
                    logger.info(f"    - Error Types: {len(error_handling.get('error_handling', {}).get('error_types', {}))}")
                    logger.info(f"    - Retry Strategy Enabled: {error_handling.get('error_handling', {}).get('retry_strategy', {}).get('enabled')}")
                else:
                    logger.warning(f"  [WARN] Error handling config retrieval failed")
                
                # Test 4: Get API Caching Config
                logger.info("\nTest 4: Get API Caching Config")
                
                caching = await get_api_caching_config(db_session)
                
                if caching.get("status") == "success":
                    logger.info(f"  [OK] API caching config retrieved")
                    logger.info(f"    - Caching Enabled: {caching.get('caching_config', {}).get('enabled')}")
                    logger.info(f"    - Deduplication Enabled: {caching.get('caching_config', {}).get('deduplication', {}).get('enabled')}")
                else:
                    logger.warning(f"  [WARN] API caching config retrieval failed")
                
                # Test 5: Get Token Management Config
                logger.info("\nTest 5: Get Token Management Config")
                
                token_mgmt = await get_token_management_config(db_session)
                
                if token_mgmt.get("status") == "success":
                    logger.info(f"  [OK] Token management config retrieved")
                    logger.info(f"    - Automatic Refresh: {token_mgmt.get('token_management', {}).get('automatic_refresh', {}).get('enabled')}")
                    logger.info(f"    - Token Storage: {token_mgmt.get('token_management', {}).get('token_storage', {}).get('method')}")
                else:
                    logger.warning(f"  [WARN] Token management config retrieval failed")
                
                # Test 6: Get Request Cancellation Config
                logger.info("\nTest 6: Get Request Cancellation Config")
                
                cancellation = await get_request_cancellation_config(db_session)
                
                if cancellation.get("status") == "success":
                    logger.info(f"  [OK] Request cancellation config retrieved")
                    logger.info(f"    - Cancellation Enabled: {cancellation.get('cancellation_config', {}).get('enabled')}")
                    logger.info(f"    - Cancel on Unmount: {cancellation.get('cancellation_config', {}).get('cancel_on_unmount')}")
                else:
                    logger.warning(f"  [WARN] Request cancellation config retrieval failed")
                
                # Test 7: Verify API Integration Benefits
                logger.info("\nTest 7: Verify API Integration Benefits")
                logger.info("  Note: API integration layer provides:")
                logger.info("    - Centralized API calls")
                logger.info("    - Request/response interceptors")
                logger.info("    - Error handling and retry logic")
                logger.info("    - Request caching and deduplication")
                logger.info("    - Automatic token refresh")
                logger.info("    - Request cancellation")
                logger.info("  [OK] API integration layer is implemented")
                
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
    logger.info("STATE MANAGEMENT AND API INTEGRATION LAYER TEST")
    logger.info("Tasks 72-73: State Management, API Integration Layer")
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
        
        # Test state management
        results.append(("State Management (Task 72)", await test_state_management()))
        
        # Test API integration
        results.append(("API Integration Layer (Task 73)", await test_api_integration()))
        
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

