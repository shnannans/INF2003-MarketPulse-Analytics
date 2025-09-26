import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Database URLs
MYSQL_URL = f"mysql+aiomysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASS', '')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'databaseproj')}"
MONGO_URL = f"mongodb://{os.getenv('MONGO_HOST', 'localhost')}:{os.getenv('MONGO_PORT', '27017')}"
MONGO_DB_NAME = os.getenv('MONGO_DB', 'databaseproj')
MONGO_COLLECTION_NAME = os.getenv('MONGO_COLLECTION', 'financial_news')

# Global variables for database connections
engine = None
AsyncSessionLocal = None
mongo_client = None
mongo_db = None
news_collection = None
Base = declarative_base()

# Database initialization functions
async def init_database():
    """Initialize database connections"""
    global engine, AsyncSessionLocal, mongo_client, mongo_db, news_collection

    try:
        # Initialize MySQL connection
        logger.info("Initializing MySQL connection...")
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
        logger.error(f"MySQL connection failed: {e}")
        # Don't fail completely, just log the error

    try:
        # Initialize MongoDB connection
        logger.info("Initializing MongoDB connection...")
        mongo_client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        mongo_db = mongo_client[MONGO_DB_NAME]
        news_collection = mongo_db[MONGO_COLLECTION_NAME]

        # Test MongoDB connection
        await mongo_client.admin.command('ping')
        logger.info("MongoDB connection established successfully")

    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        # Don't fail completely, just log the error

async def close_database():
    """Close database connections"""
    global engine, mongo_client

    try:
        if engine:
            await engine.dispose()
            logger.info("MySQL connection closed")
    except Exception as e:
        logger.error(f"Error closing MySQL connection: {e}")

    try:
        if mongo_client:
            mongo_client.close()
            logger.info("MongoDB connection closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")

async def test_all_connections():
    """Test all database connections and return status"""
    mysql_status = await check_mysql_connection()
    mongo_status = await check_mongo_connection()

    return {
        "mysql": "connected" if mysql_status else "disconnected",
        "mongodb": "connected" if mongo_status else "disconnected"
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

# Dependency to get MongoDB collection
async def get_mongo_collection():
    if news_collection is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="MongoDB service unavailable")
    return news_collection

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

async def check_mongo_connection():
    try:
        if not mongo_client:
            return False

        await mongo_client.admin.command('ping')
        return True
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return False