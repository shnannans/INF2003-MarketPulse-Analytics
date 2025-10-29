# Environment Setup Guide

**Team Member 4 Deliverable** - MarketPulse Analytics

## Table of Contents
1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Environment Configuration](#environment-configuration)
4. [Connection Testing](#connection-testing)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start

1. Copy the environment template:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` with your actual credentials

3. Set up Google Cloud authentication (see below)

4. Start the server:
   ```bash
   cd api_python
   python -m uvicorn main:app --reload
   ```

---

## Prerequisites

### Required Software
- **Python 3.8+** with pip
- **Google Cloud Account** access (for database)
- **NewsAPI Account** (free tier available)

### Python Dependencies
Install from requirements.txt:
```bash
pip install -r requirements.txt
```

---

## Environment Configuration

### 1. Google Cloud MySQL

**Current Setup:** Database is already configured on Google Cloud at IP `34.133.0.30`

**Configuration:**
```bash
DB_HOST=34.133.0.30
DB_PORT=3306
DB_NAME=databaseproj
DB_USER=root
DB_PASS=YourActualPassword
```

**Important Notes:**
- Database schema already exists (no setup needed)
- Data already populated (no seed data needed)
- URL-encode special characters in password:
  - `@` becomes `%40`
  - `#` becomes `%23`
  - `&` becomes `%26`

**Connection String:**
```
mysql+aiomysql://root:password%40@34.133.0.30:3306/databaseproj
```

### 2. Google Cloud Firestore

**Current Setup:** Firestore uses Application Default Credentials (ADC)

**Authentication Method - RECOMMENDED (ADC via gcloud CLI):**

1. **Install Google Cloud SDK:**
   ```bash
   # Windows (via PowerShell as Administrator)
   (New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
   & $env:Temp\GoogleCloudSDKInstaller.exe
   
   # After installation, restart your terminal
   ```

2. **Authenticate with Google Cloud:**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Set your project:**
   ```bash
   gcloud config set project inf1005-452110
   ```

4. **Verify authentication:**
   ```bash
   gcloud auth list
   # Should show your account
   ```

**Alternative Authentication (Service Account Key File):**

If you prefer to use a service account key file:

1. Obtain `service_key.json` from Google Cloud Console
2. Place it in `api_python/` directory
3. Set environment variable in `.env`:
   ```bash
   GOOGLE_APPLICATION_CREDENTIALS=api_python/service_key.json
   ```

**Service Account Permissions Required:**
- Cloud Datastore User
- Firebase Admin (recommended)

**Collections:** Will auto-create on first use

### 3. NewsAPI

**Configuration:**
```bash
NEWSAPI_KEY=your_newsapi_key_here
```

**Get API Key:**
1. Visit https://newsapi.org/register
2. Sign up for free tier (100 requests/day)
3. Copy your API key
4. Add to `.env` file

**Rate Limits:**
- Free tier: 100 requests/day
- Development tier: 1,000 requests/day
- Business tier: 250,000 requests/day

---

## Connection Testing

### Test MySQL Connection
```bash
python -c "
from api_python.config.database import check_mysql_connection
import asyncio
print('MySQL:', 'Connected' if asyncio.run(check_mysql_connection()) else 'Failed')
"
```

### Test Firestore Connection
```bash
python -c "
from api_python.config.firestore import get_firestore_client
client = get_firestore_client()
print('Firestore:', 'Connected' if client else 'Failed')
"
```

### Test API Server
```bash
cd api_python
python -m uvicorn main:app --reload
# Open http://localhost:8000/docs in browser
```

### Test Endpoints
```bash
# Health check
curl http://localhost:8000/api/dashboard

# Test Firestore
curl http://localhost:8000/api/test-firestore
```

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_HOST` | MySQL host IP | `34.133.0.30` |
| `DB_PORT` | MySQL port | `3306` |
| `DB_NAME` | Database name | `databaseproj` |
| `DB_USER` | Database username | `root` |
| `DB_PASS` | Database password | `YourPassword` (URL-encoded) |
| `NEWSAPI_KEY` | NewsAPI key | `abc123...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | API server host | `0.0.0.0` |
| `API_PORT` | API server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `FIRESTORE_DATABASE` | Firestore database ID | `databaseproj` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service account key path | Not set (uses ADC) |

---

## Troubleshooting

### Issue: MySQL Connection Failed
**Error:** `Can't connect to MySQL server`

**Solutions:**
1. Check if IP `34.133.0.30` is accessible from your network
2. Verify firewall allows port 3306
3. Confirm credentials are correct (remember URL-encoding)
4. Check if Google Cloud allows your IP address

### Issue: Firestore Permission Denied
**Error:** `403 Missing or insufficient permissions`

**Solutions:**
1. Run `gcloud auth application-default login`
2. Verify service account has "Firebase Admin" role
3. Check that credentials are set up correctly

### Issue: NewsAPI Rate Limited
**Error:** `429 Too Many Requests`

**Solutions:**
1. Check your daily quota
2. Use `live=false` parameter in API calls to use cached data
3. Consider upgrading API plan

### Issue: Module Not Found
**Error:** `No module named 'api_python'`

**Solutions:**
```bash
# Make sure you're in the project root
cd /path/to/MarketPulse-Analytics

# Install dependencies
pip install -r requirements.txt
```

---

## Next Steps

1. ✅ Configure `.env` file
2. ✅ Test connections
3. ✅ Start API server
4. ✅ Test endpoints
5. Read other documentation files in `docs/` directory

---

**Created by:** Team Member 4  
**Last Updated:** 2024

