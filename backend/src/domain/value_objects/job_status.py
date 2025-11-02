"""Job status value object."""

from enum import Enum


class JobStatus(str, Enum):
    """
    Represents the status of a generation job.
    
    State transitions:
    QUEUED -> PROCESSING -> COMPLETED
    QUEUED -> PROCESSING -> FAILED
    QUEUED -> CANCELLED
    PROCESSING -> CANCELLED
    """
    
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    def can_transition_to(self, new_status: "JobStatus") -> bool:
        """
        Check if transition to new status is valid.
        
        Args:
            new_status: The target status
            
        Returns:
            True if transition is valid, False otherwise
        """
        valid_transitions = {
            JobStatus.QUEUED: {JobStatus.PROCESSING, JobStatus.CANCELLED},
            JobStatus.PROCESSING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED},
            JobStatus.COMPLETED: set(),  # Terminal state
            JobStatus.FAILED: set(),  # Terminal state
            JobStatus.CANCELLED: set(),  # Terminal state
        }
        
        return new_status in valid_transitions.get(self, set())
    
    def is_terminal(self) -> bool:
        """Check if this is a terminal status (no further transitions possible)."""
        return self in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
    
    def is_active(self) -> bool:
        """Check if job is actively being processed."""
        return self == JobStatus.PROCESSING
    
    def is_pending(self) -> bool:
        """Check if job is waiting to be processed."""
        return self == JobStatus.QUEUED

