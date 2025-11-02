"""User Repository interface - Port for user data access."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities import User


class UserRepository(ABC):
    """
    Abstract repository interface for User entities.
    
    This is a port in the Hexagonal Architecture - it defines the contract
    that infrastructure adapters must implement.
    """
    
    @abstractmethod
    async def create(self, user: User) -> User:
        """
        Create a new user.
        
        Args:
            user: The user to create
            
        Returns:
            The created user with any database-generated fields populated
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get a user by their ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            The user if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by their email address.
        
        Args:
            email: The email address
            
        Returns:
            The user if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by their username.
        
        Args:
            username: The username
            
        Returns:
            The user if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_api_key_hash(self, api_key_hash: str) -> Optional[User]:
        """
        Get a user by their API key hash.
        
        Args:
            api_key_hash: The hashed API key
            
        Returns:
            The user if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = False
    ) -> List[User]:
        """
        Get all users.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            active_only: If True, only return active users
            
        Returns:
            List of users
        """
        pass
    
    @abstractmethod
    async def update(self, user: User) -> User:
        """
        Update an existing user.
        
        Args:
            user: The user to update
            
        Returns:
            The updated user
        """
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """
        Check if a user with the given email exists.
        
        Args:
            email: The email address
            
        Returns:
            True if user exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def exists_by_username(self, username: str) -> bool:
        """
        Check if a user with the given username exists.
        
        Args:
            username: The username
            
        Returns:
            True if user exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def count(self, active_only: bool = False) -> int:
        """
        Count users.
        
        Args:
            active_only: If True, only count active users
            
        Returns:
            Number of users
        """
        pass

