# ADR-002: Database-First Data Fetching Strategy

**Date:** 2024  
**Status:** Accepted  
**Deciders:** Development Team

## Context

The application needs to fetch stock data, news, and sentiment information. We can either:
1. Always fetch from external APIs (yfinance, NewsAPI) - Slow, rate-limited
2. Always use database cache - May have stale data
3. Hybrid approach - Use database first, fallback to APIs

## Decision

Implement a **Database-First Strategy with Write-Through Caching**:
1. Always check database first
2. If data exists and is fresh → return from database
3. If data missing or stale → fetch from API, store in database, then return
4. Store new data in database immediately (write-through)

## Rationale

### Benefits

**Performance:**
- Faster response times (database queries < API calls)
- Reduced latency for users
- Better user experience

**Reliability:**
- Reduces dependency on external APIs
- Handles API failures gracefully (can serve stale data)
- Less impact from rate limiting

**Cost:**
- Reduces NewsAPI calls (saves quota)
- Less network bandwidth
- Lower external API costs

**Data Consistency:**
- Single source of truth in database
- Historical data preservation
- Better for analytics and reporting

### Trade-offs

**Staleness:**
- Data may be slightly outdated
- Mitigated by configurable TTL (Time To Live)
- Can force refresh with `live=true` parameter

**Complexity:**
- More code to maintain
- Database writes add slight latency
- Need to handle write failures gracefully

## Implementation Details

### Stock Data Flow

```python
def get_stock_data(ticker, days):
    # 1. Query MySQL database
    db_data = query_stock_prices(ticker, days)
    
    # 2. Check if sufficient data exists
    if len(db_data) >= minimum_days:
        return db_data  # Fast path
    
    # 3. Fetch from yfinance (slow path)
    live_data = fetch_from_yfinance(ticker, days)
    
    # 4. Store in database (write-through)
    store_in_mysql(live_data)
    
    # 5. Return data
    return live_data
```

### News & Sentiment Flow

```python
def get_news(ticker, days, live=False):
    # 1. Query Firestore
    cached_news = query_firestore(ticker, days)
    
    # 2. Check if data exists and fresh
    if cached_news and not live:
        return cached_news  # Fast path
    
    # 3. Fetch from NewsAPI (slow path)
    api_news = fetch_from_newsapi(ticker, days)
    
    # 4. Store in Firestore (write-through)
    store_in_firestore(api_news)
    
    # 5. Return data
    return api_news
```

## Alternatives Considered

### Option 1: Always Use External APIs
- **Rejected:** Too slow, rate-limited, poor user experience

### Option 2: Cache-Aside Pattern
- **Rejected:** More complex invalidation logic required

### Option 3: Write-Back Pattern
- **Rejected:** Risk of data loss if cache fails before write

### Option 4: Read-Through with Background Refresh
- **Considered:** Good for future optimization, but adds complexity

## Configuration

**TTL Settings:**
- Stock data: Configurable (default: use database if available)
- News data: 15 minutes TTL
- Sentiment: 15 minutes TTL

**Live Parameter:**
- `live=false`: Use cache (default)
- `live=true`: Force fetch from API

## Consequences

**Positive:**
- ✅ Significant performance improvement
- ✅ Reduced API rate limit issues
- ✅ Better user experience
- ✅ Historical data preservation
- ✅ Cost savings on API calls

**Negative:**
- ⚠️ Slightly more complex code
- ⚠️ Need to handle database write failures
- ⚠️ Stale data possible (but acceptable for use case)

## Monitoring

**Metrics to Track:**
- Database hit rate (should be > 80%)
- API call reduction (target: 70% reduction)
- Response time improvement (target: 50% faster)
- Cache freshness (verify TTL working)

## Future Enhancements

1. **Background Refresh:** Update cache before TTL expires
2. **Invalidation Strategy:** Clear cache on specific events
3. **Multi-tier Caching:** Add Redis for even faster access
4. **Smart Prefetching:** Predict and cache likely requests

---

**Approved by:** Development Team  
**Last Updated:** 2024

