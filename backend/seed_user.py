import asyncio
import logging
import sys
from uuid import uuid4

# Add src to path if needed
import os
sys.path.append(os.getcwd())

from src.infrastructure.database import get_session_factory, init_db
from src.domain.entities import User
from src.infrastructure.adapters.database import PostgreSQLUserRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed():
    logger.info("Seeding database...")
    
    # Ensure DB is initialized
    await init_db()
    
    async with get_session_factory()() as session:
        repo = PostgreSQLUserRepository(session)
        
        # Create a new user
        user_id = uuid4()
        user = User(
            id=user_id,
            email="admin@example.com",
            username="admin",
            is_active=True,
            is_admin=True,
            quota_limit=1000,
            quota_used=0
        )
        
        try:
            created_user = await repo.create(user)
            logger.info("="*50)
            logger.info(f"✅ Created Admin User")
            logger.info(f"ID: {created_user.id}")
            logger.info(f"Username: {created_user.username}")
            logger.info(f"API Key (use this ID): {created_user.id}")
            logger.info("="*50)
        except Exception as e:
            logger.error(f"Failed to create user: {e}")

if __name__ == "__main__":
    asyncio.run(seed())
