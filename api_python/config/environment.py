"""
Environment Configuration (Task 53: Environment Management)
Provides centralized environment variable management
"""
import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class EnvironmentConfig:
    """
    Environment configuration manager (Task 53: Environment Management).
    Centralizes all environment variable access with defaults.
    """
    
    # Application
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE", "logs/marketpulse.log")
    
    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "False").lower() == "true"
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASS: str = os.getenv("DB_PASS", "")
    DB_NAME: str = os.getenv("DB_NAME", "databaseproj")
    
    # Database Connection Pool
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_PRE_PING: bool = os.getenv("DB_POOL_PRE_PING", "True").lower() == "true"
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    
    # Read Replica (optional)
    REPLICA_DB_URL: Optional[str] = os.getenv("REPLICA_DB_URL", None)
    
    # Firestore
    FIRESTORE_PROJECT_ID: str = os.getenv("FIRESTORE_PROJECT_ID", "databaseproj")
    FIRESTORE_CREDENTIALS: Optional[str] = os.getenv("FIRESTORE_CREDENTIALS", None)
    
    # News API
    NEWS_API_KEY: Optional[str] = os.getenv("NEWS_API_KEY", None)
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    
    # Caching
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", None)
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
    
    # Startup Sync
    ENABLE_STARTUP_SYNC: bool = os.getenv("ENABLE_STARTUP_SYNC", "True").lower() == "true"
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment."""
        return cls.ENVIRONMENT.lower() == "production"
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development environment."""
        return cls.ENVIRONMENT.lower() == "development"
    
    @classmethod
    def is_testing(cls) -> bool:
        """Check if running in testing environment."""
        return cls.ENVIRONMENT.lower() == "testing"
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database connection URL."""
        return f"mysql+aiomysql://{cls.DB_USER}:{cls.DB_PASS}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    @classmethod
    def validate(cls):
        """
        Validate environment configuration.
        Returns (is_valid, errors).
        """
        errors = []
        
        # Required in production
        if cls.is_production():
            if cls.SECRET_KEY == "your-secret-key-change-in-production":
                errors.append("SECRET_KEY must be changed in production")
            
            if cls.DEBUG:
                errors.append("DEBUG should be False in production")
            
            if not cls.NEWS_API_KEY:
                errors.append("NEWS_API_KEY is required")
        
        # Database validation
        if not cls.DB_HOST:
            errors.append("DB_HOST is required")
        
        if not cls.DB_NAME:
            errors.append("DB_NAME is required")
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """Get configuration summary (safe for logging, excludes secrets)."""
        return {
            "environment": cls.ENVIRONMENT,
            "debug": cls.DEBUG,
            "log_level": cls.LOG_LEVEL,
            "api_host": cls.API_HOST,
            "api_port": cls.API_PORT,
            "db_host": cls.DB_HOST,
            "db_port": cls.DB_PORT,
            "db_name": cls.DB_NAME,
            "db_user": cls.DB_USER,
            "pool_size": cls.DB_POOL_SIZE,
            "max_overflow": cls.DB_MAX_OVERFLOW,
            "rate_limit_per_minute": cls.RATE_LIMIT_PER_MINUTE,
            "rate_limit_per_hour": cls.RATE_LIMIT_PER_HOUR,
            "enable_startup_sync": cls.ENABLE_STARTUP_SYNC,
            "has_news_api_key": bool(cls.NEWS_API_KEY),
            "has_redis": bool(cls.REDIS_URL),
            "has_replica": bool(cls.REPLICA_DB_URL)
        }


# Global config instance
config = EnvironmentConfig()

