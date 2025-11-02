"""Application layer exceptions."""


class ApplicationError(Exception):
    """Base exception for application layer errors."""
    
    def __init__(self, message: str, code: str = "APPLICATION_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class ResourceNotFoundError(ApplicationError):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: str) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(message, code="RESOURCE_NOT_FOUND")


class PermissionDeniedError(ApplicationError):
    """Raised when user doesn't have permission to access a resource."""
    
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message, code="PERMISSION_DENIED")


class QuotaExceededError(ApplicationError):
    """Raised when user has exceeded their quota."""
    
    def __init__(self, quota_limit: int, quota_used: int) -> None:
        self.quota_limit = quota_limit
        self.quota_used = quota_used
        message = f"Quota exceeded: {quota_used}/{quota_limit} jobs used"
        super().__init__(message, code="QUOTA_EXCEEDED")


class InvalidStateTransitionError(ApplicationError):
    """Raised when an invalid state transition is attempted."""
    
    def __init__(self, current_state: str, target_state: str) -> None:
        self.current_state = current_state
        self.target_state = target_state
        message = f"Cannot transition from '{current_state}' to '{target_state}'"
        super().__init__(message, code="INVALID_STATE_TRANSITION")


class ValidationError(ApplicationError):
    """Raised when business logic validation fails."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, code="VALIDATION_ERROR")

