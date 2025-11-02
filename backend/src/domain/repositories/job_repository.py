"""Job Repository interface - Port for job data access."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities import GenerationJob
from ..value_objects import JobStatus


class JobRepository(ABC):
    """
    Abstract repository interface for GenerationJob entities.
    
    This is a port in the Hexagonal Architecture - it defines the contract
    that infrastructure adapters must implement.
    """
    
    @abstractmethod
    async def create(self, job: GenerationJob) -> GenerationJob:
        """
        Create a new job.
        
        Args:
            job: The job to create
            
        Returns:
            The created job with any database-generated fields populated
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, job_id: UUID) -> Optional[GenerationJob]:
        """
        Get a job by its ID.
        
        Args:
            job_id: The job ID
            
        Returns:
            The job if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[GenerationJob]:
        """
        Get all jobs for a user.
        
        Args:
            user_id: The user ID
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            List of jobs for the user
        """
        pass
    
    @abstractmethod
    async def get_by_status(
        self,
        status: JobStatus,
        limit: int = 100,
        offset: int = 0
    ) -> List[GenerationJob]:
        """
        Get jobs by status.
        
        Args:
            status: The job status
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            List of jobs with the specified status
        """
        pass
    
    @abstractmethod
    async def get_queued_jobs(
        self,
        limit: int = 100
    ) -> List[GenerationJob]:
        """
        Get queued jobs ordered by priority (highest first) and creation time.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of queued jobs
        """
        pass
    
    @abstractmethod
    async def update(self, job: GenerationJob) -> GenerationJob:
        """
        Update an existing job.
        
        Args:
            job: The job to update
            
        Returns:
            The updated job
        """
        pass
    
    @abstractmethod
    async def delete(self, job_id: UUID) -> bool:
        """
        Delete a job.
        
        Args:
            job_id: The job ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def count_by_user_id(self, user_id: UUID) -> int:
        """
        Count jobs for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Number of jobs for the user
        """
        pass
    
    @abstractmethod
    async def count_by_status(self, status: JobStatus) -> int:
        """
        Count jobs by status.
        
        Args:
            status: The job status
            
        Returns:
            Number of jobs with the specified status
        """
        pass
    
    @abstractmethod
    async def get_active_jobs_count(self) -> int:
        """
        Get count of active (processing) jobs.
        
        Returns:
            Number of active jobs
        """
        pass
    
    @abstractmethod
    async def exists(self, job_id: UUID) -> bool:
        """
        Check if a job exists.
        
        Args:
            job_id: The job ID
            
        Returns:
            True if job exists, False otherwise
        """
        pass

