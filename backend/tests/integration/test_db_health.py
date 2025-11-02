"""Test database connection."""

import asyncio
from src.config import get_settings
from src.infrastructure.database import check_db_health

async def main():
    settings = get_settings()
    print(f"Database URL: {settings.database_url}")
    
    is_healthy = await check_db_health()
    print(f"Database healthy: {is_healthy}")

if __name__ == "__main__":
    asyncio.run(main())

