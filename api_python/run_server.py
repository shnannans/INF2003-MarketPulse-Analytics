#!/usr/bin/env python3
"""
MarketPulse API Server Launcher

Usage:
    python run_server.py

This script starts the FastAPI server with proper configuration.
"""

import uvicorn
import logging
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def main():
    """Start the FastAPI server"""

    # Get port from environment variable or default to 8080
    port = int(os.getenv('API_PORT', '8080'))
    
    # Debug: Show what port will be used
    api_port_env = os.getenv('API_PORT')
    if api_port_env:
        print(f"DEBUG: API_PORT environment variable found: {api_port_env}")
    else:
        print("DEBUG: API_PORT environment variable not set, using default: 8080")

    print("=" * 60)
    print("MarketPulse API Server")
    print("=" * 60)
    print(f"Starting FastAPI server on port {port}...")
    print(f"API Documentation: http://localhost:{port}/docs")
    print(f"Health Check: http://localhost:{port}/health")
    print(f"Login Page: http://localhost:{port}/login.html")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print(f"Note: To use a different port, set API_PORT environment variable")
    print(f"      Windows CMD: set API_PORT=8081")
    print(f"      Windows PowerShell: $env:API_PORT=8081")
    print(f"      Linux/Mac: export API_PORT=8081")

    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            reload_excludes=["*.log", "*.pyc", "__pycache__", "*.log.*", "logs/*"],
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()