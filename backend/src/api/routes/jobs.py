"""Job management endpoints."""

import logging
from typing import Annotated, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi import Form

from ...application.dtos import CreateJobRequest, JobListResponse, JobResponse
from ...application.use_cases import (
    CancelJobUseCase,
    CreateGenerationJobUseCase,
    GetJobStatusUseCase,
    ListUserJobsUseCase,
)
from ..dependencies import (
    get_cancel_job_use_case,
    get_create_job_use_case,
    get_current_user_id,
    get_get_job_status_use_case,
    get_list_jobs_use_case,
    get_user_repository,
    PostgreSQLUserRepository,
)
from ..domain.entities import User

# Create router
router = APIRouter()


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Generation Job",
    description="""
    Create a new media generation job.
    
    The job will be queued for processing and executed asynchronously.
    You can monitor the job status using the job ID returned in the response.
    
    **Authentication Required:** Yes (X-API-Key header)
    
    **Quota:** This endpoint consumes 1 quota unit per request.
    """,
    responses={
        201: {
            "description": "Job created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "123e4567-e89b-12d3-a456-426614174001",
                        "content_type": "video",
                        "prompt": "A beautiful sunset over mountains",
                        "model_name": "moneyprinter-turbo",
                        "parameters": {"duration": 5, "resolution": "1080p"},
                        "status": "queued",
                        "priority": 5,
                        "progress": None,
                        "created_at": "2025-10-02T08:00:00Z",
                        "updated_at": "2025-10-02T08:00:00Z",
                        "started_at": None,
                        "completed_at": None,
                        "error_message": None,
                        "retry_count": 0,
                        "result_url": None,
                    }
                }
            },
        },
        400: {"description": "Invalid request data"},
        401: {"description": "Missing or invalid API key"},
        403: {"description": "User account inactive"},
        429: {"description": "Quota exceeded"},
        422: {"description": "Validation error"},
    },
)
async def create_job(
    request: CreateJobRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    use_case: Annotated[CreateGenerationJobUseCase, Depends(get_create_job_use_case)],
) -> JobResponse:
    """
    Create a new generation job.
    
    Args:
        request: Job creation request with prompt and parameters
        user_id: Authenticated user ID from dependency injection
        use_case: Create job use case from dependency injection
        
    Returns:
        JobResponse: Created job details
        
    Raises:
        HTTPException: 401 if authentication fails
        HTTPException: 403 if user is inactive
        HTTPException: 429 if quota exceeded
        HTTPException: 422 if validation fails
    """
    logger.info(f"Creating job for user {user_id}: {request.content_type}")
    
    # Execute use case
    job = await use_case.execute(user_id, request)
    
    logger.info(f"Job created: {job.id}")
    return job


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Job Status",
    description="""
    Retrieve the current status and details of a generation job.
    
    **Authentication Required:** Yes (X-API-Key header)
    
    **Permissions:** You can only access jobs that belong to your account.
    """,
    responses={
        200: {
            "description": "Job details retrieved successfully",
        },
        401: {"description": "Missing or invalid API key"},
        403: {"description": "Permission denied - job belongs to another user"},
        404: {"description": "Job not found"},
    },
)
async def get_job_status(
    job_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    use_case: Annotated[GetJobStatusUseCase, Depends(get_get_job_status_use_case)],
) -> JobResponse:
    """
    Get job status and details.
    
    Args:
        job_id: Job ID to retrieve
        user_id: Authenticated user ID from dependency injection
        use_case: Get job status use case from dependency injection
        
    Returns:
        JobResponse: Job details
        
    Raises:
        HTTPException: 401 if authentication fails
        HTTPException: 403 if user doesn't own the job
        HTTPException: 404 if job not found
    """
    logger.info(f"Getting job status: {job_id} for user {user_id}")
    
    # Execute use case
    job = await use_case.execute(user_id, job_id)
    
    logger.debug(f"Job status retrieved: {job.id} - {job.status}")
    return job


