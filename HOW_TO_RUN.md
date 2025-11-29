**Step 1: Install Requirements**
```bash
pip install -r requirements.txt
```


**Step 2: Using uvicorn directly**
```bash
cd api_python
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Step 3: Start HTTP Server**

Open a new terminal and run:

```bash
cd static
python -m http.server 8080
```

**Step 4: Start HTTP Server**

Go to http://localhost:8080/login.html
