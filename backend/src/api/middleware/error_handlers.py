"""Error handlers for FastAPI application."""

import logging
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from ...application.exceptions import (
    ApplicationError,
    InvalidStateTransitionError,
    PermissionDeniedError,
    QuotaExceededError,
    ResourceNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    """
    Create standardized error response.
    
    Args:
        status_code: HTTP status code
        error_code: Application error code
        message: Human-readable error message
        details: Optional additional error details
        
    Returns:
        JSONResponse: Standardized error response
    """
    content: Dict[str, Any] = {
        "error": {
            "code": error_code,
            "message": message,
        }
    }
    
    if details is not None:
        content["error"]["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=content,
    )


def register_error_handlers(app: FastAPI) -> None:
    """
    Register error handlers for the FastAPI application.
    
    This function registers handlers for:
    - Application-specific exceptions (ResourceNotFoundError, etc.)
    - Pydantic validation errors
    - Generic exceptions
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        request: Request,
        exc: ResourceNotFoundError,
    ) -> JSONResponse:
        """Handle ResourceNotFoundError (404)."""
        logger.warning(f"Resource not found: {exc.message}")
        return create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=exc.code,
            message=exc.message,
        )
    
    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(
        request: Request,
        exc: PermissionDeniedError,
    ) -> JSONResponse:
        """Handle PermissionDeniedError (403)."""
        logger.warning(f"Permission denied: {exc.message}")
        return create_error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=exc.code,
            message=exc.message,
        )
    
    @app.exception_handler(QuotaExceededError)
    async def quota_exceeded_handler(
        request: Request,
        exc: QuotaExceededError,
    ) -> JSONResponse:
        """Handle QuotaExceededError (429)."""
        logger.warning(f"Quota exceeded: {exc.message}")
        return create_error_response(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=exc.code,
            message=exc.message,
            details={
                "quota_limit": exc.quota_limit,
                "quota_used": exc.quota_used,
            },
        )
    
    @app.exception_handler(InvalidStateTransitionError)
    async def invalid_state_transition_handler(
        request: Request,
        exc: InvalidStateTransitionError,
    ) -> JSONResponse:
        """Handle InvalidStateTransitionError (400)."""
        logger.warning(f"Invalid state transition: {exc.message}")
        return create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=exc.code,
            message=exc.message,
            details={
                "current_state": exc.current_state,
                "target_state": exc.target_state,
            },
        )
    
    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        """Handle application ValidationError (400)."""
        logger.warning(f"Validation error: {exc.message}")
        return create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=exc.code,
            message=exc.message,
        )
    
    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        """Handle generic ApplicationError (500)."""
        logger.error(f"Application error: {exc.message}")
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=exc.code,
            message=exc.message,
        )
    
    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle FastAPI RequestValidationError (422)."""
        logger.warning(f"Request validation error: {exc.errors()}")
        
        # Format validation errors for better readability
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            })
        
        return create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": errors},
        )
    
    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_error_handler(
        request: Request,
        exc: PydanticValidationError,
    ) -> JSONResponse:
        """Handle Pydantic ValidationError (422)."""
        logger.warning(f"Pydantic validation error: {exc.errors()}")
        
        # Format validation errors
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            })
        
        return create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message="Validation failed",
            details={"errors": errors},
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions (500)."""
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again later.",
        )