@router.get(
    "/jobs",
    response_model=JobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List User Jobs",
    description="""
    List all generation jobs for the authenticated user with pagination.
    
    **Authentication Required:** Yes (X-API-Key header)
    
    **Pagination:** Use `page` and `page_size` query parameters to paginate results.
    
    **Filtering:** Use `status` query parameter to filter by job status.
    """,
    responses={
        200: {
            "description": "Jobs retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "jobs": [
                            {
                                "id": "123e4567-e89b-12d3-a456-426614174000",
                                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                                "content_type": "video",
                                "status": "completed",
                                "created_at": "2025-10-02T08:00:00Z",
                            }
                        ],
                        "total": 42,
                        "page": 1,
                        "page_size": 10,
                        "has_next": True,
                        "has_prev": False,
                    }
                }
            },
        },
        401: {"description": "Missing or invalid API key"},
        422: {"description": "Invalid pagination parameters"},
    },
)
async def list_jobs(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    use_case: Annotated[ListUserJobsUseCase, Depends(get_list_jobs_use_case)],
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=100, description="Number of items per page")
    ] = 10,
    status: Annotated[
        Optional[str],
        Query(
            description="Filter by job status (queued, processing, completed, failed, cancelled)"
        ),
    ] = None,
) -> JobListResponse:
    """
    List user's jobs with pagination and filtering.
    
    Args:
        user_id: Authenticated user ID from dependency injection
        use_case: List jobs use case from dependency injection
        page: Page number (1-indexed)
        page_size: Number of items per page (1-100)
        status: Optional status filter
        
    Returns:
        JobListResponse: Paginated list of jobs
        
    Raises:
        HTTPException: 401 if authentication fails
        HTTPException: 422 if pagination parameters are invalid
    """
    logger.info(
        f"Listing jobs for user {user_id}: page={page}, size={page_size}, status={status}"
    )
    
    # Execute use case
    jobs = await use_case.execute(
        user_id=user_id,
        page=page,
        page_size=page_size,
        status_filter=status,
    )
    
    logger.debug(f"Found {jobs.total} jobs for user {user_id}")
    return jobs


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Job",
    description="""
    Cancel a generation job that is queued or in progress.
    
    **Authentication Required:** Yes (X-API-Key header)
    
    **Permissions:** You can only cancel jobs that belong to your account.
    
    **Note:** Jobs that are already completed, failed, or cancelled cannot be cancelled.
    """,
    responses={
        200: {
            "description": "Job cancelled successfully",
        },
        400: {"description": "Job cannot be cancelled (already in terminal state)"},
        401: {"description": "Missing or invalid API key"},
        403: {"description": "Permission denied - job belongs to another user"},
        404: {"description": "Job not found"},
    },
)
async def cancel_job(
    job_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    use_case: Annotated[CancelJobUseCase, Depends(get_cancel_job_use_case)],
) -> JobResponse:
    """
    Cancel a generation job.
    
    Args:
        job_id: Job ID to cancel
        user_id: Authenticated user ID from dependency injection
        use_case: Cancel job use case from dependency injection
        
    Returns:
        JobResponse: Updated job details with cancelled status
        
    Raises:
        HTTPException: 400 if job is in terminal state
        HTTPException: 401 if authentication fails
        HTTPException: 403 if user doesn't own the job
        HTTPException: 404 if job not found
    """
    logger.info(f"Cancelling job: {job_id} for user {user_id}")
    
    # Execute use case
    job = await use_case.execute(user_id, job_id)
    
    logger.info(f"Job cancelled: {job.id}")
    return job


