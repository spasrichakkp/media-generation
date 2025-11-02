"""Database connection management with SQLAlchemy 2.0 async."""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from ...config import Settings, get_settings

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """
    Get or create the async database engine.
    
    Args:
        settings: Application settings (optional, will use get_settings() if not provided)
        
    Returns:
        AsyncEngine instance
    """
    global _engine
    
    if _engine is None:
        if settings is None:
            settings = get_settings()
        
        # Create async engine with asyncpg driver
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            # Use NullPool for testing to avoid connection issues
            poolclass=NullPool if settings.environment == "test" else None,
        )
        
        logger.info(
            f"Database engine created: pool_size={settings.database_pool_size}, "
            f"max_overflow={settings.database_max_overflow}"
        )
    
    return _engine


def get_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """
    Get or create the async session factory.
    
    Args:
        engine: AsyncEngine instance (optional, will use get_engine() if not provided)
        
    Returns:
        async_sessionmaker instance
    """
    global _async_session_factory
    
    if _async_session_factory is None:
        if engine is None:
            engine = get_engine()
        
        # Create session factory with expire_on_commit=False
        # This allows accessing attributes after commit without triggering lazy loads
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        
        logger.info("Database session factory created")
    
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Yields an AsyncSession that is automatically closed after use.
    This follows the FastAPI dependency injection pattern with yield.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    
    Yields:
        AsyncSession instance
    """
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(engine: AsyncEngine | None = None) -> None:
    """
    Initialize the database by creating all tables.
    
    This should only be used in development/testing.
    In production, use Alembic migrations instead.
    
    Args:
        engine: AsyncEngine instance (optional, will use get_engine() if not provided)
    """
    if engine is None:
        engine = get_engine()
    
    from .models import Base
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created")


async def check_db_health(engine: AsyncEngine | None = None) -> bool:
    """
    Check database connectivity.

    Args:
        engine: AsyncEngine instance (optional, will use get_engine() if not provided)

    Returns:
        True if database is accessible, False otherwise
    """
    from sqlalchemy import text

    if engine is None:
        engine = get_engine()

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def close_db(engine: AsyncEngine | None = None) -> None:
    """
    Close database connections and dispose of the engine.
    
    This should be called on application shutdown.
    
    Args:
        engine: AsyncEngine instance (optional, will use get_engine() if not provided)
    """
    global _engine, _async_session_factory
    
    if engine is None:
        engine = _engine
    
    if engine is not None:
        await engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connections closed")

