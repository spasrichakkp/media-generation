"""User entity - Represents a user of the platform."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass
class User:
    """
    Represents a user of the media generation platform.
    
    Attributes:
        id: Unique identifier for the user
        email: User's email address
        username: User's username
        api_key_hash: Hashed API key for authentication
        created_at: When the user account was created
        updated_at: When the user account was last updated
        is_active: Whether the user account is active
        is_admin: Whether the user has admin privileges
        quota_limit: Maximum number of jobs per day (None = unlimited)
        quota_used: Number of jobs used today
        quota_reset_at: When the quota will reset
    """
    
    # Required fields
    email: str
    username: str
    
    # Auto-generated fields
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    is_admin: bool = False
    
    # Optional fields
    api_key_hash: Optional[str] = None
    updated_at: Optional[datetime] = None
    quota_limit: Optional[int] = 100  # Default: 100 jobs per day
    quota_used: int = 0
    quota_reset_at: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        # Validate email
        if not self.email or "@" not in self.email:
            raise ValueError("Invalid email address")
        
        # Validate username
        if not self.username or len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")
        
        # Set quota reset time if not set
        if self.quota_reset_at is None:
            self.quota_reset_at = self._get_next_reset_time()
    
    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def set_api_key_hash(self, api_key_hash: str) -> None:
        """
        Set the hashed API key.
        
        Args:
            api_key_hash: The hashed API key
        """
        if not api_key_hash:
            raise ValueError("API key hash cannot be empty")
        
        self.api_key_hash = api_key_hash
        self.updated_at = datetime.utcnow()
    
    def can_create_job(self) -> bool:
        """
        Check if user can create a new job based on quota.
        
        Returns:
            True if user can create a job, False otherwise
        """
        if not self.is_active:
            return False
        
        # Admin users have unlimited quota
        if self.is_admin:
            return True
        
        # No quota limit
        if self.quota_limit is None:
            return True
        
        # Check if quota needs reset
        if self.quota_reset_at and datetime.utcnow() >= self.quota_reset_at:
            self.reset_quota()
        
        # Check quota
        return self.quota_used < self.quota_limit
    
    def increment_quota(self) -> None:
        """Increment the quota usage counter."""
        self.quota_used += 1
        self.updated_at = datetime.utcnow()
    
    def reset_quota(self) -> None:
        """Reset the quota usage counter."""
        self.quota_used = 0
        self.quota_reset_at = self._get_next_reset_time()
        self.updated_at = datetime.utcnow()
    
    def set_quota_limit(self, limit: Optional[int]) -> None:
        """
        Set the quota limit.
        
        Args:
            limit: New quota limit (None = unlimited)
        """
        if limit is not None and limit < 0:
            raise ValueError("Quota limit must be non-negative")
        
        self.quota_limit = limit
        self.updated_at = datetime.utcnow()
    
    def make_admin(self) -> None:
        """Grant admin privileges to the user."""
        self.is_admin = True
        self.updated_at = datetime.utcnow()
    
    def revoke_admin(self) -> None:
        """Revoke admin privileges from the user."""
        self.is_admin = False
        self.updated_at = datetime.utcnow()
    
    def _get_next_reset_time(self) -> datetime:
        """
        Calculate the next quota reset time (midnight UTC).
        
        Returns:
            Next reset time
        """
        now = datetime.utcnow()
        next_reset = datetime(now.year, now.month, now.day, 0, 0, 0)
        
        # If it's already past midnight, set to tomorrow
        if next_reset <= now:
            from datetime import timedelta
            next_reset += timedelta(days=1)
        
        return next_reset
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary representation."""
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "quota_limit": self.quota_limit,
            "quota_used": self.quota_used,
            "quota_reset_at": self.quota_reset_at.isoformat() if self.quota_reset_at else None,
        }

