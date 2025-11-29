"""
Migration script to create users table
Run this script once to create the users table in the database
"""
import asyncio
import sys
import os
import logging
from sqlalchemy import text

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import init_database, close_database, AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_users_table():
    """Create users table if it doesn't exist"""
    await init_database()
    
    # Import again after initialization to get the updated global
    from config.database import AsyncSessionLocal
    
    if not AsyncSessionLocal:
        logger.error("Database session not available")
        await close_database()
        sys.exit(1)
    
    try:
        async with AsyncSessionLocal() as session:
            # Check if table already exists
            check_table_query = text("""
                SELECT COUNT(*) as count
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'users'
            """)
            
            result = await session.execute(check_table_query)
            count = result.scalar()
            
            if count > 0:
                logger.info("Table 'users' already exists. Skipping migration.")
                return
            
            logger.info("Creating users table...")
            
            # Create the table
            create_table_query = text("""
                CREATE TABLE users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    is_active INT NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NULL,
                    deleted_at DATETIME NULL,
                    INDEX idx_username (username),
                    INDEX idx_email (email),
                    INDEX idx_deleted_at (deleted_at)
                )
            """)
            
            await session.execute(create_table_query)
            await session.commit()
            
            logger.info("✓ Successfully created users table")
            logger.info("✓ Migration completed successfully")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await close_database()

if __name__ == "__main__":
    asyncio.run(create_users_table())

