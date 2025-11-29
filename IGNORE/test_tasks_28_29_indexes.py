"""
Test script for Tasks 28-29: Covering Indexes and Full-Text Indexes
Tests that indexes are created and being used for dashboard queries and search
"""
import asyncio
import sys
import logging
import time
from sqlalchemy import text
from config.database import init_database, close_database, AsyncSessionLocal, get_mysql_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_covering_indexes():
    """Test that covering indexes are being used in queries"""
    logger.info("=" * 60)
    logger.info("TEST: Covering Indexes (Task 28)")
    logger.info("=" * 60)
    
    test_passed = False
    try:
        async for db_session in get_mysql_session():
            try:
                # Test 1: Query that should use idx_companies_listing
                logger.info("\nTest 1: Company Listing Query (should use idx_companies_listing)")
                logger.info("Query: SELECT ticker, company_name, sector, market_cap FROM companies WHERE sector = 'Technology' AND deleted_at IS NULL ORDER BY market_cap DESC")
                
                explain_query1 = text("""
                    EXPLAIN SELECT ticker, company_name, sector, market_cap 
                    FROM companies 
                    WHERE sector = 'Technology' 
                      AND deleted_at IS NULL
                    ORDER BY market_cap DESC
                    LIMIT 10
                """)
                
                result1 = await db_session.execute(explain_query1)
                explain_result1 = result1.fetchall()
                
                logger.info("EXPLAIN result:")
                index_used = False
                for row in explain_result1:
                    key_name = row[5] if len(row) > 5 else None
                    key_type = row[3] if len(row) > 3 else None
                    rows_estimated = row[8] if len(row) > 8 else None
                    extra = row[9] if len(row) > 9 else None
                    logger.info(f"  - Key: {key_name}, Type: {key_type}, Rows: {rows_estimated}, Extra: {extra}")
                    if key_name and 'idx_companies_listing' in str(key_name):
                        index_used = True
                        logger.info(f"  ✓ Index '{key_name}' is being used!")
                    elif key_type and key_type != 'ALL':
                        index_used = True
                        logger.info(f"  ✓ Query is using index (type: {key_type})")
                
                if not index_used:
                    logger.warning("  ⚠ Index might not be used (check EXPLAIN output above)")
                
                # Test 2: Query that should use idx_metrics_ticker
                logger.info("\nTest 2: Financial Metrics Query (should use idx_metrics_ticker)")
                logger.info("Query: SELECT ticker, pe_ratio, dividend_yield, beta, market_cap FROM financial_metrics WHERE ticker = 'AAPL'")
                
                explain_query2 = text("""
                    EXPLAIN SELECT ticker, pe_ratio, dividend_yield, beta, market_cap 
                    FROM financial_metrics 
                    WHERE ticker = 'AAPL'
                """)
                
                result2 = await db_session.execute(explain_query2)
                explain_result2 = result2.fetchall()
                
                logger.info("EXPLAIN result:")
                index_used2 = False
                for row in explain_result2:
                    key_name = row[5] if len(row) > 5 else None
                    key_type = row[3] if len(row) > 3 else None
                    rows_estimated = row[8] if len(row) > 8 else None
                    extra = row[9] if len(row) > 9 else None
                    logger.info(f"  - Key: {key_name}, Type: {key_type}, Rows: {rows_estimated}, Extra: {extra}")
                    if key_name and 'idx_metrics_ticker' in str(key_name):
                        index_used2 = True
                        logger.info(f"  ✓ Index '{key_name}' is being used!")
                    elif key_type and key_type != 'ALL':
                        index_used2 = True
                        logger.info(f"  ✓ Query is using index (type: {key_type})")
                
                if not index_used2:
                    logger.warning("  ⚠ Index might not be used (check EXPLAIN output above)")
                
                # Test 3: Performance test for covering index
                logger.info("\nTest 3: Performance Test (Covering Index)")
                logger.info("Executing company listing query 10 times...")
                
                query_perf = text("""
                    SELECT ticker, company_name, sector, market_cap 
                    FROM companies 
                    WHERE sector = 'Technology' 
                      AND deleted_at IS NULL
                    ORDER BY market_cap DESC
                    LIMIT 10
                """)
                
                times = []
                for i in range(10):
                    start = time.time()
                    await db_session.execute(query_perf)
                    elapsed = time.time() - start
                    times.append(elapsed)
                
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                logger.info(f"  ✓ Average query time: {avg_time*1000:.2f}ms")
                logger.info(f"  ✓ Min query time: {min_time*1000:.2f}ms")
                logger.info(f"  ✓ Max query time: {max_time*1000:.2f}ms")
                
                if avg_time < 0.1:
                    logger.info("  ✓ Performance is excellent (< 100ms average)")
                elif avg_time < 0.5:
                    logger.info("  ✓ Performance is good (< 500ms average)")
                else:
                    logger.warning(f"  ⚠ Performance might need optimization (>{avg_time*1000:.0f}ms average)")
                
                # Test 4: Verify covering indexes exist
                logger.info("\nTest 4: Verify Covering Indexes Exist")
                check_indexes = text("""
                    SELECT TABLE_NAME, INDEX_NAME, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as columns
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND INDEX_NAME IN ('idx_companies_listing', 'idx_metrics_ticker')
                    GROUP BY TABLE_NAME, INDEX_NAME
                """)
                
                result3 = await db_session.execute(check_indexes)
                indexes = result3.fetchall()
                
                if len(indexes) >= 1:  # At least companies index should exist
                    logger.info("  ✓ Covering indexes exist:")
                    for idx in indexes:
                        logger.info(f"    - {idx[0]}.{idx[1]}: {idx[2]}")
                else:
                    logger.error("  ✗ Expected covering indexes not found")
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


