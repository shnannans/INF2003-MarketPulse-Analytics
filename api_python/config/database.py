import os
from config.environment import config
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Database URLs (Task 36: Read Replicas)
# Primary database for writes
PRIMARY_DB_HOST = os.getenv('DB_HOST', 'localhost')
PRIMARY_DB_PORT = os.getenv('DB_PORT', '3306')
PRIMARY_DB_USER = os.getenv('DB_USER', 'root')
PRIMARY_DB_PASS = os.getenv('DB_PASS', '')
PRIMARY_DB_NAME = os.getenv('DB_NAME', 'databaseproj')

# Read replica database for analytics (defaults to primary if not configured)
REPLICA_DB_HOST = os.getenv('REPLICA_DB_HOST', PRIMARY_DB_HOST)
REPLICA_DB_PORT = os.getenv('REPLICA_DB_PORT', PRIMARY_DB_PORT)
REPLICA_DB_USER = os.getenv('REPLICA_DB_USER', PRIMARY_DB_USER)
REPLICA_DB_PASS = os.getenv('REPLICA_DB_PASS', PRIMARY_DB_PASS)
REPLICA_DB_NAME = os.getenv('REPLICA_DB_NAME', PRIMARY_DB_NAME)

# Primary (write) database URL
PRIMARY_MYSQL_URL = f"mysql+aiomysql://{PRIMARY_DB_USER}:{PRIMARY_DB_PASS}@{PRIMARY_DB_HOST}:{PRIMARY_DB_PORT}/{PRIMARY_DB_NAME}"

# Replica (read) database URL
REPLICA_MYSQL_URL = f"mysql+aiomysql://{REPLICA_DB_USER}:{REPLICA_DB_PASS}@{REPLICA_DB_HOST}:{REPLICA_DB_PORT}/{REPLICA_DB_NAME}"

# Legacy URL for backward compatibility
MYSQL_URL = PRIMARY_MYSQL_URL

# Global variables for database connections
engine = None  # Primary (write) engine
read_engine = None  # Read replica engine (Task 36)
AsyncSessionLocal = None  # Primary (write) session
ReadSessionLocal = None  # Read replica session (Task 36)
Base = declarative_base()

# Connection pool configuration (Task 37: Connection Pooling)
POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '20'))  # Number of connections to maintain
MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))  # Additional connections if pool is exhausted
POOL_PRE_PING = os.getenv('DB_POOL_PRE_PING', 'true').lower() == 'true'  # Verify connections before using
POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))  # Recycle connections after 1 hour

# Database initialization functions
async def init_database():
    """Initialize database connections (Tasks 36-37: Read Replicas and Connection Pooling)"""
    global engine, read_engine, AsyncSessionLocal, ReadSessionLocal

    try:
        # Initialize primary (write) MySQL connection (Task 37: Connection Pooling)
        logger.info("Initializing MySQL primary (write) connection...")
        try:
            engine = create_async_engine(
                PRIMARY_MYSQL_URL,
                echo=False,
                poolclass=QueuePool,
                pool_size=POOL_SIZE,
                max_overflow=MAX_OVERFLOW,
                pool_pre_ping=POOL_PRE_PING,
                pool_recycle=POOL_RECYCLE
            )
            AsyncSessionLocal = sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Test primary MySQL connection
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            logger.info(f"MySQL primary connection established successfully (pool_size={POOL_SIZE}, max_overflow={MAX_OVERFLOW})")
        except Exception as e:
            logger.warning(f"MySQL primary connection failed: {e}")
            logger.info("Continuing without MySQL primary connection...")
            engine = None
            AsyncSessionLocal = None

        # Initialize read replica connection (Task 36: Read Replicas)
        # Only create separate read engine if replica is configured differently
        if (REPLICA_DB_HOST != PRIMARY_DB_HOST or 
            REPLICA_DB_PORT != PRIMARY_DB_PORT or 
            REPLICA_DB_USER != PRIMARY_DB_USER):
            logger.info("Initializing MySQL read replica connection...")
            try:
                read_engine = create_async_engine(
                    REPLICA_MYSQL_URL,
                    echo=False,
                    poolclass=QueuePool,
                    pool_size=POOL_SIZE,  # Can be configured separately for reads
                    max_overflow=MAX_OVERFLOW,
                    pool_pre_ping=POOL_PRE_PING,
                    pool_recycle=POOL_RECYCLE
                )
                ReadSessionLocal = sessionmaker(
                    read_engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )

                # Test read replica connection
                async with ReadSessionLocal() as session:
                    await session.execute(text("SELECT 1"))
                logger.info(f"MySQL read replica connection established successfully")
            except Exception as e:
                logger.warning(f"MySQL read replica connection failed: {e}")
                logger.info("Falling back to primary for reads...")
                read_engine = None
                ReadSessionLocal = None
        else:
            # Use primary for reads if replica is not configured
            logger.info("Read replica not configured, using primary for reads")
            read_engine = engine
            ReadSessionLocal = AsyncSessionLocal

    except Exception as e:
        logger.error(f"MySQL connection failed: {e}")
        # Don't fail completely, just log the error


