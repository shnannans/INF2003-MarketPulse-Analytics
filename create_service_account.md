# Create New Firestore Service Account

## Steps to create a new service account with proper permissions:

### 1. Go to Google Cloud Console
- Visit: https://console.cloud.google.com/iam-admin/serviceaccounts
- Select project: `inf1005-452110`

### 2. Create Service Account
- Click "Create Service Account"
- Name: `firestore-service-account`
- Description: `Service account for Firestore access`

### 3. Assign Roles
Add these roles:
- **Cloud Datastore User**
- **Firebase Admin SDK Administrator Service Agent**
- **Firebase Admin**

### 4. Create and Download Key
- Click "Create Key"
- Choose "JSON"
- Download the key file
- Replace your current `service_key.json` with the new one

### 5. Update Environment
Make sure your `.env` file points to the new key:
```
GOOGLE_APPLICATION_CREDENTIALS=service_key.json
FIRESTORE_PROJECT_ID=inf1005-452110
```

## Alternative: Use Application Default Credentials
If you're running locally, you can also use:
```bash
gcloud auth application-default login
```

This will use your personal Google account credentials instead of a service account.
