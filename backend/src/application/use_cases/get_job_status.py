"""Get job status use case."""

import logging
from uuid import UUID

from ...domain.entities import GenerationJob
from ...domain.repositories import JobRepository
from ..dtos import JobResponse
from ..exceptions import PermissionDeniedError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class GetJobStatusUseCase:
    """
    Use case for retrieving job status.
    
    This use case retrieves a job's current status and details,
    ensuring the requesting user has permission to view it.
    
    Example:
        ```python
        use_case = GetJobStatusUseCase(job_repository=job_repo)
        
        response = await use_case.execute(user_id, job_id)
        print(f"Job status: {response.status}")
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
        Execute the get job status use case.
        
        Args:
            user_id: ID of the user requesting job status
            job_id: ID of the job to retrieve
            
        Returns:
            JobResponse DTO with job information
            
        Raises:
            ResourceNotFoundError: If job not found
            PermissionDeniedError: If user doesn't own the job
        """
        logger.info(f"Getting job status: {job_id} for user {user_id}")
        
        # 1. Fetch job from repository
        job = await self.job_repository.get_by_id(job_id)
        if job is None:
            logger.warning(f"Job not found: {job_id}")
            raise ResourceNotFoundError("Job", str(job_id))
        
        # 2. Verify user owns the job
        if job.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to access job {job_id} "
                f"owned by {job.user_id}"
            )
            raise PermissionDeniedError(
                "You don't have permission to access this job"
            )
        
        logger.debug(f"Job found: {job_id}, status: {job.status.value}")
        
        # 3. Convert to response DTO
        response = self._to_response_dto(job)
        
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
            progress=job.progress,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            retry_count=job.retry_count,
            result_url=job.result_url,
        )

