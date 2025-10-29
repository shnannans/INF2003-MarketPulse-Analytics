import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Database URLs
MYSQL_URL = f"mysql+aiomysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASS', '')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'databaseproj')}"

# Global variables for database connections
engine = None
AsyncSessionLocal = None
Base = declarative_base()

# Database initialization functions
async def init_database():
    """Initialize database connections"""
    global engine, AsyncSessionLocal

    try:
        # Initialize MySQL connection (optional)
        logger.info("Initializing MySQL connection...")
        try:
            engine = create_async_engine(
                MYSQL_URL,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            AsyncSessionLocal = sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Test MySQL connection
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            logger.info("MySQL connection established successfully")
        except Exception as e:
            logger.warning(f"MySQL connection failed: {e}")
            logger.info("Continuing without MySQL connection...")
            engine = None
            AsyncSessionLocal = None

    except Exception as e:
        logger.error(f"MySQL connection failed: {e}")
        # Don't fail completely, just log the error


async def close_database():
    """Close database connections"""
    global engine

    try:
        if engine:
            await engine.dispose()
            logger.info("MySQL connection closed")
    except Exception as e:
        logger.error(f"Error closing MySQL connection: {e}")

async def test_all_connections():
    """Test all database connections and return status"""
    mysql_status = await check_mysql_connection() if engine else False

    return {
        "mysql": "connected" if mysql_status else "disconnected",
        "firestore": "available"  # Firestore is always available if service key exists
    }

# Dependency to get database session
async def get_mysql_session():
    if not AsyncSessionLocal:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="MySQL service unavailable")

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Health check functions
async def check_mysql_connection():
    try:
        if not AsyncSessionLocal:
            return False

        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"MySQL connection failed: {e}")
        return False
