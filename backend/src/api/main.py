"""FastAPI application - Main entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..config import get_settings
from ..infrastructure.database import check_db_health, init_db
from .middleware import register_error_handlers

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting Media Generation Platform API...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
        
        # Check database health
        if await check_db_health():
            logger.info("Database health check passed")
        else:
            logger.error("Database health check failed")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    logger.info("API startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Media Generation Platform API...")
    logger.info("API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Media Generation Platform API",
    description="""
    REST API for AI-powered media generation platform.
    
    ## Features
    
    * **Job Management** - Create, monitor, and cancel generation jobs
    * **Async Processing** - Non-blocking job execution with Celery
    * **Quota Management** - User-based quota tracking and limits
    * **Multiple Models** - Support for various AI models (MoneyPrinterTurbo, etc.)
    
    ## Authentication
    
    All endpoints require authentication using an API key.
    Include your API key in the `X-API-Key` header:
    
    ```
    X-API-Key: your-api-key-here
    ```
    
    ## Rate Limiting
    
    API requests are subject to rate limiting based on your quota.
    Check the `X-RateLimit-*` headers in responses for current limits.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Register error handlers
register_error_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.get_cors_methods_list(),
    allow_headers=["*"],
)


# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="API Root",
    response_description="Welcome message and API information",
)
async def root() -> JSONResponse:
    """
    API root endpoint.
    
    Returns basic information about the API and links to documentation.
    
    Returns:
        JSONResponse: Welcome message and API metadata
    """
    return JSONResponse(
        content={
            "message": "Welcome to Media Generation Platform API",
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        }
    )


# Health check endpoint (no authentication required)
@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    response_description="Service health status",
)
async def health_check() -> JSONResponse:
    """
    Health check endpoint.

    Checks the health of the API and its dependencies (database, cache, etc.).

    Returns:
        JSONResponse: Health status of all components
    """
    # Check database health
    try:
        db_healthy = await check_db_health()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_healthy = False

    # Overall health status
    healthy = db_healthy

    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "healthy" if healthy else "unhealthy",
            "components": {
                "api": "healthy",
                "database": "healthy" if db_healthy else "unhealthy",
            },
        }
    )


# Import and register route modules
from .routes import jobs

app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

