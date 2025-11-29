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

    print("=" * 60)
    print("MarketPulse API Server")
    print("=" * 60)
    print("Starting FastAPI server...")
    print("API Documentation: http://localhost:8080/docs")
    print("Health Check: http://localhost:8080/health")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)

    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8080,
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