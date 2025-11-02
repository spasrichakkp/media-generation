"""PostgreSQL implementation of JobRepository."""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.entities import GenerationJob
from ....domain.repositories import JobRepository
from ....domain.value_objects import ContentType, JobStatus
from ...database.models import GenerationJobModel

logger = logging.getLogger(__name__)


class PostgreSQLJobRepository(JobRepository):
    """
    PostgreSQL implementation of JobRepository using SQLAlchemy async.
    
    Converts between ORM models and domain entities.
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
    
    async def create(self, job: GenerationJob) -> GenerationJob:
        """Create a new job in the database."""
        try:
            # Convert domain entity to ORM model
            job_model = self._to_model(job)
            
            # Add to session and flush to get any database-generated values
            self.session.add(job_model)
            await self.session.flush()
            await self.session.refresh(job_model)
            
            # Convert back to domain entity
            return self._to_entity(job_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error creating job: {e}")
            await self.session.rollback()
            raise
    
    async def get_by_id(self, job_id: UUID) -> Optional[GenerationJob]:
        """Get a job by its ID."""
        try:
            stmt = select(GenerationJobModel).where(GenerationJobModel.id == job_id)
            result = await self.session.execute(stmt)
            job_model = result.scalar_one_or_none()
            
            if job_model is None:
                return None
            
            return self._to_entity(job_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting job by ID {job_id}: {e}")
            raise
    
    async def get_by_user_id(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[GenerationJob]:
        """Get all jobs for a user."""
        try:
            stmt = (
                select(GenerationJobModel)
                .where(GenerationJobModel.user_id == user_id)
                .order_by(GenerationJobModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await self.session.execute(stmt)
            job_models = result.scalars().all()
            
            return [self._to_entity(model) for model in job_models]
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting jobs for user {user_id}: {e}")
            raise
    
    async def get_by_status(
        self,
        status: JobStatus,
        limit: int = 100,
        offset: int = 0
    ) -> List[GenerationJob]:
        """Get jobs by status."""
        try:
            stmt = (
                select(GenerationJobModel)
                .where(GenerationJobModel.status == status.value)
                .order_by(GenerationJobModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await self.session.execute(stmt)
            job_models = result.scalars().all()
            
            return [self._to_entity(model) for model in job_models]
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting jobs by status {status}: {e}")
            raise
    
    async def get_queued_jobs(self, limit: int = 100) -> List[GenerationJob]:
        """Get queued jobs ordered by priority and creation time."""
        try:
            stmt = (
                select(GenerationJobModel)
                .where(GenerationJobModel.status == JobStatus.QUEUED.value)
                .order_by(
                    GenerationJobModel.priority.desc(),
                    GenerationJobModel.created_at.asc()
                )
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            job_models = result.scalars().all()
            
            return [self._to_entity(model) for model in job_models]
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting queued jobs: {e}")
            raise
    
    async def update(self, job: GenerationJob) -> GenerationJob:
        """Update an existing job."""
        try:
            # Get existing model
            stmt = select(GenerationJobModel).where(GenerationJobModel.id == job.id)
            result = await self.session.execute(stmt)
            job_model = result.scalar_one_or_none()
            
            if job_model is None:
                raise ValueError(f"Job with ID {job.id} not found")
            
            # Update fields from domain entity
            self._update_model_from_entity(job_model, job)
            
            await self.session.flush()
            await self.session.refresh(job_model)
            
            return self._to_entity(job_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error updating job {job.id}: {e}")
            await self.session.rollback()
            raise
    
    async def delete(self, job_id: UUID) -> bool:
        """Delete a job."""
        try:
            stmt = select(GenerationJobModel).where(GenerationJobModel.id == job_id)
            result = await self.session.execute(stmt)
            job_model = result.scalar_one_or_none()
            
            if job_model is None:
                return False
            
            await self.session.delete(job_model)
            await self.session.flush()
            
            return True
        
        except SQLAlchemyError as e:
            logger.error(f"Error deleting job {job_id}: {e}")
            await self.session.rollback()
            raise
    
    async def count_by_user_id(self, user_id: UUID) -> int:
        """Count jobs for a user."""
        try:
            stmt = (
                select(func.count())
                .select_from(GenerationJobModel)
                .where(GenerationJobModel.user_id == user_id)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one()
        
        except SQLAlchemyError as e:
            logger.error(f"Error counting jobs for user {user_id}: {e}")
            raise
    
    async def count_by_status(self, status: JobStatus) -> int:
        """Count jobs by status."""
        try:
            stmt = (
                select(func.count())
                .select_from(GenerationJobModel)
                .where(GenerationJobModel.status == status.value)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one()
        
        except SQLAlchemyError as e:
            logger.error(f"Error counting jobs by status {status}: {e}")
            raise
    
    async def get_active_jobs_count(self) -> int:
        """Get count of active (processing) jobs."""
        return await self.count_by_status(JobStatus.PROCESSING)
    
    async def exists(self, job_id: UUID) -> bool:
        """Check if a job exists."""
        try:
            stmt = select(func.count()).select_from(GenerationJobModel).where(
                GenerationJobModel.id == job_id
            )
            result = await self.session.execute(stmt)
            count = result.scalar_one()
            return count > 0
        
        except SQLAlchemyError as e:
            logger.error(f"Error checking if job {job_id} exists: {e}")
            raise
    
    def _to_entity(self, model: GenerationJobModel) -> GenerationJob:
        """Convert ORM model to domain entity."""
        return GenerationJob(
            id=model.id,
            user_id=model.user_id,
            content_type=ContentType(model.content_type),
            prompt=model.prompt,
            model_name=model.model_name,
            parameters=model.parameters,
            status=JobStatus(model.status),
            priority=model.priority,
            created_at=model.created_at,
            updated_at=model.updated_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            error_message=model.error_message,
            retry_count=model.retry_count,
            webhook_url=model.webhook_url,
        )
    
    def _to_model(self, entity: GenerationJob) -> GenerationJobModel:
        """Convert domain entity to ORM model."""
        return GenerationJobModel(
            id=entity.id,
            user_id=entity.user_id,
            content_type=entity.content_type.value,
            prompt=entity.prompt,
            model_name=entity.model_name,
            parameters=entity.parameters,
            status=entity.status.value,
            priority=entity.priority,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            error_message=entity.error_message,
            retry_count=entity.retry_count,
            webhook_url=entity.webhook_url,
        )
    
    def _update_model_from_entity(
        self,
        model: GenerationJobModel,
        entity: GenerationJob
    ) -> None:
        """Update ORM model fields from domain entity."""
        model.status = entity.status.value
        model.priority = entity.priority
        model.updated_at = entity.updated_at
        model.started_at = entity.started_at
        model.completed_at = entity.completed_at
        model.error_message = entity.error_message
        model.retry_count = entity.retry_count
        model.parameters = entity.parameters

