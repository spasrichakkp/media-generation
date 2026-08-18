"""PostgreSQL implementation of Job Repository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities import GenerationJob
from ...domain.repositories import JobRepository
from ...domain.value_objects import ContentType, JobStatus
from ..database.models import GenerationJobModel


class PostgresJobRepository(JobRepository):
    """
    PostgreSQL implementation of JobRepository using SQLAlchemy.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy AsyncSession
        """
        self.session = session

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
            result_url=model.result_url,
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
            result_url=entity.result_url,
            webhook_url=entity.webhook_url,
        )

    async def create(self, job: GenerationJob) -> GenerationJob:
        """Create a new job."""
        model = self._to_model(job)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, job_id: UUID) -> Optional[GenerationJob]:
        """Get a job by its ID."""
        result = await self.session.execute(
            select(GenerationJobModel).where(GenerationJobModel.id == job_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_user_id(
        self, user_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[GenerationJob]:
        """Get all jobs for a user."""
        result = await self.session.execute(
            select(GenerationJobModel)
            .where(GenerationJobModel.user_id == user_id)
            .order_by(desc(GenerationJobModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_by_status(
        self, status: JobStatus, limit: int = 100, offset: int = 0
    ) -> List[GenerationJob]:
        """Get jobs by status."""
        result = await self.session.execute(
            select(GenerationJobModel)
            .where(GenerationJobModel.status == status.value)
            .order_by(desc(GenerationJobModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def get_queued_jobs(self, limit: int = 100) -> List[GenerationJob]:
        """
        Get queued jobs ordered by priority (highest first) and creation time.
        """
        result = await self.session.execute(
            select(GenerationJobModel)
            .where(GenerationJobModel.status == JobStatus.QUEUED.value)
            .order_by(desc(GenerationJobModel.priority), GenerationJobModel.created_at)
            .limit(limit)
        )
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def update(self, job: GenerationJob) -> GenerationJob:
        """Update an existing job."""
        import logging
        from sqlalchemy import update
        logger = logging.getLogger(__name__)
        
        logger.info(f"DEBUG_REPO: Updating job {job.id}. Entity result_url: {job.result_url}")
        
        stmt = (
            update(GenerationJobModel)
            .where(GenerationJobModel.id == job.id)
            .values(
                status=job.status.value,
                result_url=job.result_url,
                progress=job.progress,
                updated_at=func.now(),
                started_at=job.started_at,
                completed_at=job.completed_at,
                error_message=job.error_message,
                retry_count=job.retry_count
            )
            .returning(GenerationJobModel)
        )
        
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        logger.info(f"DEBUG_REPO: Updated model result_url: {model.result_url}")
        
        await self.session.flush()
        return self._to_entity(model)

    async def delete(self, job_id: UUID) -> bool:
        """Delete a job."""
        result = await self.session.execute(
            select(GenerationJobModel).where(GenerationJobModel.id == job_id)
        )
        model = result.scalar_one_or_none()
        
        if model:
            await self.session.delete(model)
            await self.session.flush()
            return True
        return False

    async def count_by_user_id(self, user_id: UUID) -> int:
        """Count jobs for a user."""
        result = await self.session.execute(
            select(func.count(GenerationJobModel.id)).where(GenerationJobModel.user_id == user_id)
        )
        return result.scalar_one() or 0

    async def count_by_status(self, status: JobStatus) -> int:
        """Count jobs by status."""
        result = await self.session.execute(
            select(func.count(GenerationJobModel.id)).where(GenerationJobModel.status == status.value)
        )
        return result.scalar_one() or 0

    async def get_active_jobs_count(self) -> int:
        """Get count of active (processing) jobs."""
        result = await self.session.execute(
            select(func.count(GenerationJobModel.id)).where(
                GenerationJobModel.status == JobStatus.PROCESSING.value
            )
        )
        return result.scalar_one() or 0

    async def exists(self, job_id: UUID) -> bool:
        """Check if a job exists."""
        result = await self.session.execute(
            select(GenerationJobModel.id).where(GenerationJobModel.id == job_id).limit(1)
        )
        return result.scalar_one_or_none() is not None
