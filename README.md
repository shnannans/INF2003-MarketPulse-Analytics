## Prerequisites
- Python 3.8 or higher required

## Step 1: Download the requirements
pip install -r requirements.txt

Note: The .env file is already configured with default settings.

## Step 2: Run the API Server

### Using the run_server.py script 

## For Powershell
```bash
cd api_python
$env:API_PORT="8080" # or use 8082, or 8083 etc 
python run_server.py
```
## For Command Prompt
```bash
cd api_python
set API_PORT=8080 # optional use 8082, or 8083 etc 
python run_server.py
```

## Step 3: Access the Application

**Verification:** If the login page loads successfully, the server has started correctly.

START FROM THE LOGIN PAGE

admin cc@gmail.com qwerty123
user qq@gmail.com qwerty123
Or create a new user 

- Login Page: http://localhost:8080/login.html # change the port to match step 2

- Frontend (Static Files): http://localhost:8080/
- API Documentation (Swagger): http://localhost:8080/docs
- Alternative API Docs (ReDoc): http://localhost:8080/redoc
- Health Check: http://localhost:8080/health

Note: The FastAPI server automatically serves static files from the `static/` directory, so you don't need a separate HTTP server.

---
