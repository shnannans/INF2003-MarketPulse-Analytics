# Cloud Connection Guide

**Team Member 4 Deliverable** - MarketPulse Analytics

This guide explains how to connect to Google Cloud databases from your local machine.

---

## Overview

The MarketPulse Analytics platform uses two Google Cloud services:
1. **Cloud SQL (MySQL)** - For structured stock data
2. **Cloud Firestore** - For news and sentiment data

Both are hosted on Google Cloud Platform and accessible over the internet.

---

## MySQL Connection

### Connection Details

- **Host:** `34.133.0.30`
- **Port:** `3306`
- **Database:** `databaseproj`
- **Username:** `root`
- **Password:** (See team lead)

### Configuration

Add to your `.env` file:
```bash
DB_HOST=34.133.0.30
DB_PORT=3306
DB_NAME=databaseproj
DB_USER=root
DB_PASS=YourPassword%40
```

**Important:** URL-encode special characters in password:
- `@` → `%40`
- `#` → `%23`
- `&` → `%26`

### Network Requirements

1. **IP Whitelisting:**
   - Your public IP must be whitelisted in Google Cloud Console
   - Contact team lead to add your IP address
   - Check your IP: https://whatismyipaddress.com/

2. **Port 3306:**
   - Ensure your firewall allows outbound connections on port 3306
   - Most corporate networks allow this by default

### Testing Connection

```bash
# Test from command line
python -c "
import asyncio
from api_python.config.database import check_mysql_connection
result = asyncio.run(check_mysql_connection())
print('Connected!' if result else 'Failed')
"
```

---

## Firestore Connection

### Authentication Methods

#### Method 1: Application Default Credentials (Recommended)

**Steps:**
1. Install Google Cloud SDK
2. Authenticate:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project inf1005-452110
   ```
3. No additional configuration needed!

**Benefits:**
- No key files to manage
- Automatic credential refresh
- Uses your Google account

#### Method 2: Service Account Key

**Steps:**
1. Download service account key from Google Cloud Console
2. Save as `api_python/service_key.json`
3. Set in `.env`:
   ```bash
   GOOGLE_APPLICATION_CREDENTIALS=api_python/service_key.json
   ```

### Firestore Database

- **Project ID:** `inf1005-452110`
- **Database ID:** `databaseproj`

### Testing Connection

```bash
# Test Firestore
python -c "
from api_python.config.firestore import get_firestore_client
client = get_firestore_client()
print('Connected!' if client else 'Failed')
"
```

---

## Security Considerations

### Network Security

1. **MySQL:**
   - Only whitelisted IPs can connect
   - SSL encryption recommended for production
   - Strong password required

2. **Firestore:**
   - Access controlled via IAM roles
   - Service account with least privilege
   - Credentials never stored in code

### Best Practices

1. **Never commit credentials:**
   - Use `.env` file (in `.gitignore`)
   - Don't share passwords via email
   - Use environment variables in production

2. **Rotate credentials:**
   - Change passwords periodically
   - Regenerate service account keys if compromised

3. **Monitor access:**
   - Check Google Cloud logs regularly
   - Review IAM permissions quarterly

---

## Troubleshooting

### MySQL Connection Issues

**Issue:** Connection timeout
- Check if IP is whitelisted
- Verify firewall settings
- Test network connectivity: `Test-NetConnection -ComputerName 34.133.0.30 -Port 3306`

**Issue:** Authentication failed
- Verify credentials in `.env`
- Check password encoding (URL-encode special chars)
- Confirm username is correct

### Firestore Connection Issues

**Issue:** Project not found
- Run: `gcloud config set project inf1005-452110`
- Check project ID in Google Cloud Console

**Issue:** Permission denied
- Verify service account has "Firebase Admin" role
- Check IAM permissions in Google Cloud Console
- Re-authenticate: `gcloud auth application-default login`

---

## Next Steps

1. ✅ Configure `.env` file with database credentials
2. ✅ Set up Google Cloud authentication
3. ✅ Test connections using commands above
4. ✅ Start the API server

For more details, see:
- [Environment Setup Guide](environment_setup_guide.md)
- [Known Issues](known_issues.md)

---

**Created by:** Team Member 4  
**Last Updated:** 2024

