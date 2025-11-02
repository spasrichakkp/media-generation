"""PostgreSQL implementation of ContentRepository."""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.entities import GeneratedContent
from ....domain.repositories import ContentRepository
from ....domain.value_objects import ContentType
from ...database.models import GeneratedContentModel

logger = logging.getLogger(__name__)


class PostgreSQLContentRepository(ContentRepository):
    """
    PostgreSQL implementation of ContentRepository using SQLAlchemy async.
    
    Converts between ORM models and domain entities.
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
    
    async def create(self, content: GeneratedContent) -> GeneratedContent:
        """Create a new content record in the database."""
        try:
            # Convert domain entity to ORM model
            content_model = self._to_model(content)
            
            # Add to session and flush
            self.session.add(content_model)
            await self.session.flush()
            await self.session.refresh(content_model)
            
            # Convert back to domain entity
            return self._to_entity(content_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error creating content: {e}")
            await self.session.rollback()
            raise
    
    async def get_by_id(self, content_id: UUID) -> Optional[GeneratedContent]:
        """Get content by its ID."""
        try:
            stmt = select(GeneratedContentModel).where(
                GeneratedContentModel.id == content_id
            )
            result = await self.session.execute(stmt)
            content_model = result.scalar_one_or_none()
            
            if content_model is None:
                return None
            
            return self._to_entity(content_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting content by ID {content_id}: {e}")
            raise
    
    async def get_by_job_id(self, job_id: UUID) -> Optional[GeneratedContent]:
        """Get content by job ID."""
        try:
            stmt = select(GeneratedContentModel).where(
                GeneratedContentModel.job_id == job_id
            )
            result = await self.session.execute(stmt)
            content_model = result.scalar_one_or_none()
            
            if content_model is None:
                return None
            
            return self._to_entity(content_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting content by job ID {job_id}: {e}")
            raise
    
    async def get_by_content_type(
        self,
        content_type: ContentType,
        limit: int = 100,
        offset: int = 0,
        public_only: bool = False
    ) -> List[GeneratedContent]:
        """Get content by type."""
        try:
            stmt = select(GeneratedContentModel).where(
                GeneratedContentModel.content_type == content_type.value
            )
            
            if public_only:
                stmt = stmt.where(GeneratedContentModel.is_public == True)
            
            stmt = stmt.order_by(GeneratedContentModel.created_at.desc())
            stmt = stmt.limit(limit).offset(offset)
            
            result = await self.session.execute(stmt)
            content_models = result.scalars().all()
            
            return [self._to_entity(model) for model in content_models]
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting content by type {content_type}: {e}")
            raise
    
    async def get_public_content(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[GeneratedContent]:
        """Get public content."""
        try:
            stmt = (
                select(GeneratedContentModel)
                .where(GeneratedContentModel.is_public == True)
                .order_by(GeneratedContentModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await self.session.execute(stmt)
            content_models = result.scalars().all()
            
            return [self._to_entity(model) for model in content_models]
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting public content: {e}")
            raise
    
    async def get_nsfw_content(
        self,
        threshold: float = 0.7,
        limit: int = 100,
        offset: int = 0
    ) -> List[GeneratedContent]:
        """Get content flagged as NSFW."""
        try:
            stmt = (
                select(GeneratedContentModel)
                .where(GeneratedContentModel.nsfw_score >= threshold)
                .order_by(GeneratedContentModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await self.session.execute(stmt)
            content_models = result.scalars().all()
            
            return [self._to_entity(model) for model in content_models]
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting NSFW content: {e}")
            raise
    
    async def get_unmoderated_content(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[GeneratedContent]:
        """Get content that hasn't been moderated."""
        try:
            stmt = (
                select(GeneratedContentModel)
                .where(GeneratedContentModel.is_moderated == False)
                .order_by(GeneratedContentModel.created_at.asc())
                .limit(limit)
                .offset(offset)
            )
            result = await self.session.execute(stmt)
            content_models = result.scalars().all()
            
            return [self._to_entity(model) for model in content_models]
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting unmoderated content: {e}")
            raise
    
    async def update(self, content: GeneratedContent) -> GeneratedContent:
        """Update existing content."""
        try:
            # Get existing model
            stmt = select(GeneratedContentModel).where(
                GeneratedContentModel.id == content.id
            )
            result = await self.session.execute(stmt)
            content_model = result.scalar_one_or_none()
            
            if content_model is None:
                raise ValueError(f"Content with ID {content.id} not found")
            
            # Update fields from domain entity
            self._update_model_from_entity(content_model, content)
            
            await self.session.flush()
            await self.session.refresh(content_model)
            
            return self._to_entity(content_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error updating content {content.id}: {e}")
            await self.session.rollback()
            raise
    
    async def delete(self, content_id: UUID) -> bool:
        """Delete content."""
        try:
            stmt = select(GeneratedContentModel).where(
                GeneratedContentModel.id == content_id
            )
            result = await self.session.execute(stmt)
            content_model = result.scalar_one_or_none()
            
            if content_model is None:
                return False
            
            await self.session.delete(content_model)
            await self.session.flush()
            
            return True
        
        except SQLAlchemyError as e:
            logger.error(f"Error deleting content {content_id}: {e}")
            await self.session.rollback()
            raise
    
    async def delete_by_job_id(self, job_id: UUID) -> bool:
        """Delete content by job ID."""
        try:
            stmt = select(GeneratedContentModel).where(
                GeneratedContentModel.job_id == job_id
            )
            result = await self.session.execute(stmt)
            content_model = result.scalar_one_or_none()
            
            if content_model is None:
                return False
            
            await self.session.delete(content_model)
            await self.session.flush()
            
            return True
        
        except SQLAlchemyError as e:
            logger.error(f"Error deleting content by job ID {job_id}: {e}")
            await self.session.rollback()
            raise
    
    async def exists(self, content_id: UUID) -> bool:
        """Check if content exists."""
        try:
            stmt = select(func.count()).select_from(GeneratedContentModel).where(
                GeneratedContentModel.id == content_id
            )
            result = await self.session.execute(stmt)
            count = result.scalar_one()
            return count > 0
        
        except SQLAlchemyError as e:
            logger.error(f"Error checking if content {content_id} exists: {e}")
            raise
    
    async def count_by_content_type(self, content_type: ContentType) -> int:
        """Count content by type."""
        try:
            stmt = (
                select(func.count())
                .select_from(GeneratedContentModel)
                .where(GeneratedContentModel.content_type == content_type.value)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one()
        
        except SQLAlchemyError as e:
            logger.error(f"Error counting content by type {content_type}: {e}")
            raise
    
    def _to_entity(self, model: GeneratedContentModel) -> GeneratedContent:
        """Convert ORM model to domain entity."""
        return GeneratedContent(
            id=model.id,
            job_id=model.job_id,
            content_url=model.content_url,
            content_type=ContentType(model.content_type),
            file_size=model.file_size,
            file_format=model.file_format,
            width=model.width,
            height=model.height,
            duration=model.duration,
            metadata=model.content_metadata,
            created_at=model.created_at,
            is_public=model.is_public,
            nsfw_score=model.nsfw_score,
            is_moderated=model.is_moderated,
        )
    
    def _to_model(self, entity: GeneratedContent) -> GeneratedContentModel:
        """Convert domain entity to ORM model."""
        return GeneratedContentModel(
            id=entity.id,
            job_id=entity.job_id,
            content_url=entity.content_url,
            content_type=entity.content_type.value,
            file_size=entity.file_size,
            file_format=entity.file_format,
            width=entity.width,
            height=entity.height,
            duration=entity.duration,
            content_metadata=entity.metadata,
            created_at=entity.created_at,
            is_public=entity.is_public,
            nsfw_score=entity.nsfw_score,
            is_moderated=entity.is_moderated,
        )
    
    def _update_model_from_entity(
        self,
        model: GeneratedContentModel,
        entity: GeneratedContent
    ) -> None:
        """Update ORM model fields from domain entity."""
        model.file_size = entity.file_size
        model.width = entity.width
        model.height = entity.height
        model.duration = entity.duration
        model.content_metadata = entity.metadata
        model.is_public = entity.is_public
        model.nsfw_score = entity.nsfw_score
        model.is_moderated = entity.is_moderated

