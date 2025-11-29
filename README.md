## Step 1: Download the requirements
pip install -r requirements.txt

## Step 2: Run the API Server

### Using the run_server.py script 

```bash
cd api_python
python run_server.py
```


## Step 3: Access the Application

START FROM THE LOGIN PAGE
admin cc@gmail.com qwerty123
user qq@gmail.com qwerty123
- **Login Page**: http://localhost:8080/login.html

- **Frontend (Static Files)**: http://localhost:8080/
- **API Documentation (Swagger)**: http://localhost:8080/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8080/redoc
- **Health Check**: http://localhost:8080/health

**Note:** The FastAPI server automatically serves static files from the `static/` directory, so you don't need a separate HTTP server.

---