async def close_database():
    """Close database connections (Tasks 36-37)"""
    global engine, read_engine

    try:
        if engine:
            await engine.dispose()
            logger.info("MySQL primary connection closed")
        if read_engine and read_engine != engine:
            await read_engine.dispose()
            logger.info("MySQL read replica connection closed")
    except Exception as e:
        logger.error(f"Error closing MySQL connection: {e}")

async def test_all_connections():
    """Test all database connections and return status"""
    mysql_status = await check_mysql_connection() if engine else False

    return {
        "mysql": "connected" if mysql_status else "disconnected",
        "firestore": "available"  # Firestore is always available if service key exists
    }

# Dependency to get database session (Task 36: Read Replicas)
async def get_mysql_session(read_only: bool = False):
    """
    Get MySQL database session.
    
    Args:
        read_only: If True, use read replica (for analytics queries).
                   If False, use primary (for writes).
    
    Returns:
        AsyncSession for database operations
    """
    # Determine which session to use
    session_local = ReadSessionLocal if read_only and ReadSessionLocal else AsyncSessionLocal
    
    if not session_local:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="MySQL service unavailable")

    async with session_local() as session:
        try:
            yield session
        finally:
            await session.close()


# Convenience functions for read/write separation (Task 36)
async def get_read_session():
    """Get read-only session for analytics queries (Task 36: Read Replicas)"""
    async for session in get_mysql_session(read_only=True):
        yield session


async def get_write_session():
    """Get write session for mutations (Task 36: Read Replicas)"""
    async for session in get_mysql_session(read_only=False):
        yield session


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


# Connection pool monitoring (Task 37: Connection Pooling)
def get_pool_status():
    """
    Get connection pool status for monitoring (Task 37: Connection Pooling).
    
    Returns:
        Dictionary with pool statistics
    """
    status = {
        "primary": None,
        "read_replica": None
    }
    
    try:
        if engine and hasattr(engine, 'pool'):
            pool = engine.pool
            status["primary"] = {
                "pool_size": getattr(pool, 'size', lambda: None)(),
                "checked_out": getattr(pool, 'checkedout', lambda: None)(),
                "overflow": getattr(pool, 'overflow', lambda: None)(),
                "pool_class": pool.__class__.__name__
            }
    except Exception as e:
        logger.error(f"Error getting primary pool status: {e}")
        status["primary"] = {"error": str(e)}
    
    try:
        if read_engine and read_engine != engine and hasattr(read_engine, 'pool'):
            pool = read_engine.pool
            status["read_replica"] = {
                "pool_size": getattr(pool, 'size', lambda: None)(),
                "checked_out": getattr(pool, 'checkedout', lambda: None)(),
                "overflow": getattr(pool, 'overflow', lambda: None)(),
                "pool_class": pool.__class__.__name__
            }
    except Exception as e:
        logger.error(f"Error getting read replica pool status: {e}")
        status["read_replica"] = {"error": str(e)}
    
    return status
