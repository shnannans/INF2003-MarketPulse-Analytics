# Setting Up Google Cloud Authentication

## Quick Setup (Recommended)

### Step 1: Install Google Cloud SDK

**Windows (PowerShell as Administrator):**
```powershell
# Download and run installer
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
& $env:Temp\GoogleCloudSDKInstaller.exe

# Restart your terminal after installation
```

**macOS:**
```bash
# Using Homebrew
brew install --cask google-cloud-sdk
```

**Linux:**
```bash
# Download installer
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### Step 2: Authenticate

```bash
# Login with your Google account
gcloud auth login

# Set up Application Default Credentials
gcloud auth application-default login

# Set your project
gcloud config set project inf1005-452110
```

### Step 3: Verify

```bash
# Check if authenticated
gcloud auth list

# Should show:
# Credentialed Accounts
# ACTIVE  ACCOUNT
# *       your-email@gmail.com
```

### Step 4: Run the Application

```bash
cd api_python
python -m uvicorn main:app --reload
```

The application will now automatically use your credentials!

---

## Troubleshooting

### If you see "credentials not found":

1. **Check authentication:**
   ```bash
   gcloud auth list
   ```

2. **Re-authenticate:**
   ```bash
   gcloud auth application-default login
   ```

3. **Check project:**
   ```bash
   gcloud config get-value project
   ```

### If you want to use service account key instead:

1. Download service account key from Google Cloud Console
2. Save it as `api_python/service_key.json`
3. Set environment variable:
   ```bash
   # Windows
   set GOOGLE_APPLICATION_CREDENTIALS=api_python/service_key.json
   
   # Linux/Mac
   export GOOGLE_APPLICATION_CREDENTIALS=api_python/service_key.json
   ```

---

## Benefits of ADC

✅ **More secure** - No need to manage key files  
✅ **Easier setup** - Just run one command  
✅ **Works everywhere** - Same credentials for all Google Cloud services  
✅ **Auto-refresh** - Credentials automatically renew  
✅ **Per-user** - Each developer uses their own Google account

---

## Project Information

- **Project ID:** inf1005-452110
- **Firestore Database:** databaseproj
- **Service Account:** databaseproj@inf1005-452110.iam.gserviceaccount.com

