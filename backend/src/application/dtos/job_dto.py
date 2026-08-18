"""Job-related Data Transfer Objects (DTOs)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict


class CreateJobRequest(BaseModel):
    """
    Request DTO for creating a new generation job.
    
    This DTO represents the input from the API layer when a user
    wants to create a new content generation job.
    
    Attributes:
        prompt: Text prompt for content generation (required)
        content_type: Type of content to generate (image, video, text)
        model_name: Name of the AI model to use (optional, uses default if not provided)
        parameters: Additional generation parameters (resolution, duration, etc.)
        priority: Job priority (0-10, higher = processed first)
        webhook_url: Optional webhook URL for job completion notifications
    
    Example:
        ```python
        request = CreateJobRequest(
            prompt="A beautiful sunset over mountains",
            content_type="video",
            parameters={"duration": 5, "resolution": "1080p"}
        )
        ```
    """
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        protected_namespaces=(),  # Disable warning for model_name field
        json_schema_extra={
            "example": {
                "prompt": "A beautiful sunset over mountains with birds flying",
                "content_type": "video",
                "model_name": "moneyprinter-turbo",
                "parameters": {
                    "duration": 5,
                    "resolution": "1080p",
                    "voice": "en-US-Neural2-A"
                },
                "priority": 5,
                "webhook_url": "https://example.com/webhook"
            }
        }
    )
    
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text prompt for content generation"
    )
    
    content_type: str = Field(
        ...,
        description="Type of content to generate (image, video, text)"
    )
    
    model_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Name of the AI model to use (optional)"
    )
    
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional generation parameters"
    )
    
    priority: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Job priority (0-10, higher = processed first)"
    )
    
    webhook_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional webhook URL for notifications"
    )
    
    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content_type is one of the allowed values."""
        allowed = {"image", "video", "text", "url"}
        if v.lower() not in allowed:
            raise ValueError(f"content_type must be one of: {', '.join(allowed)}")
        return v.lower()
    
    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate webhook URL format."""
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("webhook_url must start with http:// or https://")
        return v


class UpdateJobStatusRequest(BaseModel):
    """
    Request DTO for updating job status (internal use).
    
    Used by workers to update job status and progress.
    
    Attributes:
        status: New job status
        progress: Progress percentage (0-100)
        error_message: Error message if job failed
    """
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    status: str = Field(
        ...,
        description="New job status"
    )
    
    progress: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Progress percentage (0-100)"
    )
    
    error_message: Optional[str] = Field(
        None,
        max_length=1000,
        description="Error message if job failed"
    )
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is one of the allowed values."""
        allowed = {"queued", "processing", "completed", "failed", "cancelled"}
        if v.lower() not in allowed:
            raise ValueError(f"status must be one of: {', '.join(allowed)}")
        return v.lower()


class JobResponse(BaseModel):
    """
    Response DTO for job information.
    
    This DTO represents the output sent to the API layer when
    returning job information to the user.
    
    Attributes:
        id: Unique job identifier
        user_id: ID of the user who created the job
        content_type: Type of content being generated
        prompt: Text prompt used for generation
        model_name: Name of the AI model being used
        parameters: Generation parameters
        status: Current job status
        priority: Job priority
        progress: Progress percentage (0-100)
        created_at: When the job was created
        updated_at: When the job was last updated
        started_at: When processing started
        completed_at: When processing completed
        error_message: Error message if job failed
        retry_count: Number of times job has been retried
        result_url: URL to download the generated content (if completed)
    """
    
    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=(),  # Disable warning for model_name field
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "content_type": "video",
                "prompt": "A beautiful sunset over mountains",
                "model_name": "moneyprinter-turbo",
                "parameters": {"duration": 5, "resolution": "1080p"},
                "status": "processing",
                "priority": 5,
                "progress": 45.5,
                "created_at": "2025-10-01T12:00:00Z",
                "updated_at": "2025-10-01T12:05:00Z",
                "started_at": "2025-10-01T12:01:00Z",
                "completed_at": None,
                "error_message": None,
                "retry_count": 0,
                "result_url": None
            }
        }
    )
    
    id: UUID
    user_id: UUID
    content_type: str
    prompt: str
    model_name: str
    parameters: Dict[str, Any]
    status: str
    priority: int
    progress: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    result_url: Optional[str] = None


class JobListResponse(BaseModel):
    """
    Response DTO for paginated list of jobs.
    
    Used when returning multiple jobs with pagination metadata.
    
    Attributes:
        jobs: List of job responses
        total: Total number of jobs matching the query
        page: Current page number (1-indexed)
        page_size: Number of jobs per page
        has_next: Whether there are more pages
        has_prev: Whether there are previous pages
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "jobs": [],
                "total": 42,
                "page": 1,
                "page_size": 10,
                "has_next": True,
                "has_prev": False
            }
        }
    )
    
    jobs: List[JobResponse]
    total: int = Field(..., ge=0, description="Total number of jobs")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Number of jobs per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")

