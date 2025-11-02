"""API middleware - Authentication, error handling, logging."""

from .error_handlers import register_error_handlers

__all__ = [
    "register_error_handlers",
]

