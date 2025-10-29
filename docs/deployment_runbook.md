# Deployment Runbook

# TO START THE API
cd api_python
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# TO GO TO THE WEBPAGE
ABSOLUTE PATH OF THE index.html
Example:
C:\Users\corvan\Downloads\INF2003-MarketPulse-Analytics\index.html

## Overview

This runbook provides step-by-step instructions for deploying the MarketPulse Analytics platform to Google Cloud Platform.

---

## Pre-Deployment Checklist

Before deploying, ensure you have:

- [ ] Google Cloud Account with billing enabled
- [ ] Cloud SQL MySQL instance set up
- [ ] Firestore database configured
- [ ] Service account credentials (`service_key.json`)
- [ ] NewsAPI key
- [ ] Domain name (optional, for custom URLs)
- [ ] SSL certificate (for HTTPS)

---

## Current Production Setup

**Status:** ✅ Already Deployed

**Infrastructure:**
- **MySQL:** Cloud SQL instance (IP: 34.133.0.30)
- **Firestore:** Cloud Firestore database (`databaseproj`)
- **API:** FastAPI server running locally or on VM
- **Frontend:** Static HTML served locally or via web server

---

## Deployment Options

### Option 1: Cloud Run (Recommended for Scalability)

**Best for:** Production deployment with auto-scaling

#### Steps:

1. **Containerize the API:**
   ```bash
   # Create Dockerfile
   cat > api_python/Dockerfile << EOF
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
   EOF
   ```

2. **Build and push container:**
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/marketpulse-api
   ```

3. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy marketpulse-api \
     --image gcr.io/YOUR_PROJECT_ID/marketpulse-api \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

4. **Set environment variables in Cloud Run:**
   - Add all variables from `.env` file
   - Service account: Attach Firestore service account

5. **Update frontend API URL:**
   ```javascript
   // In js/main.js
   const API_URL = 'https://YOUR_CLOUD_RUN_URL';
   ```

---

### Option 2: Compute Engine VM

**Best for:** Full control over server environment

#### Steps:

1. **Create VM instance:**
   ```bash
   gcloud compute instances create marketpulse-vm \
     --zone=us-central1-a \
     --machine-type=e2-medium \
     --image-family=ubuntu-2204-lts \
     --image-project=ubuntu-os-cloud
   ```

2. **SSH into VM:**
   ```bash
   gcloud compute ssh marketpulse-vm --zone=us-central1-a
   ```

3. **Install dependencies:**
   ```bash
   sudo apt update
   sudo apt install -y python3-pip nginx
   pip3 install -r requirements.txt
   ```

4. **Deploy application:**
   ```bash
   # Clone repository
   git clone YOUR_REPO_URL
   cd MarketPulse-Analytics/api_python
   
   # Create .env file
   nano .env
   # Add your configuration
   ```

5. **Set up as systemd service:**
   ```bash
   sudo nano /etc/systemd/system/marketpulse.service
   ```
   ```ini
   [Unit]
   Description=MarketPulse Analytics API
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/home/YOUR_USER/MarketPulse-Analytics/api_python
   ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

6. **Start service:**
   ```bash
   sudo systemctl start marketpulse
   sudo systemctl enable marketpulse
   ```

7. **Configure Nginx as reverse proxy:**
   ```nginx
   # /etc/nginx/sites-available/marketpulse
   server {
       listen 80;
       server_name YOUR_DOMAIN.COM;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

---

### Option 3: App Engine (Simplest)

**Best for:** Quick deployment with minimal configuration

#### Steps:

1. **Create `app.yaml`:**
   ```yaml
   runtime: python311
   
   env_variables:
     DB_HOST: "34.133.0.30"
     DB_PORT: "3306"
     DB_NAME: "databaseproj"
     # Add other env variables
   
   handlers:
     - url: /.*
       script: auto
   ```

2. **Deploy:**
   ```bash
   gcloud app deploy
   ```

---

## Database Setup (Already Done)

✅ **Already configured:**
- MySQL Cloud SQL instance created
- Firestore database configured
- Tables populated with data
- Indexes created

**No additional setup needed for databases.**

---

## Security Configuration

### 1. Database User (Recommendation)

**Current:** Using `root` user

**Better:** Create application user:
```sql
-- See docs/create_db_user.sql for reference
-- Run this on a test environment first
CREATE USER 'app_user'@'%' IDENTIFIED BY 'StrongPassword';
GRANT SELECT, INSERT, UPDATE ON databaseproj.* TO 'app_user'@'%';
FLUSH PRIVILEGES;
```

**Update `.env`:**
```bash
DB_USER=app_user
DB_PASS=StrongPassword
```

### 2. Service Account Permissions

**Required roles:**
- Cloud SQL Client (for MySQL access)
- Cloud Datastore User (for Firestore)
- Or: Firebase Admin (full access)

**Verify:**
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID
```

