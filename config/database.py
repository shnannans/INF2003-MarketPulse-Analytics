import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import text
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URLs - matching your PHP configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "databaseproj")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")  # XAMPP default is empty
DB_PORT = os.getenv("DB_PORT", "3307")

MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_DB = os.getenv("MONGO_DB", "databaseproj")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "financial_news")

# Construct database URLs
MYSQL_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
MONGO_URL = f"mongodb://{MONGO_HOST}:{MONGO_PORT}"

# SQLAlchemy setup
engine = create_async_engine(
    MYSQL_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,
    pool_recycle=300
)

AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

# MongoDB setup
mongo_client = None
mongo_db = None

async def init_mongodb():
    """Initialize MongoDB connection"""
    global mongo_client, mongo_db
    try:
        mongo_client = AsyncIOMotorClient(MONGO_URL)
        mongo_db = mongo_client[MONGO_DB]
        # Test connection
        await mongo_client.admin.command('ping')
        logger.info("MongoDB connection established")
        return True
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return False

async def close_mongodb():
    """Close MongoDB connection"""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB connection closed")

# Dependency functions for FastAPI
async def get_mysql_session() -> AsyncSession:
    """Get MySQL session for dependency injection"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_mongo_collection(collection_name: str = MONGO_COLLECTION):
    """Get MongoDB collection for dependency injection"""
    if mongo_db is None:
        raise Exception("MongoDB not initialized")
    return mongo_db[collection_name]

async def test_mysql_connection():
    """Test MySQL connectivity"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            row = result.fetchone()
            if row and row[0] == 1:
                logger.info("MySQL connection test successful")
                return True
            return False
    except Exception as e:
        logger.error(f"MySQL connection test failed: {e}")
        return False

async def test_mongo_connection():
    """Test MongoDB connectivity"""
    try:
        if mongo_db is None:
            await init_mongodb()
        
        if mongo_db:
            # Try to get collection stats
            collection = mongo_db[MONGO_COLLECTION]
            stats = await mongo_db.command("collstats", MONGO_COLLECTION)
            logger.info("MongoDB connection test successful")
            return True
        return False
    except Exception as e:
        logger.error(f"MongoDB connection test failed: {e}")
        return False

async def test_all_connections():
    """Test both database connections"""
    mysql_status = await test_mysql_connection()
    mongo_status = await test_mongo_connection()
    
    return {
        "mysql": mysql_status,
        "mongodb": mongo_status
    }

# Database initialization
async def init_database():
    """Initialize all database connections"""
    logger.info("Initializing database connections...")
    
    # Test MySQL
    mysql_ok = await test_mysql_connection()
    if not mysql_ok:
        logger.error("Failed to connect to MySQL")
    
    # Initialize MongoDB
    mongo_ok = await init_mongodb()
    if not mongo_ok:
        logger.error("Failed to connect to MongoDB")
    
    if mysql_ok and mongo_ok:
        logger.info("All database connections established successfully")
    else:
        logger.warning("Some database connections failed")
    
    return mysql_ok and mongo_ok

async def close_database():
    """Close all database connections"""
    await close_mongodb()
    await engine.dispose()
    logger.info("All database connections closed")