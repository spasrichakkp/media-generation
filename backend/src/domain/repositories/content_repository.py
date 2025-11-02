"""Content Repository interface - Port for generated content data access."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..entities import GeneratedContent
from ..value_objects import ContentType


class ContentRepository(ABC):
    """
    Abstract repository interface for GeneratedContent entities.
    
    This is a port in the Hexagonal Architecture - it defines the contract
    that infrastructure adapters must implement.
    """
    
    @abstractmethod
    async def create(self, content: GeneratedContent) -> GeneratedContent:
        """
        Create a new content record.
        
        Args:
            content: The content to create
            
        Returns:
            The created content with any database-generated fields populated
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, content_id: UUID) -> Optional[GeneratedContent]:
        """
        Get content by its ID.
        
        Args:
            content_id: The content ID
            
        Returns:
            The content if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_job_id(self, job_id: UUID) -> Optional[GeneratedContent]:
        """
        Get content by job ID.
        
        Args:
            job_id: The job ID
            
        Returns:
            The content if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_by_content_type(
        self,
        content_type: ContentType,
        limit: int = 100,
        offset: int = 0,
        public_only: bool = False
    ) -> List[GeneratedContent]:
        """
        Get content by type.
        
        Args:
            content_type: The content type
            limit: Maximum number of items to return
            offset: Number of items to skip
            public_only: If True, only return public content
            
        Returns:
            List of content items
        """
        pass
    
    @abstractmethod
    async def get_public_content(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[GeneratedContent]:
        """
        Get public content.
        
        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            List of public content items
        """
        pass
    
    @abstractmethod
    async def get_nsfw_content(
        self,
        threshold: float = 0.7,
        limit: int = 100,
        offset: int = 0
    ) -> List[GeneratedContent]:
        """
        Get content flagged as NSFW.
        
        Args:
            threshold: NSFW score threshold
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            List of NSFW content items
        """
        pass
    
    @abstractmethod
    async def get_unmoderated_content(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[GeneratedContent]:
        """
        Get content that hasn't been moderated.
        
        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            List of unmoderated content items
        """
        pass
    
    @abstractmethod
    async def update(self, content: GeneratedContent) -> GeneratedContent:
        """
        Update existing content.
        
        Args:
            content: The content to update
            
        Returns:
            The updated content
        """
        pass
    
    @abstractmethod
    async def delete(self, content_id: UUID) -> bool:
        """
        Delete content.
        
        Args:
            content_id: The content ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def delete_by_job_id(self, job_id: UUID) -> bool:
        """
        Delete content by job ID.
        
        Args:
            job_id: The job ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, content_id: UUID) -> bool:
        """
        Check if content exists.
        
        Args:
            content_id: The content ID
            
        Returns:
            True if content exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def count_by_content_type(self, content_type: ContentType) -> int:
        """
        Count content by type.
        
        Args:
            content_type: The content type
            
        Returns:
            Number of content items
        """
        pass

