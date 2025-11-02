"""Celery application configuration for async task processing."""

from celery import Celery
from kombu import Exchange, Queue
from loguru import logger

from ...config import get_settings

# Get settings
settings = get_settings()

# Create Celery application instance
celery_app = Celery(
    "media_generation",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_track_started=True,
    task_time_limit=settings.task_timeout,  # Hard time limit (1 hour default)
    task_soft_time_limit=settings.task_timeout - 300,  # Soft limit (55 min default)
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Reject task if worker crashes
    
    # Retry settings
    task_default_retry_delay=settings.task_retry_delay,  # 5 minutes default
    task_max_retries=settings.task_max_retries,  # 3 retries default
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results to backend
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Fetch one task at a time (for long-running tasks)
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
    worker_disable_rate_limits=False,
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Task routing
    task_routes={
        "src.infrastructure.tasks.video_generation.generate_video_task": {
            "queue": "video_generation",
            "routing_key": "video.generate",
        },
    },
    
    # Queue definitions
    task_queues=(
        Queue(
            "video_generation",
            Exchange("video_generation", type="direct"),
            routing_key="video.generate",
            queue_arguments={"x-max-priority": 10},  # Enable priority queue
        ),
        Queue(
            "default",
            Exchange("default", type="direct"),
            routing_key="default",
        ),
    ),
    
    # Default queue
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Task autodiscovery
celery_app.autodiscover_tasks(
    [
        "src.infrastructure.tasks",
    ]
)


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery configuration."""
    logger.info(f"Request: {self.request!r}")
    return {"status": "ok", "task_id": self.request.id}


# Celery signals for logging
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Set up periodic tasks (if needed in the future)."""
    logger.info("Celery periodic tasks configured")


@celery_app.on_after_finalize.connect
def setup_task_logger(sender, **kwargs):
    """Set up task logging."""
    logger.info("Celery application finalized and ready")
    logger.info(f"Broker: {settings.celery_broker_url}")
    logger.info(f"Backend: {settings.celery_result_backend}")


# Task event handlers for monitoring
@celery_app.task(bind=True)
def on_task_failure(self, exc, task_id, args, kwargs, einfo):
    """Handle task failure."""
    logger.error(f"Task {task_id} failed: {exc}")
    logger.error(f"Exception info: {einfo}")


@celery_app.task(bind=True)
def on_task_success(self, result, task_id, args, kwargs):
    """Handle task success."""
    logger.info(f"Task {task_id} completed successfully")


# Export celery app
__all__ = ["celery_app", "debug_task"]