### 3. API Key Management

- Store NewsAPI key in environment variables
- Never commit API keys to Git
- Use Google Cloud Secret Manager for production

```bash
# Create secret
echo -n "YOUR_NEWSAPI_KEY" | gcloud secrets create newsapi-key --data-file=-

# Access in code
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
secret = client.access_secret_version(request={"name": "projects/YOUR_PROJECT/secrets/newsapi-key/versions/latest"})
```

---

## Monitoring & Logging

### 1. Enable Cloud Logging

```python
# In api_python/main.py
import logging
from google.cloud import logging as cloud_logging

cloud_logging_client = cloud_logging.Client()
cloud_logging_client.setup_logging()
```

### 2. Set Up Alerts

1. Go to Google Cloud Console → Monitoring
2. Create alert policies for:
   - API errors (error rate > 5%)
   - High latency (> 2 seconds)
   - Database connection failures
3. Configure notification channels (email, Slack)

### 3. Monitor Firestore Usage

1. Go to Firestore → Usage
2. Monitor reads/writes
3. Set budget alerts

---

## Rollback Procedures

### If Deployment Fails

1. **Rollback Cloud Run:**
   ```bash
   gcloud run services update-traffic marketpulse-api --to-revisions REVISION_NAME=100
   ```

2. **Rollback VM:**
   ```bash
   sudo systemctl stop marketpulse
   # Revert to previous code version
   ```

3. **Database Rollback:**
   ```bash
   # Restore from backup snapshot
   gcloud sql backups list --instance=YOUR_INSTANCE
   gcloud sql backups restore BACKUP_ID --backup-instance=YOUR_INSTANCE
   ```

---

## Post-Deployment Verification

### 1. Health Checks

```bash
# Test API
curl https://YOUR_API_URL/api/dashboard

# Expected response:
# {"status": "success", "total_companies": 50, ...}
```

### 2. Database Connections

```bash
# Test MySQL
curl https://YOUR_API_URL/api/companies

# Test Firestore
curl https://YOUR_API_URL/api/test-firestore
```

### 3. Frontend Testing

1. Open `index.html` in browser
2. Verify charts load
3. Test ticker search
4. Check news feed

---

## Maintenance

### Regular Tasks

- **Daily:** Check error logs
- **Weekly:** Review Firestore costs
- **Monthly:** Update dependencies
- **Quarterly:** Security audit

### Updating the Application

1. Make code changes
2. Test locally
3. Deploy to staging (if available)
4. Test in staging
5. Deploy to production
6. Monitor for errors

---

## Troubleshooting

**Issue:** API not responding  
**Solution:** Check logs, verify service is running, check firewall rules

**Issue:** Database connection failed  
**Solution:** Verify IP whitelisting, check credentials, verify instance status

**Issue:** Firestore permission denied  
**Solution:** Check service account permissions, verify `service_key.json`

See [Known Issues](known_issues.md) for more troubleshooting.

---

## Emergency Contacts

- **Cloud SQL Issues:** Google Cloud Support
- **Firestore Issues:** Google Cloud Support
- **API Issues:** Check logs in Cloud Console
- **Team Lead:** [Your contact info]

---

**Created by:** Team Member 4  
**Last Updated:** 2024  
**Version:** 1.0
