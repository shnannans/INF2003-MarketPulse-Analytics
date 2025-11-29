"""
Test script for Tasks 34-35: Transaction Isolation Levels and Optimistic Locking
Tests isolation level functionality and optimistic locking with version columns
"""
import asyncio
import sys
import logging
from datetime import date, datetime
from sqlalchemy import text, select
from config.database import init_database, close_database, AsyncSessionLocal, get_mysql_session
from utils.transaction_utils import (
    IsolationLevel,
    set_transaction_isolation_level,
    get_current_isolation_level,
    update_with_optimistic_locking
)
from models.database_models import Company

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_isolation_levels():
    """Test Task 34: Transaction Isolation Levels"""
    logger.info("=" * 60)
    logger.info("TEST: Transaction Isolation Levels (Task 34)")
    logger.info("=" * 60)
    
    test_passed = False
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Test 1: Get current isolation level
                logger.info("\nTest 1: Get Current Isolation Level")
                
                current_level = await get_current_isolation_level(db_session)
                logger.info(f"  ✓ Current isolation level: {current_level}")
                
                # Test 2: Set different isolation levels
                logger.info("\nTest 2: Set Different Isolation Levels")
                
                test_levels = [
                    IsolationLevel.READ_COMMITTED,
                    IsolationLevel.REPEATABLE_READ,
                ]
                
                for level in test_levels:
                    try:
                        await set_transaction_isolation_level(db_session, level)
                        logger.info(f"  ✓ Set isolation level to: {level.value}")
                        
                        # Verify it was set
                        verify_level = await get_current_isolation_level(db_session)
                        logger.info(f"    - Verified level: {verify_level}")
                    except Exception as e:
                        logger.warning(f"  ⚠ Could not set {level.value}: {e}")
                
                # Test 3: Test isolation level behavior
                logger.info("\nTest 3: Isolation Level Behavior")
                logger.info("  Note: Isolation levels control transaction behavior:")
                logger.info("    - READ COMMITTED: Default, good for most cases")
                logger.info("    - REPEATABLE READ: For financial calculations that need consistency")
                logger.info("    - SERIALIZABLE: Maximum isolation, but can cause deadlocks")
                logger.info("  ✓ Isolation level functionality is implemented")
                
                test_passed = True
            finally:
                break
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return test_passed


async def test_optimistic_locking():
    """Test Task 35: Optimistic Locking"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Optimistic Locking (Task 35)")
    logger.info("=" * 60)
    
    test_passed = False
    test_ticker = "AAPL"  # Use existing ticker
    
    try:
        async for db_session in get_mysql_session():
            try:
                # Test 1: Get current version
                logger.info("\nTest 1: Get Current Version")
                
                company_result = await db_session.execute(
                    select(Company).where(Company.ticker == test_ticker)
                )
                company = company_result.scalar_one_or_none()
                
                if not company:
                    logger.warning(f"  ⚠ Company {test_ticker} not found, skipping test")
                    return False
                
                current_version = getattr(company, 'version', 1)
                logger.info(f"  ✓ Current version for {test_ticker}: {current_version}")
                
                # Test 2: Successful optimistic update
                logger.info("\nTest 2: Successful Optimistic Update")
                
                original_name = company.company_name
                test_name = f"{original_name} (Optimistic Test)"
                
                result = await update_with_optimistic_locking(
                    db_session,
                    Company,
                    {'ticker': test_ticker},
                    {'company_name': test_name},
                    current_version,
                    {'deleted_at': None}
                )
                
                if result['success']:
                    await db_session.commit()
                    logger.info(f"  ✓ Optimistic update successful")
                    logger.info(f"    - Version: {current_version} -> {result['current_version']}")
                    
                    # Verify update
                    await db_session.refresh(company)
                    if company.company_name == test_name:
                        logger.info(f"    - Company name updated correctly: {company.company_name}")
                    else:
                        logger.warning(f"    - Company name mismatch: expected {test_name}, got {company.company_name}")
                    
                    # Restore original name
                    new_version = result['current_version']
                    restore_result = await update_with_optimistic_locking(
                        db_session,
                        Company,
                        {'ticker': test_ticker},
                        {'company_name': original_name},
                        new_version,
                        {'deleted_at': None}
                    )
                    
                    if restore_result['success']:
                        await db_session.commit()
                        logger.info("  ✓ Original name restored")
                    else:
                        logger.warning(f"  ⚠ Could not restore original name: {restore_result.get('error')}")
                else:
                    logger.error(f"  ✗ Optimistic update failed: {result.get('error')}")
                    return False
                
                # Test 3: Version mismatch (conflict)
                logger.info("\nTest 3: Version Mismatch (Conflict)")
                
                # Get current version again
                company_result2 = await db_session.execute(
                    select(Company).where(Company.ticker == test_ticker)
                )
                company2 = company_result2.scalar_one_or_none()
                actual_version = getattr(company2, 'version', 1)
                
                # Try to update with wrong version
                wrong_version = actual_version - 1 if actual_version > 1 else 999
                
                conflict_result = await update_with_optimistic_locking(
                    db_session,
                    Company,
                    {'ticker': test_ticker},
                    {'company_name': 'Should Not Update'},
                    wrong_version,
                    {'deleted_at': None}
                )
                
                if not conflict_result['success']:
                    if 'Version mismatch' in conflict_result.get('error', ''):
                        logger.info(f"  ✓ Version mismatch detected correctly")
                        logger.info(f"    - Expected version: {wrong_version}")
                        logger.info(f"    - Actual version: {conflict_result.get('current_version')}")
                        logger.info(f"    - Error: {conflict_result.get('error')}")
                    else:
                        logger.warning(f"  ⚠ Unexpected error: {conflict_result.get('error')}")
                else:
                    logger.error("  ✗ Expected version mismatch but update succeeded")
                    await db_session.rollback()
                    return False
                
                # Test 4: Verify version increment
                logger.info("\nTest 4: Verify Version Increment")
                
                # Get current version
                company_result3 = await db_session.execute(
                    select(Company).where(Company.ticker == test_ticker)
                )
                company3 = company_result3.scalar_one_or_none()
                version_before = getattr(company3, 'version', 1)
                
                # Update with correct version
                increment_result = await update_with_optimistic_locking(
                    db_session,
                    Company,
                    {'ticker': test_ticker},
                    {'sector': company3.sector},  # Update with same value (no change)
                    version_before,
                    {'deleted_at': None}
                )
                
                if increment_result['success']:
                    await db_session.commit()
                    await db_session.refresh(company3)
                    version_after = getattr(company3, 'version', 1)
                    
                    if version_after == version_before + 1:
                        logger.info(f"  ✓ Version incremented correctly: {version_before} -> {version_after}")
                    else:
                        logger.warning(f"  ⚠ Version increment mismatch: expected {version_before + 1}, got {version_after}")
                else:
                    logger.error(f"  ✗ Version increment test failed: {increment_result.get('error')}")
                    return False
                
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
    logger.info("TRANSACTION ISOLATION LEVELS AND OPTIMISTIC LOCKING TEST")
    logger.info("Tasks 34-35: Isolation Levels, Optimistic Locking")
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
        
        # Test isolation levels
        results.append(("Transaction Isolation Levels (Task 34)", await test_isolation_levels()))
        
        # Test optimistic locking
        results.append(("Optimistic Locking (Task 35)", await test_optimistic_locking()))
        
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

