"""Cancel job use case."""

import logging
from datetime import datetime
from uuid import UUID

from ...domain.entities import GenerationJob
from ...domain.repositories import JobRepository
from ...domain.value_objects import JobStatus
from ..dtos import JobResponse
from ..exceptions import (
    InvalidStateTransitionError,
    PermissionDeniedError,
    ResourceNotFoundError,
)

logger = logging.getLogger(__name__)


class CancelJobUseCase:
    """
    Use case for cancelling a generation job.
    
    This use case cancels a job if it's in a cancellable state
    (queued or processing), ensuring the requesting user owns the job.
    
    Example:
        ```python
        use_case = CancelJobUseCase(job_repository=job_repo)
        
        response = await use_case.execute(user_id, job_id)
        print(f"Job cancelled: {response.status}")
        ```
    """
    
    def __init__(self, job_repository: JobRepository) -> None:
        """
        Initialize the use case with repository dependencies.
        
        Args:
            job_repository: Repository for job persistence
        """
        self.job_repository = job_repository
    
    async def execute(
        self,
        user_id: UUID,
        job_id: UUID,
    ) -> JobResponse:
        """
        Execute the cancel job use case.
        
        Args:
            user_id: ID of the user requesting cancellation
            job_id: ID of the job to cancel
            
        Returns:
            JobResponse DTO with updated job information
            
        Raises:
            ResourceNotFoundError: If job not found
            PermissionDeniedError: If user doesn't own the job
            InvalidStateTransitionError: If job cannot be cancelled
        """
        logger.info(f"Cancelling job: {job_id} for user {user_id}")
        
        # 1. Fetch job from repository
        job = await self.job_repository.get_by_id(job_id)
        if job is None:
            logger.warning(f"Job not found: {job_id}")
            raise ResourceNotFoundError("Job", str(job_id))
        
        # 2. Verify user owns the job
        if job.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to cancel job {job_id} "
                f"owned by {job.user_id}"
            )
            raise PermissionDeniedError(
                "You don't have permission to cancel this job"
            )
        
        # 3. Check if job can be cancelled
        if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            logger.warning(
                f"Cannot cancel job {job_id} in terminal state: {job.status.value}"
            )
            raise InvalidStateTransitionError(
                current_state=job.status.value,
                target_state="cancelled"
            )
        
        # 4. Cancel the job using domain logic
        try:
            job.mark_as_cancelled()
            logger.debug(f"Job {job_id} cancelled successfully")
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            raise
        
        # 5. Save updated job to database
        try:
            updated_job = await self.job_repository.update(job)
            logger.info(f"Job {job_id} cancelled and saved")
        except Exception as e:
            logger.error(f"Failed to save cancelled job {job_id}: {e}")
            raise
        
        # 6. Convert to response DTO
        response = self._to_response_dto(updated_job)
        
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

