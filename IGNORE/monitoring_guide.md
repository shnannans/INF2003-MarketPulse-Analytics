# Monitoring Guide

**Team Member 4 Deliverable** - MarketPulse Analytics

This guide explains how to monitor the MarketPulse Analytics platform on Google Cloud.

---

## Overview

Monitoring helps ensure the platform is running smoothly and identifies issues before they impact users.

---

## Cloud SQL Monitoring

### Accessing Cloud SQL Metrics

1. Go to Google Cloud Console
2. Navigate to **SQL** → Your Instance
3. Click **Monitoring** tab

### Key Metrics to Watch

**CPU Utilization:**
- Should be < 70% under normal load
- Spikes indicate heavy queries or need for scaling

**Memory Usage:**
- Monitor for memory pressure
- May need instance upgrade if consistently high

**Connection Count:**
- Track active connections
- Ensure connection pooling is working

**Query Performance:**
- Average query time
- Slow query log (if enabled)

### Setting Up Alerts

1. Go to **Monitoring** → **Alerting**
2. Create alert policy for:
   - High CPU (> 80%)
   - High memory (> 90%)
   - Connection limit reached
   - Failed connections

---

## Firestore Monitoring

### Accessing Firestore Metrics

1. Go to Google Cloud Console
2. Navigate to **Firestore** → **Usage**

### Key Metrics to Watch

**Read Operations:**
- Total document reads
- Read latency
- Cost implications

**Write Operations:**
- Total document writes
- Write latency
- Cost implications

**Storage:**
- Total storage used
- Collection sizes
- Document counts

### Setting Up Alerts

1. Go to **Monitoring** → **Alerting**
2. Create alert policy for:
   - High read/write rates
   - Storage thresholds
   - Error rates

---

## API Performance Monitoring

### Health Check Endpoint

Use the built-in health check:
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "database_connections": {
    "mysql": "connected",
    "firestore": "available"
  },
  "message": "MarketPulse API is running"
}
```

### Logging

**Application Logs:**
- Check console output when running server
- Look for ERROR and WARNING messages
- Monitor response times

**Key Log Messages:**
- `MySQL connection established successfully`
- `Firestore client initialized successfully`
- `DB-first: serving X rows from MySQL`
- Error messages with stack traces

---

## Error Monitoring

### Common Errors to Watch

**MySQL Errors:**
- Connection timeout
- Query failures
- Authentication errors

**Firestore Errors:**
- Permission denied (403)
- Project not found
- Authentication failures

**API Errors:**
- 500 Internal Server Error
- 503 Service Unavailable
- 429 Rate Limited (NewsAPI)

### Log Analysis

**Search for errors:**
```bash
# In server logs, look for:
- ERROR
- WARNING
- Exception
- Traceback
```

---

## Performance Monitoring

### Response Time Tracking

Monitor API endpoint response times:
- `/api/stock_analysis` - Should be < 2 seconds
- `/api/news` - Should be < 3 seconds
- `/api/sentiment` - Should be < 4 seconds

### Database Query Performance

**MySQL:**
- Check slow query log
- Monitor query execution time
- Optimize frequently accessed queries

**Firestore:**
- Monitor read/write latency
- Check query complexity
- Optimize indexes

---

## Cost Monitoring

### Cloud SQL Costs

Monitor:
- Instance hours
- Storage costs
- Backup costs
- Network egress

### Firestore Costs

Monitor:
- Document reads (charged per read)
- Document writes (charged per write)
- Storage costs
- Network egress

**Cost Optimization:**
- Use caching to reduce reads
- Batch operations when possible
- Clean up old data regularly

---

## Setting Up Alerts

### Alert Channels

**Email:**
1. Go to **Monitoring** → **Alerting** → **Notification Channels**
2. Add email address
3. Test notification

**Slack/Teams:**
1. Set up webhook URL
2. Add as notification channel
3. Configure alert policies

### Recommended Alert Policies

1. **High Error Rate:**
   - Trigger: > 5% error rate in 5 minutes
   - Action: Email team

2. **Database Down:**
   - Trigger: Connection failures
   - Action: Immediate notification

3. **High Latency:**
   - Trigger: API response > 5 seconds
   - Action: Email team

4. **Cost Threshold:**
   - Trigger: Daily cost > $X
   - Action: Email billing team

---

## Dashboard Setup

### Creating Custom Dashboards

1. Go to **Monitoring** → **Dashboards**
2. Create new dashboard
3. Add charts for:
   - API request rate
   - Error rate
   - Response time
   - Database connections
   - Firestore operations

---

## Logging Best Practices

### Structured Logging

Use consistent log formats:
```python
logger.info(f"DB-first: serving {count} rows for {ticker} from MySQL")
logger.error(f"MySQL connection failed: {e}")
```

### Log Levels

- **DEBUG:** Detailed information for debugging
- **INFO:** General information about operations
- **WARNING:** Warning messages (non-critical)
- **ERROR:** Error messages (needs attention)
- **CRITICAL:** Critical errors (immediate action needed)

---

## Troubleshooting with Monitoring

### High CPU Usage

1. Check query performance
2. Look for inefficient queries
3. Consider query optimization
4. Scale up instance if needed

### High Error Rate

1. Check error logs
2. Identify failing endpoints
3. Review recent code changes
4. Check external dependencies

### Slow Response Times

1. Check database query times
2. Review API endpoint logic
3. Check for network issues
4. Consider caching improvements

---

## Next Steps

1. ✅ Set up basic monitoring
2. ✅ Create alert policies
3. ✅ Monitor costs
4. ✅ Review logs regularly
5. ✅ Optimize based on metrics

---

**Created by:** Team Member 4  
**Last Updated:** 2024

