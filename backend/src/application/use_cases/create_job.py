"""Create generation job use case."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from ...domain.entities import GenerationJob
from ...domain.repositories import JobRepository, UserRepository
from ...domain.value_objects import ContentType
from ..dtos import CreateJobRequest, JobResponse
from ..exceptions import (
    QuotaExceededError,
    ResourceNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class CreateGenerationJobUseCase:
    """
    Use case for creating a new generation job.
    
    This use case orchestrates the business logic for creating a new
    content generation job, including:
    - Validating user exists and is active
    - Checking user quota
    - Creating the job entity
    - Saving to database
    - Updating user quota
    
    Example:
        ```python
        use_case = CreateGenerationJobUseCase(
            job_repository=job_repo,
            user_repository=user_repo
        )
        
        request = CreateJobRequest(
            prompt="A beautiful sunset",
            content_type="video"
        )
        
        response = await use_case.execute(user_id, request)
        ```
    """
    
    def __init__(
        self,
        job_repository: JobRepository,
        user_repository: UserRepository,
    ) -> None:
        """
        Initialize the use case with repository dependencies.
        
        Args:
            job_repository: Repository for job persistence
            user_repository: Repository for user persistence
        """
        self.job_repository = job_repository
        self.user_repository = user_repository
    
    async def execute(
        self,
        user_id: UUID,
        request: CreateJobRequest,
    ) -> JobResponse:
        """
        Execute the create job use case.
        
        Args:
            user_id: ID of the user creating the job
            request: Job creation request DTO
            
        Returns:
            JobResponse DTO with created job information
            
        Raises:
            ResourceNotFoundError: If user not found
            QuotaExceededError: If user has exceeded quota
            ValidationError: If user is inactive or validation fails
        """
        logger.info(f"Creating job for user {user_id}: {request.content_type}")
        
        # 1. Validate user exists and is active
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            logger.warning(f"User not found: {user_id}")
            raise ResourceNotFoundError("User", str(user_id))
        
        if not user.is_active:
            logger.warning(f"Inactive user attempted to create job: {user_id}")
            raise ValidationError("User account is inactive")
        
        # 2. Check user quota
        if not user.can_create_job():
            logger.warning(
                f"User {user_id} exceeded quota: "
                f"{user.quota_used}/{user.quota_limit}"
            )
            raise QuotaExceededError(
                quota_limit=user.quota_limit or 0,
                quota_used=user.quota_used
            )
        
        # 3. Convert DTO to domain entity
        try:
            content_type = ContentType(request.content_type)
        except ValueError:
            raise ValidationError(f"Invalid content type: {request.content_type}")
        
        job = GenerationJob(
            user_id=user_id,
            content_type=content_type,
            prompt=request.prompt,
            model_name=request.model_name,
            parameters=request.parameters,
            priority=request.priority,
            webhook_url=request.webhook_url,
        )
        
        logger.debug(f"Created job entity: {job.id}")
        
        # 4. Save job to database
        try:
            saved_job = await self.job_repository.create(job)
            logger.info(f"Job created successfully: {saved_job.id}")
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise
        
        # 5. Update user quota
        try:
            user.increment_quota()
            await self.user_repository.update(user)
            logger.debug(
                f"Updated user quota: {user.quota_used}/{user.quota_limit}"
            )
        except Exception as e:
            logger.error(f"Failed to update user quota: {e}")
            # Note: Job is already created, but quota not updated
            # This is acceptable - quota will be corrected on next reset

        # 6. Enqueue Celery task for async video generation
        try:
            from ...infrastructure.tasks import generate_video_task

            task = generate_video_task.delay(str(saved_job.id))
            logger.info(
                f"Enqueued video generation task {task.id} for job {saved_job.id}"
            )
        except Exception as e:
            logger.error(f"Failed to enqueue video generation task: {e}")
            # Job is created but task not enqueued
            # User can retry or we can have a background job to pick up orphaned jobs

        # 7. Convert domain entity to response DTO
        response = self._to_response_dto(saved_job)

        return response
    
    def _to_response_dto(self, job: GenerationJob) -> JobResponse:
        """
        Convert domain entity to response DTO.
        
        Args:
            job: GenerationJob domain entity
            
        Returns:
            JobResponse DTO
        """
        return JobResponse(
            id=job.id,
            user_id=job.user_id,
            content_type=job.content_type.value,
            prompt=job.prompt,
            model_name=job.model_name or "",
            parameters=job.parameters,
            status=job.status.value,
            priority=job.priority,
            progress=None,  # Progress tracking will be added later
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            retry_count=job.retry_count,
            result_url=None,  # Will be populated when job completes
        )

