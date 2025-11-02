"""List user jobs use case."""

import logging
from typing import List, Optional
from uuid import UUID

from ...domain.entities import GenerationJob
from ...domain.repositories import JobRepository
from ...domain.value_objects import JobStatus
from ..dtos import JobListResponse, JobResponse
from ..exceptions import ValidationError

logger = logging.getLogger(__name__)


class ListUserJobsUseCase:
    """
    Use case for listing user's jobs with pagination.
    
    This use case retrieves a paginated list of jobs for a user,
    with optional status filtering.
    
    Example:
        ```python
        use_case = ListUserJobsUseCase(job_repository=job_repo)
        
        response = await use_case.execute(
            user_id=user_id,
            page=1,
            page_size=10,
            status_filter="processing"
        )
        
        print(f"Found {response.total} jobs")
        for job in response.jobs:
            print(f"  - {job.id}: {job.status}")
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
        page: int = 1,
        page_size: int = 10,
        status_filter: Optional[str] = None,
    ) -> JobListResponse:
        """
        Execute the list jobs use case.
        
        Args:
            user_id: ID of the user whose jobs to list
            page: Page number (1-indexed)
            page_size: Number of jobs per page (1-100)
            status_filter: Optional status to filter by
            
        Returns:
            JobListResponse DTO with paginated jobs
            
        Raises:
            ValidationError: If page/page_size invalid or status invalid
        """
        logger.info(
            f"Listing jobs for user {user_id}: "
            f"page={page}, size={page_size}, status={status_filter}"
        )
        
        # 1. Validate pagination parameters
        if page < 1:
            raise ValidationError("Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise ValidationError("Page size must be between 1 and 100")
        
        # 2. Validate status filter if provided
        status_enum: Optional[JobStatus] = None
        if status_filter is not None:
            try:
                status_enum = JobStatus(status_filter.lower())
            except ValueError:
                raise ValidationError(f"Invalid status: {status_filter}")
        
        # 3. Calculate offset
        offset = (page - 1) * page_size
        
        # 4. Fetch jobs from repository
        if status_enum is not None:
            # Get jobs by status (all users)
            all_jobs = await self.job_repository.get_by_status(
                status=status_enum,
                limit=1000,  # Get all to filter by user
                offset=0,
            )
            # Filter by user
            jobs = [j for j in all_jobs if j.user_id == user_id][offset:offset + page_size]
            total = len([j for j in all_jobs if j.user_id == user_id])
        else:
            # Get all jobs for user
            jobs = await self.job_repository.get_by_user_id(
                user_id=user_id,
                limit=page_size,
                offset=offset,
            )
            total = await self.job_repository.count_by_user_id(user_id=user_id)
        
        logger.debug(
            f"Found {len(jobs)} jobs (total: {total}) for user {user_id}"
        )
        
        # 6. Convert to response DTOs
        job_responses = [self._to_response_dto(job) for job in jobs]
        
        # 7. Calculate pagination metadata
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        response = JobListResponse(
            jobs=job_responses,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_prev=has_prev,
        )
        
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

