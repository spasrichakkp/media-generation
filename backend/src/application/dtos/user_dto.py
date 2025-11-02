"""User-related Data Transfer Objects (DTOs)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class UserResponse(BaseModel):
    """
    Response DTO for user information.
    
    This DTO represents the output sent to the API layer when
    returning user information.
    
    Attributes:
        id: Unique user identifier
        email: User's email address
        username: User's username
        created_at: When the user account was created
        is_active: Whether the user account is active
        is_admin: Whether the user has admin privileges
        quota_limit: Maximum number of jobs per day (None = unlimited)
        quota_used: Number of jobs used today
        quota_remaining: Number of jobs remaining today
        quota_reset_at: When the quota will reset
    """
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "email": "user@example.com",
                "username": "johndoe",
                "created_at": "2025-01-01T00:00:00Z",
                "is_active": True,
                "is_admin": False,
                "quota_limit": 100,
                "quota_used": 25,
                "quota_remaining": 75,
                "quota_reset_at": "2025-10-02T00:00:00Z"
            }
        }
    )
    
    id: UUID
    email: str
    username: str
    created_at: datetime
    is_active: bool
    is_admin: bool
    quota_limit: Optional[int] = None
    quota_used: int = 0
    quota_remaining: Optional[int] = None
    quota_reset_at: Optional[datetime] = None
    
    @property
    def has_quota(self) -> bool:
        """Check if user has remaining quota."""
        if self.quota_limit is None:
            return True  # Unlimited quota
        return self.quota_used < self.quota_limit

