"""PostgreSQL implementation of User Repository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities import User
from ...domain.repositories import UserRepository
from ...domain.value_objects import UserRole
from ..database.models import UserModel


class PostgresUserRepository(UserRepository):
    """
    PostgreSQL implementation of UserRepository using SQLAlchemy.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.

        Args:
            session: SQLAlchemy AsyncSession
        """
        self.session = session

    def _to_entity(self, model: UserModel) -> User:
        """Convert ORM model to domain entity."""
        return User(
            id=model.id,
            email=model.email,
            username=model.username,
            api_key_hash=model.api_key_hash,
            role=UserRole.ADMIN if model.is_admin else UserRole.USER,
            is_active=model.is_active,
            quota_limit=model.quota_limit,
            quota_used=model.quota_used,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: User) -> UserModel:
        """Convert domain entity to ORM model."""
        return UserModel(
            id=entity.id,
            email=entity.email,
            username=entity.username,
            api_key_hash=entity.api_key_hash,
            is_admin=entity.role == UserRole.ADMIN,
            is_active=entity.is_active,
            quota_limit=entity.quota_limit,
            quota_used=entity.quota_used,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def create(self, user: User) -> User:
        """Create a new user."""
        model = self._to_model(user)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by their ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by their email address."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by their username."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_api_key_hash(self, api_key_hash: str) -> Optional[User]:
        """Get a user by their API key hash."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.api_key_hash == api_key_hash)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_all(
        self, limit: int = 100, offset: int = 0, active_only: bool = False
    ) -> List[User]:
        """Get all users."""
        query = select(UserModel).limit(limit).offset(offset)
        
        if active_only:
            query = query.where(UserModel.is_active == True)  # noqa: E712
            
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def update(self, user: User) -> User:
        """Update an existing user."""
        # We merge the entity state into the session
        # Note: In a real app, we might want to fetch first to ensure existence
        # or handle specific field updates. Here we do a full update.
        model = self._to_model(user)
        merged_model = await self.session.merge(model)
        await self.session.flush()
        return self._to_entity(merged_model)

    async def delete(self, user_id: UUID) -> bool:
        """Delete a user."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        
        if model:
            await self.session.delete(model)
            await self.session.flush()
            return True
        return False

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists."""
        result = await self.session.execute(
            select(UserModel.id).where(UserModel.email == email).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def exists_by_username(self, username: str) -> bool:
        """Check if a user with the given username exists."""
        result = await self.session.execute(
            select(UserModel.id).where(UserModel.username == username).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def count(self, active_only: bool = False) -> int:
        """Count users."""
        query = select(func.count(UserModel.id))
        
        if active_only:
            query = query.where(UserModel.is_active == True)  # noqa: E712
            
        result = await self.session.execute(query)
        return result.scalar_one() or 0
