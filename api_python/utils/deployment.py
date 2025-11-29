"""
Deployment Utilities (Task 52: Deployment Configuration)
Provides utilities for deployment and configuration management
"""
import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from config.environment import config

logger = logging.getLogger(__name__)


class DeploymentManager:
    """
    Deployment manager (Task 52: Deployment Configuration).
    Handles deployment-related operations.
    """
    
    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """
        Check if all required dependencies are installed.
        Returns dictionary of dependency status.
        """
        dependencies = {
            "fastapi": False,
            "uvicorn": False,
            "sqlalchemy": False,
            "aiomysql": False,
            "pydantic": False,
            "python-dotenv": False,
            "psutil": False
        }
        
        for dep in dependencies.keys():
            try:
                __import__(dep.replace("-", "_"))
                dependencies[dep] = True
            except ImportError:
                dependencies[dep] = False
        
        return dependencies
    
    @staticmethod
    def check_environment_files() -> Dict[str, bool]:
        """
        Check if required environment files exist.
        Returns dictionary of file status.
        """
        base_path = Path(__file__).parent.parent.parent
        files = {
            ".env": (base_path / ".env").exists(),
            ".env.example": (base_path / ".env.example").exists(),
            "requirements.txt": (base_path / "requirements.txt").exists(),
            "Dockerfile": (base_path / "Dockerfile").exists(),
            "docker-compose.yml": (base_path / "docker-compose.yml").exists()
        }
        
        return files
    
    @staticmethod
    def validate_deployment_config() -> tuple[bool, list[str]]:
        """
        Validate deployment configuration.
        Returns (is_valid, errors).
        """
        errors = []
        
        # Check dependencies
        deps = DeploymentManager.check_dependencies()
        missing_deps = [dep for dep, installed in deps.items() if not installed]
        if missing_deps:
            errors.append(f"Missing dependencies: {', '.join(missing_deps)}")
        
        # Validate environment config
        is_valid, config_errors = config.validate()
        if not is_valid:
            errors.extend(config_errors)
        
        # Check required directories
        required_dirs = ["logs", "api_python"]
        for dir_name in required_dirs:
            dir_path = Path(__file__).parent.parent.parent / dir_name
            if not dir_path.exists():
                errors.append(f"Required directory missing: {dir_name}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def get_deployment_info() -> Dict[str, Any]:
        """
        Get deployment information.
        Returns dictionary with deployment details.
        """
        return {
            "environment": config.ENVIRONMENT,
            "python_version": sys.version,
            "dependencies": DeploymentManager.check_dependencies(),
            "environment_files": DeploymentManager.check_environment_files(),
            "config_summary": config.get_config_summary(),
            "validation": {
                "is_valid": DeploymentManager.validate_deployment_config()[0],
                "errors": DeploymentManager.validate_deployment_config()[1]
            }
        }


def create_env_example():
    """
    Create .env.example file from current environment (Task 52: Deployment Configuration).
    """
    base_path = Path(__file__).parent.parent.parent
    env_example_path = base_path / ".env.example"
    
    env_example_content = """# MarketPulse Analytics - Environment Configuration
# Copy this file to .env and update with your values

# Application
ENVIRONMENT=development
DEBUG=False
LOG_LEVEL=INFO
LOG_FILE=logs/marketpulse.log

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=False

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASS=
DB_NAME=databaseproj

# Database Connection Pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_PRE_PING=True
DB_POOL_RECYCLE=3600

# Read Replica (optional)
# REPLICA_DB_URL=mysql+aiomysql://user:pass@host:port/dbname

# Firestore
FIRESTORE_PROJECT_ID=databaseproj
# FIRESTORE_CREDENTIALS=path/to/service_key.json

# News API
# NEWS_API_KEY=your_news_api_key_here

# Security
SECRET_KEY=your-secret-key-change-in-production
ALLOWED_ORIGINS=*

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Caching
# REDIS_URL=redis://localhost:6379/0
CACHE_TTL=300

# Startup Sync
ENABLE_STARTUP_SYNC=True
"""
    
    try:
        with open(env_example_path, "w") as f:
            f.write(env_example_content)
        logger.info(f"Created .env.example file at {env_example_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating .env.example: {e}")
        return False

