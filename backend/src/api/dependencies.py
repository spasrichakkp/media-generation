"""Dependency injection for FastAPI routes."""

import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..application.exceptions import ResourceNotFoundError
from ..application.use_cases import (
    CancelJobUseCase,
    CreateGenerationJobUseCase,
    GetJobStatusUseCase,
    ListUserJobsUseCase,
)
from ..domain.entities import User
from ..infrastructure.adapters.database import (
    PostgreSQLJobRepository,
    PostgreSQLUserRepository,
)
from ..infrastructure.database import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# Database Session Dependency
# ============================================================================

async def get_session() -> AsyncSession:
    """
    Get database session dependency.
    
    This is a wrapper around get_db() for FastAPI dependency injection.
    
    Yields:
        AsyncSession: Database session
    """
    async for session in get_db():
        yield session


# ============================================================================
# Repository Dependencies
# ============================================================================

async def get_job_repository(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> PostgreSQLJobRepository:
    """
    Get job repository dependency.
    
    Args:
        session: Database session from dependency injection
        
    Returns:
        PostgreSQLJobRepository: Job repository instance
    """
    return PostgreSQLJobRepository(session)


async def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> PostgreSQLUserRepository:
    """
    Get user repository dependency.
    
    Args:
        session: Database session from dependency injection
        
    Returns:
        PostgreSQLUserRepository: User repository instance
    """
    return PostgreSQLUserRepository(session)


# ============================================================================
# Use Case Dependencies
# ============================================================================

async def get_create_job_use_case(
    job_repo: Annotated[PostgreSQLJobRepository, Depends(get_job_repository)],
    user_repo: Annotated[PostgreSQLUserRepository, Depends(get_user_repository)],
) -> CreateGenerationJobUseCase:
    """
    Get create job use case dependency.
    
    Args:
        job_repo: Job repository from dependency injection
        user_repo: User repository from dependency injection
        
    Returns:
        CreateGenerationJobUseCase: Use case instance
    """
    return CreateGenerationJobUseCase(job_repo, user_repo)


async def get_get_job_status_use_case(
    job_repo: Annotated[PostgreSQLJobRepository, Depends(get_job_repository)],
) -> GetJobStatusUseCase:
    """
    Get job status use case dependency.
    
    Args:
        job_repo: Job repository from dependency injection
        
    Returns:
        GetJobStatusUseCase: Use case instance
    """
    return GetJobStatusUseCase(job_repo)


async def get_list_jobs_use_case(
    job_repo: Annotated[PostgreSQLJobRepository, Depends(get_job_repository)],
) -> ListUserJobsUseCase:
    """
    Get list jobs use case dependency.
    
    Args:
        job_repo: Job repository from dependency injection
        
    Returns:
        ListUserJobsUseCase: Use case instance
    """
    return ListUserJobsUseCase(job_repo)


async def get_cancel_job_use_case(
    job_repo: Annotated[PostgreSQLJobRepository, Depends(get_job_repository)],
) -> CancelJobUseCase:
    """
    Get cancel job use case dependency.
    
    Args:
        job_repo: Job repository from dependency injection
        
    Returns:
        CancelJobUseCase: Use case instance
    """
    return CancelJobUseCase(job_repo)


# ============================================================================
# Authentication Dependencies
# ============================================================================

async def get_current_user(
    x_api_key: Annotated[Optional[str], Header()] = None,
    user_repo: Annotated[PostgreSQLUserRepository, Depends(get_user_repository)] = None,
) -> User:
    """
    Get current authenticated user from API key.
    
    This dependency validates the API key and returns the associated user.
    
    Args:
        x_api_key: API key from X-API-Key header
        user_repo: User repository from dependency injection
        
    Returns:
        User: Authenticated user entity
        
    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    if not x_api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # For now, we'll use a simple API key lookup
    # In production, this should use hashed API keys
    try:
        # Try to parse as UUID (user ID for testing)
        user_id = UUID(x_api_key)
        user = await user_repo.get_by_id(user_id)
        
        if user is None:
            logger.warning(f"Invalid API key: user not found for ID {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        if not user.is_active:
            logger.warning(f"Inactive user attempted access: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        
        logger.debug(f"Authenticated user: {user.id}")
        return user
        
    except ValueError:
        # Invalid UUID format
        logger.warning(f"Invalid API key format: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    except ResourceNotFoundError:
        logger.warning(f"User not found for API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def get_current_user_id(
    user: Annotated[User, Depends(get_current_user)]
) -> UUID:
    """
    Get current user ID from authenticated user.
    
    This is a convenience dependency that extracts just the user ID.
    
    Args:
        user: Authenticated user from dependency injection
        
    Returns:
        UUID: User ID
    """
    return user.id