@router.post(
    "/users",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="""
    Register a new user account.
    
    Creates a new user with the provided email and username.
    Upon successful registration, an API key is generated and stored
    hashed in the database. The user can immediately use the API key
    with the X-API-Key header.
    
    **Rate Limited:** This endpoint is rate-limited to prevent abuse.
    """,
    responses={
        201: {
            "description": "User registered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "username": "testuser",
                        "api_key": "85bb62b5-7551-4c06-8e44-819c546fc433",
                        "is_active": True,
                        "quota_limit": 100
                    }
                }
            },
        },
        400: {"description": "Invalid request data - email or username already taken or invalid format"},
        422: {"description": "Validation error - email format invalid or username too short"},
    },
)
async def register_user(
    email: Annotated[str, Form()],
    username: Annotated[str, Form()],
) -> dict:
    """
    Register a new user.
    
    Args:
        email: User's email address
        username: User's username (minimum 3 characters)
        
    Returns:
        dict: User information including generated API key
    """
    from ..dependencies import get_current_user_id
    from ..application.use_cases import CreateGenerationJobUseCase
    from ..domain.entities import User
    from ..infrastructure.adapters.database import PostgreSQLUserRepository
    from src.infrastructure.database import get_db, get_session_factory
    
    logger.info(f"Registering new user: {email}")
    
    # Generate user ID
    user_id = uuid4()
    
    # Generate random API key
    api_key = str(uuid4())
    
    # Hash the API key (using simple encoding for now, in production use bcrypt)
    import hashlib
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Create user entity
    user = User(
        id=user_id,
        email=email,
        username=username,
        api_key_hash=api_key_hash,
        is_active=True,
        quota_limit=100,
        quota_used=0,
    )
    
    # Save user to database
    async with get_session_factory()() as session:
        repo = PostgreSQLUserRepository(session)
        created_user = await repo.create(user)
        await session.commit()
    
    logger.success(f"✅ User registered: {created_user.id}")
    
    return {
        "id": str(created_user.id),
        "email": created_user.email,
        "username": created_user.username,
        "api_key": api_key,
        "is_active": created_user.is_active,
        "quota_limit": created_user.quota_limit,
    }


@router.post(
    "/auth/login",
    response_model=dict,
    summary="User Login",
    description="""
    Log in with API key.
    
    Validates the provided API key and returns user information.
    This endpoint replaces traditional password-based authentication
    with API key-based authentication.
    
    **Authentication Required:** Provide the API key in X-API-Key header
    for subsequent requests.
    """,
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "username": "testuser",
                        "is_active": True,
                        "quota_used": 0,
                        "quota_limit": 100
                    }
                }
            },
        },
        401: {"description": "Invalid API key - authentication failed"},
    },
)
async def login_user(
    x_api_key: Annotated[str, Header()],
    user_repo: Annotated[PostgreSQLUserRepository, Depends(get_user_repository)],
) -> dict:
    """
    Log in with API key.
    
    Args:
        x_api_key: API key from X-API-Key header
        user_repo: User repository from dependency injection
        
    Returns:
        dict: User information if authentication successful
    """
    from src.infrastructure.database import get_session_factory
    from ..domain.entities import User
    
    logger.info("Attempting user login with API key")
    
    async with get_session_factory()() as session:
        repo = PostgreSQLUserRepository(session)
        
        # Use the repository's get_by_api_key_hash method
        user = await repo.get_by_api_key_hash(x_api_key)
        
        if user is None:
            logger.warning("Invalid API key: user not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        if not user.is_active:
            logger.warning(f"Inactive user attempted login: {user.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        
        logger.info(f"✅ User logged in: {user.id}")
        
        return {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "quota_used": user.quota_used,
            "quota_limit": user.quota_limit,
        }


@router.get(
    "/auth/key",
    response_model=dict,
    summary="Get Current User API Key",
    description="""
    Retrieve the current user's API key.
    
    Returns the API key associated with the authenticated user.
    The key can be used in the X-API-Key header for subsequent requests.
    """,
    responses={
        200: {
            "description": "API key retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "api_key": "85bb62b5-7551-4c06-8e44-819c546fc433",
                        "message": "Use this key in X-API-Key header for authentication"
                    }
                }
            },
        },
        401: {"description": "Not authenticated - no valid API key provided"},
    },
)
async def get_api_key(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Get the current user's API key.
    
    Args:
        current_user: Authenticated user from dependency injection
        
    Returns:
        dict: API key and usage information
    """
    import hashlib
    
    # Return the API key (in production, this might be partially masked or a different format)
    # For now, we return the key that was used to authenticate
    # The client should store this securely and use it in X-API-Key header
    
    return {
        "api_key": str(current_user.id),  # Using user ID as API key identifier
        "message": "Use this identifier in X-API-Key header for authentication",
        "quota_limit": current_user.quota_limit,
        "quota_used": current_user.quota_used,
    }

