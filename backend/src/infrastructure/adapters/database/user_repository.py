"""PostgreSQL implementation of UserRepository."""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.entities import User
from ....domain.repositories import UserRepository
from ...database.models import UserModel

logger = logging.getLogger(__name__)


class PostgreSQLUserRepository(UserRepository):
    """
    PostgreSQL implementation of UserRepository using SQLAlchemy async.
    
    Converts between ORM models and domain entities.
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session
    
    async def create(self, user: User) -> User:
        """Create a new user in the database."""
        try:
            # Convert domain entity to ORM model
            user_model = self._to_model(user)
            
            # Add to session and flush
            self.session.add(user_model)
            await self.session.flush()
            await self.session.refresh(user_model)
            
            # Convert back to domain entity
            return self._to_entity(user_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error creating user: {e}")
            await self.session.rollback()
            raise
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by their ID."""
        try:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await self.session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model is None:
                return None
            
            return self._to_entity(user_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            raise
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by their email address."""
        try:
            stmt = select(UserModel).where(UserModel.email == email)
            result = await self.session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model is None:
                return None
            
            return self._to_entity(user_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by email {email}: {e}")
            raise
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by their username."""
        try:
            stmt = select(UserModel).where(UserModel.username == username)
            result = await self.session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model is None:
                return None
            
            return self._to_entity(user_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by username {username}: {e}")
            raise
    
    async def get_by_api_key_hash(self, api_key_hash: str) -> Optional[User]:
        """Get a user by their API key hash."""
        try:
            stmt = select(UserModel).where(UserModel.api_key_hash == api_key_hash)
            result = await self.session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model is None:
                return None
            
            return self._to_entity(user_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by API key hash: {e}")
            raise
    
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = False
    ) -> List[User]:
        """Get all users."""
        try:
            stmt = select(UserModel).order_by(UserModel.created_at.desc())
            
            if active_only:
                stmt = stmt.where(UserModel.is_active == True)
            
            stmt = stmt.limit(limit).offset(offset)
            
            result = await self.session.execute(stmt)
            user_models = result.scalars().all()
            
            return [self._to_entity(model) for model in user_models]
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting all users: {e}")
            raise
    
    async def update(self, user: User) -> User:
        """Update an existing user."""
        try:
            # Get existing model
            stmt = select(UserModel).where(UserModel.id == user.id)
            result = await self.session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model is None:
                raise ValueError(f"User with ID {user.id} not found")
            
            # Update fields from domain entity
            self._update_model_from_entity(user_model, user)
            
            await self.session.flush()
            await self.session.refresh(user_model)
            
            return self._to_entity(user_model)
        
        except SQLAlchemyError as e:
            logger.error(f"Error updating user {user.id}: {e}")
            await self.session.rollback()
            raise
    
    async def delete(self, user_id: UUID) -> bool:
        """Delete a user."""
        try:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await self.session.execute(stmt)
            user_model = result.scalar_one_or_none()
            
            if user_model is None:
                return False
            
            await self.session.delete(user_model)
            await self.session.flush()
            
            return True
        
        except SQLAlchemyError as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            await self.session.rollback()
            raise
    
    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists."""
        try:
            stmt = select(func.count()).select_from(UserModel).where(UserModel.email == email)
            result = await self.session.execute(stmt)
            count = result.scalar_one()
            return count > 0
        
        except SQLAlchemyError as e:
            logger.error(f"Error checking if email {email} exists: {e}")
            raise
    
    async def exists_by_username(self, username: str) -> bool:
        """Check if a user with the given username exists."""
        try:
            stmt = select(func.count()).select_from(UserModel).where(
                UserModel.username == username
            )
            result = await self.session.execute(stmt)
            count = result.scalar_one()
            return count > 0
        
        except SQLAlchemyError as e:
            logger.error(f"Error checking if username {username} exists: {e}")
            raise
    
    async def count(self, active_only: bool = False) -> int:
        """Count users."""
        try:
            stmt = select(func.count()).select_from(UserModel)
            
            if active_only:
                stmt = stmt.where(UserModel.is_active == True)
            
            result = await self.session.execute(stmt)
            return result.scalar_one()
        
        except SQLAlchemyError as e:
            logger.error(f"Error counting users: {e}")
            raise
    
    def _to_entity(self, model: UserModel) -> User:
        """Convert ORM model to domain entity."""
        return User(
            id=model.id,
            email=model.email,
            username=model.username,
            api_key_hash=model.api_key_hash,
            created_at=model.created_at,
            updated_at=model.updated_at,
            is_active=model.is_active,
            is_admin=model.is_admin,
            quota_limit=model.quota_limit,
            quota_used=model.quota_used,
            quota_reset_at=model.quota_reset_at,
        )
    
    def _to_model(self, entity: User) -> UserModel:
        """Convert domain entity to ORM model."""
        return UserModel(
            id=entity.id,
            email=entity.email,
            username=entity.username,
            api_key_hash=entity.api_key_hash,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            is_active=entity.is_active,
            is_admin=entity.is_admin,
            quota_limit=entity.quota_limit,
            quota_used=entity.quota_used,
            quota_reset_at=entity.quota_reset_at,
        )
    
    def _update_model_from_entity(self, model: UserModel, entity: User) -> None:
        """Update ORM model fields from domain entity."""
        model.email = entity.email
        model.username = entity.username
        model.api_key_hash = entity.api_key_hash
        model.updated_at = entity.updated_at
        model.is_active = entity.is_active
        model.is_admin = entity.is_admin
        model.quota_limit = entity.quota_limit
        model.quota_used = entity.quota_used
        model.quota_reset_at = entity.quota_reset_at

