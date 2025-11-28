"""Generation Job entity - Core domain entity for content generation requests."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from ..value_objects import ContentType, JobStatus, ModelType


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    
    def __init__(self, current: JobStatus, target: JobStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Cannot transition from {current.value} to {target.value}"
        )


@dataclass
class GenerationJob:
    """
    Represents a content generation job.
    
    This is the core entity of the domain, representing a request to generate
    content (image, video, text) using an AI model.
    
    Attributes:
        id: Unique identifier for the job
        user_id: ID of the user who created the job
        content_type: Type of content to generate (image, video, text)
        prompt: Text prompt for content generation
        model_name: Name of the AI model to use
        parameters: Additional parameters for generation (resolution, duration, etc.)
        status: Current status of the job
        priority: Job priority (higher = processed first)
        created_at: When the job was created
        updated_at: When the job was last updated
        started_at: When processing started
        completed_at: When processing completed
        error_message: Error message if job failed
        retry_count: Number of times job has been retried
        webhook_url: Optional webhook URL for notifications
    """
    
    # Required fields
    user_id: UUID
    content_type: ContentType
    prompt: str
    
    # Auto-generated fields
    id: UUID = field(default_factory=uuid4)
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Optional fields
    model_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    webhook_url: Optional[str] = None
    result_url: Optional[str] = None  # URL to the generated content
    progress: int = 0  # Progress percentage (0-100)
    
    def __post_init__(self) -> None:
        """Validate and set defaults after initialization."""
        # Set default model if not provided
        if self.model_name is None:
            self.model_name = self.content_type.get_default_model()
        
        # Validate prompt
        if not self.prompt or not self.prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        # Validate priority 
        if self.priority < 0:
            raise ValueError("Priority must be non-negative")
    
    def mark_as_processing(self) -> None:
        """
        Mark the job as processing.
        
        Raises:
            InvalidStateTransitionError: If transition is not valid
        """
        self._transition_to(JobStatus.PROCESSING)
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_as_completed(self) -> None:
        """
        Mark the job as completed.
        
        Raises:
            InvalidStateTransitionError: If transition is not valid
        """
        self._transition_to(JobStatus.COMPLETED)
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_as_failed(self, error_message: str) -> None:
        """
        Mark the job as failed.
        
        Args:
            error_message: Description of the failure
            
        Raises:
            InvalidStateTransitionError: If transition is not valid
        """
        if not error_message:
            raise ValueError("Error message is required when marking job as failed")
        
        self._transition_to(JobStatus.FAILED)
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_as_cancelled(self) -> None:
        """
        Mark the job as cancelled.
        
        Raises:
            InvalidStateTransitionError: If transition is not valid
        """
        self._transition_to(JobStatus.CANCELLED)
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def increment_retry_count(self) -> None:
        """Increment the retry counter."""
        self.retry_count += 1
        self.updated_at = datetime.utcnow()
    
    def can_retry(self, max_retries: int = 3) -> bool:
        """
        Check if the job can be retried.
        
        Args:
            max_retries: Maximum number of retries allowed
            
        Returns:
            True if job can be retried, False otherwise
        """
        return (
            self.status == JobStatus.FAILED
            and self.retry_count < max_retries
        )
    
    def can_cancel(self) -> bool:
        """
        Check if the job can be cancelled.
        
        Returns:
            True if job can be cancelled, False otherwise
        """
        return not self.status.is_terminal()
    
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status.is_terminal()
    
    def is_active(self) -> bool:
        """Check if job is actively being processed."""
        return self.status.is_active()
    
    def is_pending(self) -> bool:
        """Check if job is waiting to be processed."""
        return self.status.is_pending()
    
    def get_processing_time(self) -> Optional[float]:
        """
        Get the processing time in seconds.
        
        Returns:
            Processing time in seconds, or None if not completed
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def get_queue_time(self) -> float:
        """
        Get the time spent in queue in seconds.
        
        Returns:
            Queue time in seconds
        """
        end_time = self.started_at or datetime.utcnow()
        return (end_time - self.created_at).total_seconds()
    
    def _transition_to(self, new_status: JobStatus) -> None:
        """
        Transition to a new status with validation.
        
        Args:
            new_status: The target status
            
        Raises:
            InvalidStateTransitionError: If transition is not valid
        """
        if not self.status.can_transition_to(new_status):
            raise InvalidStateTransitionError(self.status, new_status)
        
        self.status = new_status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "content_type": self.content_type.value,
            "prompt": self.prompt,
            "model_name": self.model_name,
            "parameters": self.parameters,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "webhook_url": self.webhook_url,
            "result_url": self.result_url,
        }

