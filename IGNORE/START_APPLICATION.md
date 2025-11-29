# How to Start and Use MarketPulse Analytics

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.11+ installed
- MySQL database running
- All dependencies installed (`pip install -r requirements.txt`)

---

## Step 1: Stop Any Running Servers

If you see a port conflict error, first stop any existing server:

**Option A: Kill the existing process (Windows)**
```powershell
# Find the process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with the actual process ID)
taskkill /PID 35512 /F
```

**Option B: Use a different port**
```powershell
# Use port 8001 instead
cd api_python
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Step 2: Start the Backend API Server

### Method 1: Using uvicorn directly (Recommended)
```powershell
cd api_python
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Method 2: Using the run_server.py script
```powershell
cd api_python
python run_server.py
```

### Method 3: Using Python directly
```powershell
cd api_python
python main.py
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**API Endpoints:**
- API Documentation: http://localhost:8000/docs
- ReDoc Documentation: http://localhost:8000/redoc
- Health Check: http://localhost:8000/api/health
- OpenAPI Schema: http://localhost:8000/openapi.json

---

## Step 3: Start the Frontend

### Option A: Using a Local Web Server (Recommended)

**Using Python's built-in server:**
```powershell
# In the project root directory
python -m http.server 8080
```

**Using Node.js http-server (if installed):**
```powershell
npx http-server -p 8080
```

**Using VS Code Live Server:**
- Right-click on `index.html`
- Select "Open with Live Server"

### Option B: Open Directly in Browser
Simply open `index.html` in your browser (some features may not work due to CORS)

**Frontend URL:**
- Main Dashboard: http://localhost:8080/index.html
- Login Page: http://localhost:8080/login.html
- Register Page: http://localhost:8080/register.html

---

## Step 4: Using the Application

### First Time Setup

1. **Register a New User**
   - Navigate to http://localhost:8080/register.html
   - Fill in username, email, and password
   - Click "Register"
   - You'll be automatically logged in

2. **Login (if you already have an account)**
   - Navigate to http://localhost:8080/login.html
   - Enter your email and password
   - Click "Login"
   - You'll be redirected to the dashboard

### Using the Dashboard

1. **View Stock Data**
   - The main dashboard shows stock prices, sentiment analysis, and market indices
   - Use the search bar to find specific tickers
   - Select date ranges (Day, Week, Month)

2. **Advanced Analytics** (Logged in users)
   - Click on the "Advanced Analytics" section
   - View Window Functions, Sector Performance, Price Trends, etc.
   - Refresh materialized views for latest data

3. **Profile Management**
   - Click "Profile" in the navigation
   - Edit your email address
   - Change your password
   - View account information

### Admin Features

If you're logged in as an admin:

1. **Admin Dashboard**
   - Click "Admin" in the navigation
   - View user statistics
   - Manage users (create, edit, delete)
   - Promote/demote admins

2. **Company Management**
   - Click "Companies" in the admin section
   - Create new companies
   - Edit company information
   - Delete/restore companies
   - Export company data

3. **News Management**
   - Click "News" in the admin section
   - Ingest news articles
   - Bulk ingest articles (JSON upload)
   - Edit/delete articles
   - Filter by sentiment and date

---

## 🔧 Troubleshooting

### Port Already in Use

**Error:** `[WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions`

**Solution:**
```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or use a different port
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Database Connection Error

**Error:** `Can't connect to MySQL server`

**Solution:**
1. Ensure MySQL is running
2. Check your `.env` file has correct database credentials:
   ```
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASS=your_password
   DB_NAME=databaseproj
   ```

### CORS Errors in Browser

**Error:** `Access to fetch at 'http://localhost:8000' from origin 'http://localhost:8080' has been blocked by CORS policy`

**Solution:**
- The backend already has CORS enabled for all origins
- Make sure the API server is running
- Check that you're accessing the frontend from a web server (not file://)

### Frontend Not Loading

**Solution:**
- Make sure you're using a web server (not opening HTML files directly)
- Check browser console for errors
- Verify all JavaScript files are loading correctly
- Check that the API server is running on port 8000

---

## 📝 Environment Configuration

Create a `.env` file in the project root:

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASS=your_password
DB_NAME=databaseproj

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True

# Environment
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO

# Firestore (optional)
FIRESTORE_PROJECT_ID=databaseproj

# Security
SECRET_KEY=your-secret-key-here
```

---

## 🎯 Quick Reference

### Backend API Endpoints

**Authentication:**
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token
- `POST /api/auth/logout` - Logout

**Users:**
- `GET /api/users` - List users
- `POST /api/users` - Create user
- `GET /api/users/{id}` - Get user
- `PATCH /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user

**Companies:**
- `GET /api/companies` - List companies
- `POST /api/companies` - Create company
- `GET /api/companies/{ticker}` - Get company
- `PUT /api/companies/{ticker}` - Update company
- `DELETE /api/companies/{ticker}` - Delete company

**News:**
- `GET /api/news` - List news articles
- `POST /api/news/ingest` - Ingest news article
- `GET /api/news/{id}` - Get article
- `PATCH /api/news/{id}` - Update article
- `DELETE /api/news/{id}` - Delete article

**Health & Monitoring:**
- `GET /api/health` - Health check
- `GET /api/health/dashboard` - Health dashboard
- `GET /api/status/system` - System status

### Frontend Pages

- `/index.html` - Main dashboard
- `/login.html` - Login page
- `/register.html` - Registration page
- `/profile.html` - User profile
- `/admin.html` - Admin dashboard
- `/admin-companies.html` - Company management
- `/admin-news.html` - News management

---

## 🛑 Stopping the Application

**To stop the backend server:**
- Press `Ctrl+C` in the terminal where the server is running

**To stop the frontend server:**
- Press `Ctrl+C` in the terminal where the web server is running

---

## 📚 Additional Resources

- API Documentation: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Frontend Implementation Summary: `FRONTEND_IMPLEMENTATION_SUMMARY.md`
- Deployment Guide: `docs/deployment_runbook.md`

---

## ✅ Verification Checklist

Before using the application, verify:

- [ ] MySQL database is running
- [ ] Database connection is configured in `.env`
- [ ] All Python dependencies are installed
- [ ] Backend API server is running on port 8000
- [ ] Frontend web server is running on port 8080
- [ ] You can access http://localhost:8000/docs
- [ ] You can access http://localhost:8080/index.html

---

**🎉 You're all set! Start the servers and begin using MarketPulse Analytics!**