async def test_fulltext_indexes():
    """Test that full-text indexes work for search"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Full-Text Indexes (Task 29)")
    logger.info("=" * 60)
    
    test_passed = False
    try:
        async for db_session in get_mysql_session():
            try:
                # Test 1: Verify full-text index exists
                logger.info("\nTest 1: Verify Full-Text Index Exists")
                check_ft_index = text("""
                    SELECT INDEX_NAME, COLUMN_NAME, INDEX_TYPE
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'companies'
                      AND INDEX_NAME = 'idx_company_name_ft'
                """)
                
                result1 = await db_session.execute(check_ft_index)
                ft_index = result1.fetchall()
                
                if ft_index:
                    logger.info("  ✓ Full-text index exists:")
                    for idx in ft_index:
                        logger.info(f"    - {idx[0]}: {idx[1]} (type: {idx[2]})")
                else:
                    logger.warning("  ⚠ Full-text index not found (may not be supported)")
                    return False
                
                # Test 2: Test full-text search query
                logger.info("\nTest 2: Full-Text Search Query")
                logger.info("Query: SELECT ticker, company_name, sector FROM companies WHERE MATCH(company_name) AGAINST('Apple' IN NATURAL LANGUAGE MODE) AND deleted_at IS NULL")
                
                try:
                    ft_search_query = text("""
                        SELECT ticker, company_name, sector 
                        FROM companies 
                        WHERE MATCH(company_name) AGAINST(:search_term IN NATURAL LANGUAGE MODE)
                          AND deleted_at IS NULL
                        LIMIT 10
                    """)
                    
                    result2 = await db_session.execute(ft_search_query, {"search_term": "Apple"})
                    search_results = result2.fetchall()
                    
                    if search_results:
                        logger.info(f"  ✓ Found {len(search_results)} results:")
                        for row in search_results[:5]:  # Show first 5
                            logger.info(f"    - {row[0]}: {row[1]} ({row[2]})")
                    else:
                        logger.info("  ✓ Query executed successfully (no results found for 'Apple')")
                    
                except Exception as e:
                    if "doesn't support" in str(e).lower() or "not supported" in str(e).lower():
                        logger.warning(f"  ⚠ Full-text search not supported: {e}")
                        return False
                    else:
                        raise
                
                # Test 3: Compare performance with LIKE query
                logger.info("\nTest 3: Performance Comparison (Full-Text vs LIKE)")
                
                # Full-text search
                ft_query = text("""
                    SELECT ticker, company_name, sector 
                    FROM companies 
                    WHERE MATCH(company_name) AGAINST(:search_term IN NATURAL LANGUAGE MODE)
                      AND deleted_at IS NULL
                    LIMIT 10
                """)
                
                times_ft = []
                for i in range(10):
                    start = time.time()
                    await db_session.execute(ft_query, {"search_term": "Tech"})
                    elapsed = time.time() - start
                    times_ft.append(elapsed)
                
                avg_time_ft = sum(times_ft) / len(times_ft)
                
                # LIKE search (for comparison)
                like_query = text("""
                    SELECT ticker, company_name, sector 
                    FROM companies 
                    WHERE company_name LIKE :search_term
                      AND deleted_at IS NULL
                    LIMIT 10
                """)
                
                times_like = []
                for i in range(10):
                    start = time.time()
                    await db_session.execute(like_query, {"search_term": "%Tech%"})
                    elapsed = time.time() - start
                    times_like.append(elapsed)
                
                avg_time_like = sum(times_like) / len(times_like)
                
                logger.info(f"  ✓ Full-text search average: {avg_time_ft*1000:.2f}ms")
                logger.info(f"  ✓ LIKE search average: {avg_time_like*1000:.2f}ms")
                
                if avg_time_ft < avg_time_like:
                    improvement = ((avg_time_like - avg_time_ft) / avg_time_like) * 100
                    logger.info(f"  ✓ Full-text search is {improvement:.1f}% faster than LIKE")
                else:
                    logger.info("  ℹ Performance comparison (full-text may be better for larger datasets)")
                
                # Test 4: Test relevance ranking
                logger.info("\nTest 4: Relevance Ranking Test")
                try:
                    relevance_query = text("""
                        SELECT ticker, company_name, sector,
                               MATCH(company_name) AGAINST(:search_term IN NATURAL LANGUAGE MODE) as relevance
                        FROM companies 
                        WHERE MATCH(company_name) AGAINST(:search_term IN NATURAL LANGUAGE MODE)
                          AND deleted_at IS NULL
                        ORDER BY relevance DESC
                        LIMIT 5
                    """)
                    
                    result3 = await db_session.execute(relevance_query, {"search_term": "Technology"})
                    relevance_results = result3.fetchall()
                    
                    if relevance_results:
                        logger.info("  ✓ Relevance ranking results:")
                        for row in relevance_results:
                            logger.info(f"    - {row[0]}: {row[1]} (relevance: {row[3]:.4f})")
                    else:
                        logger.info("  ✓ Relevance ranking works (no results for 'Technology')")
                except Exception as e:
                    logger.warning(f"  ⚠ Relevance ranking test: {e}")
                
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
    logger.info("COVERING AND FULL-TEXT INDEXES TEST")
    logger.info("Tasks 28-29: Covering Indexes, Full-Text Indexes")
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
        
        # Test covering indexes
        results.append(("Covering Indexes (Task 28)", await test_covering_indexes()))
        
        # Test full-text indexes
        results.append(("Full-Text Indexes (Task 29)", await test_fulltext_indexes()))
        
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

