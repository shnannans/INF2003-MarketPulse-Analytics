# Known Issues & Troubleshooting Guide

**Team Member 4 Deliverable** - MarketPulse Analytics

## Quick Reference

| Issue | Category | Severity | Status |
|-------|----------|----------|--------|
| MySQL connection timeout | Infrastructure | High | Documented |
| Firestore authentication | Security | Medium | Fixed |
| NewsAPI rate limiting | External API | Medium | Documented |
| Moving averages missing | Data | Low | Fixed |
| Schema mismatch issues | Database | Critical | Fixed |

---

## Critical Issues (Fixed)

### ✅ Issue: Company Model Schema Mismatch

**Problem:**
- SQLAlchemy model expected `id` field as primary key
- Actual database used `ticker` as primary key
- API returned 500 errors when querying companies

**Solution:**
- Updated `api_python/models/database_models.py`
- Changed Company model to use `ticker` as primary key
- Added missing fields to match actual schema

**Status:** ✅ FIXED

### ✅ Issue: adj_close Field Not Found

**Problem:**
- API tried to select `adj_close` field that didn't exist
- Database queries failed, fell back to live data
- Moving averages not showing in charts

**Solution:**
- Removed `adj_close` from database queries
- Use `close_price` as substitute
- Fixed in `api_python/routers/stock_analysis.py`

**Status:** ✅ FIXED

---

## Infrastructure Issues

### ⚠️ MySQL Connection Timeout

**Symptoms:**
- `Can't connect to MySQL server on '@34.133.0.30'`
- Connection refused errors
- Connection timeout errors

**Causes:**
1. Firewall blocking port 3306
2. IP address not whitelisted in Google Cloud
3. Network connectivity issues
4. MySQL service down

**Solutions:**

#### 1. Check Network Connectivity
```bash
# Test port connectivity (Windows PowerShell)
Test-NetConnection -ComputerName 34.133.0.30 -Port 3306
```

#### 2. Whitelist Your IP in Google Cloud
1. Go to Google Cloud Console
2. Navigate to Cloud SQL → Your Instance
3. Click "Connections" → "Authorized Networks"
4. Add your public IP address
5. Save and wait 1-2 minutes

#### 3. Verify Password Encoding
- Special characters in password must be URL-encoded
- `@` becomes `%40` in `.env` file
- Example: `Password123@` → `Password123%40`

**Status:** ⚠️ Documented - Contact team lead for IP whitelisting

---

### ⚠️ Firestore Authentication Issues

**Symptoms:**
- `Failed to initialize Firestore client`
- `Project was not passed and could not be determined`
- `403 Missing or insufficient permissions`

**Solutions:**

#### 1. Use Application Default Credentials (Recommended)
```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Set project
gcloud config set project inf1005-452110
```

#### 2. Use Service Account Key (Alternative)
1. Download service account key from Google Cloud Console
2. Place in `api_python/service_key.json`
3. Set in `.env`: `GOOGLE_APPLICATION_CREDENTIALS=api_python/service_key.json`

**Status:** ✅ Fixed (use ADC or service account key)

---

## External API Issues

### ⚠️ NewsAPI Rate Limiting

**Symptoms:**
- `429 Too Many Requests`
- API returns empty results
- "NewsAPI subscription expired" error

**Causes:**
1. Exceeded daily quota (100 requests/day free tier)
2. Too many concurrent requests
3. Rapid successive requests

**Solutions:**

#### 1. Use Cached Data
Set `live=false` parameter in API calls:
```javascript
// Frontend
fetch('/api/news?live=false&ticker=AAPL')
```

#### 2. Implement Request Throttling
The API already implements caching to reduce API calls

#### 3. Upgrade API Plan
- Visit https://newsapi.org/pricing
- Upgrade to development tier ($449/month)
- Or business tier ($4499/month)

**Workaround:**
- Use Firestore data exclusively with `live=false`
- Fall back to general financial news
- API automatically falls back to cached data

**Status:** ⚠️ Documented - Use caching to reduce API calls

---

## Data Issues

### ⚠️ Moving Averages Missing for Some Companies

**Symptoms:**
- MA_20, MA_50, MA_200 showing as null
- Some companies missing technical indicators

**Causes:**
1. Insufficient historical data (< 200 days for MA_200)
2. Data collection period too short
3. Rolling window calculation requires N data points

**Solutions:**

#### 1. Collect More Historical Data
```python
# In local_data_collection.py
hist = stock.history(period="2y")  # Collect 2 years of data
```

**Expected:** At least 200 days for all companies

**Status:** ✅ Fixed (collecting 2 years of data)

---

## Application Issues

### ⚠️ Import Errors

**Symptoms:**
- `No module named 'api_python'`
- Import errors when running scripts

**Solutions:**

#### 1. Check Working Directory
```bash
# Make sure you're in project root
cd /path/to/MarketPulse-Analytics
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

---

### ⚠️ Server Not Starting

**Symptoms:**
- Port 8000 already in use
- `Address already in use`
- Server crashes on startup

**Solutions:**

#### 1. Kill Existing Process
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

#### 2. Use Different Port
```bash
uvicorn main:app --reload --port 8001
```

---

## Performance Issues

### ⚠️ Slow API Responses

**Symptoms:**
- API takes > 5 seconds to respond
- Timeout errors
- Database queries slow

**Solutions:**

#### 1. Use Database-First Strategy
The API already implements database-first caching:
```bash
GET /api/stock_analysis?ticker=AAPL
# Uses cached database data, not live yfinance
```

#### 2. Connection Pooling
Already implemented in `api_python/config/database.py`

---

## Browser Issues

### ⚠️ CORS Errors

**Symptoms:**
- `Access-Control-Allow-Origin` errors
- Cannot fetch API from frontend

**Solutions:**
Already configured in `api_python/main.py` - CORS is enabled for all origins

---

## Reporting Issues

### How to Report New Issues

1. **Check this document first** - Issue might already be documented
2. **Include error messages** - Full stack trace if available
3. **Describe steps to reproduce** - What were you doing when it happened?
4. **Environment details** - OS, Python version, browser
5. **Screenshots** - If UI-related issue

### Contact

- **Technical Lead:** Team Member 4 (DevOps)
- **Database Admin:** Contact team lead for cloud access
- **Emergencies:** Check Google Cloud Console logs

---

**Last Updated:** 2024  
**Maintained by:** Team Member 4

