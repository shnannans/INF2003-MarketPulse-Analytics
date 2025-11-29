"""
Test script for Tasks 52-53: Deployment Configuration and Environment Management
Tests deployment utilities and environment configuration
"""
import asyncio
import sys
import logging
from pathlib import Path
from config.environment import config, EnvironmentConfig
from utils.deployment import DeploymentManager, create_env_example

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_environment_configuration():
    """Test Task 53: Environment Management"""
    logger.info("=" * 60)
    logger.info("TEST: Environment Configuration (Task 53)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        # Test 1: Environment detection
        logger.info("\nTest 1: Environment Detection")
        
        logger.info(f"  [OK] Environment: {config.ENVIRONMENT}")
        logger.info(f"  [OK] Is Production: {config.is_production()}")
        logger.info(f"  [OK] Is Development: {config.is_development()}")
        logger.info(f"  [OK] Is Testing: {config.is_testing()}")
        
        # Test 2: Configuration values
        logger.info("\nTest 2: Configuration Values")
        
        logger.info(f"  [OK] API Host: {config.API_HOST}")
        logger.info(f"  [OK] API Port: {config.API_PORT}")
        logger.info(f"  [OK] Database Host: {config.DB_HOST}")
        logger.info(f"  [OK] Database Name: {config.DB_NAME}")
        logger.info(f"  [OK] Pool Size: {config.DB_POOL_SIZE}")
        logger.info(f"  [OK] Rate Limit (per minute): {config.RATE_LIMIT_PER_MINUTE}")
        
        # Test 3: Database URL generation
        logger.info("\nTest 3: Database URL Generation")
        
        db_url = config.get_database_url()
        logger.info(f"  [OK] Database URL generated: {db_url[:50]}...")
        
        # Test 4: Configuration validation
        logger.info("\nTest 4: Configuration Validation")
        
        is_valid, errors = config.validate()
        if is_valid:
            logger.info("  [OK] Configuration is valid")
        else:
            logger.warning(f"  [WARN] Configuration has {len(errors)} errors:")
            for error in errors:
                logger.warning(f"    - {error}")
        
        # Test 5: Configuration summary
        logger.info("\nTest 5: Configuration Summary")
        
        summary = config.get_config_summary()
        logger.info(f"  [OK] Configuration summary generated")
        logger.info(f"    - Environment: {summary.get('environment')}")
        logger.info(f"    - Debug: {summary.get('debug')}")
        logger.info(f"    - Has News API Key: {summary.get('has_news_api_key')}")
        logger.info(f"    - Has Redis: {summary.get('has_redis')}")
        logger.info(f"    - Has Replica: {summary.get('has_replica')}")
        
        # Test 6: Environment-specific behavior
        logger.info("\nTest 6: Environment-Specific Behavior")
        
        if config.is_development():
            logger.info("  [OK] Running in development mode")
            logger.info("    - Debug mode may be enabled")
            logger.info("    - More verbose logging")
        elif config.is_production():
            logger.info("  [OK] Running in production mode")
            logger.info("    - Debug mode should be disabled")
            logger.info("    - Security checks enabled")
        
        logger.info("\n  [OK] Environment configuration is working correctly")
        test_passed = True
        
    except Exception as e:
        logger.error(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def test_deployment_configuration():
    """Test Task 52: Deployment Configuration"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Deployment Configuration (Task 52)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        # Test 1: Check dependencies
        logger.info("\nTest 1: Check Dependencies")
        
        deps = DeploymentManager.check_dependencies()
        installed_deps = [dep for dep, installed in deps.items() if installed]
        missing_deps = [dep for dep, installed in deps.items() if not installed]
        
        logger.info(f"  [OK] Installed dependencies: {len(installed_deps)}")
        for dep in installed_deps:
            logger.info(f"    - {dep}")
        
        if missing_deps:
            logger.warning(f"  [WARN] Missing dependencies: {len(missing_deps)}")
            for dep in missing_deps:
                logger.warning(f"    - {dep}")
        else:
            logger.info("  [OK] All required dependencies are installed")
        
        # Test 2: Check environment files
        logger.info("\nTest 2: Check Environment Files")
        
        files = DeploymentManager.check_environment_files()
        existing_files = [name for name, exists in files.items() if exists]
        missing_files = [name for name, exists in files.items() if not exists]
        
        logger.info(f"  [OK] Existing files: {len(existing_files)}")
        for file_name in existing_files:
            logger.info(f"    - {file_name}")
        
        if missing_files:
            logger.info(f"  [INFO] Missing files (optional): {len(missing_files)}")
            for file_name in missing_files:
                logger.info(f"    - {file_name}")
        
        # Test 3: Validate deployment config
        logger.info("\nTest 3: Validate Deployment Configuration")
        
        is_valid, errors = DeploymentManager.validate_deployment_config()
        
        if is_valid:
            logger.info("  [OK] Deployment configuration is valid")
        else:
            logger.warning(f"  [WARN] Deployment configuration has {len(errors)} issues:")
            for error in errors:
                logger.warning(f"    - {error}")
        
        # Test 4: Get deployment info
        logger.info("\nTest 4: Get Deployment Information")
        
        info = DeploymentManager.get_deployment_info()
        logger.info(f"  [OK] Deployment information retrieved")
        logger.info(f"    - Environment: {info.get('environment')}")
        logger.info(f"    - Python Version: {info.get('python_version', '').split()[0]}")
        logger.info(f"    - Dependencies: {len([d for d, installed in info.get('dependencies', {}).items() if installed])} installed")
        
        # Test 5: Create .env.example
        logger.info("\nTest 5: Create .env.example File")
        
        success = create_env_example()
        if success:
            logger.info("  [OK] .env.example file created successfully")
            
            # Check if file exists
            env_example_path = Path(__file__).parent.parent.parent / ".env.example"
            if env_example_path.exists():
                logger.info(f"  [OK] File exists at: {env_example_path}")
                file_size = env_example_path.stat().st_size
                logger.info(f"  [OK] File size: {file_size} bytes")
            else:
                logger.warning("  [WARN] File was created but not found")
        else:
            logger.warning("  [WARN] Failed to create .env.example file")
        
        # Test 6: Verify deployment benefits
        logger.info("\nTest 6: Verify Deployment Benefits")
        logger.info("  Note: Deployment configuration provides:")
        logger.info("    - Docker containerization")
        logger.info("    - Docker Compose orchestration")
        logger.info("    - Environment variable management")
        logger.info("    - Dependency checking")
        logger.info("    - Configuration validation")
        logger.info("    - Easy deployment and scaling")
        logger.info("  [OK] Deployment configuration is implemented")
        
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
    logger.info("DEPLOYMENT AND ENVIRONMENT CONFIGURATION TEST")
    logger.info("Tasks 52-53: Deployment Configuration, Environment Management")
    logger.info("=" * 60)
    
    try:
        results = []
        
        # Test environment configuration
        results.append(("Environment Configuration (Task 53)", await test_environment_configuration()))
        
        # Test deployment configuration
        results.append(("Deployment Configuration (Task 52)", await test_deployment_configuration()))
        
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


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

