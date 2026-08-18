"""Video generation Celery task."""

import asyncio
from datetime import datetime
from uuid import UUID

from celery import Task
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_settings
from ...domain.entities import GenerationJob
from ...domain.value_objects import JobStatus
from ..adapters.database import PostgreSQLJobRepository
from ..database import get_session_factory
from .celery_app import celery_app

# Get settings
settings = get_settings()


class VideoGenerationTask(Task):
    """
    Custom Celery task class for video generation.

    Provides automatic retry logic and error handling.
    """

    autoretry_for = (Exception,)
    retry_kwargs = {
        "max_retries": settings.task_max_retries,
        "countdown": settings.task_retry_delay,
    }
    retry_backoff = True  # Exponential backoff
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True  # Add random jitter to prevent thundering herd


async def update_job_status(
    job_id: UUID,
    status: JobStatus,
    progress: int | None = None,
    error_message: str | None = None,
    result_url: str | None = None,
) -> None:
    """
    Update job status in database.

    Args:
        job_id: Job ID to update
        status: New job status
        progress: Optional progress percentage (0-100)
        error_message: Optional error message for failed jobs
        result_url: Optional URL to the generated content
    """
    async_session = get_session_factory()
    async with async_session() as session:
        try:
            job_repo = PostgreSQLJobRepository(session)

            # Get job
            job = await job_repo.get_by_id(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            # Update status (only transition if different from current status)
            if status != job.status:
                if status == JobStatus.PROCESSING:
                    job.mark_as_processing()
                elif status == JobStatus.COMPLETED:
                    job.mark_as_completed()
                elif status == JobStatus.FAILED:
                    job.mark_as_failed(error_message or "Unknown error")
                elif status == JobStatus.CANCELLED:
                    job.mark_as_cancelled()
            else:
                # Already in target status, just update timestamp
                job.updated_at = datetime.utcnow()

            # Update progress if provided
            if progress is not None:
                job.progress = progress

            # Update result URL if provided
            if result_url is not None:
                job.result_url = result_url

            # Save to database
            logger.info(f"Updating job {job_id} in DB. Status: {status}, Result URL: {job.result_url}")
            await job_repo.update(job)
            await session.commit()

            logger.info(f"Job {job_id} status updated to {status.value}, progress: {job.progress}%")

        except Exception as e:
            logger.error(f"Failed to update job status: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_job_details(job_id: UUID) -> GenerationJob | None:
    """
    Fetch job details from database.

    Args:
        job_id: Job ID to fetch

    Returns:
        GenerationJob entity or None if not found
    """
    async_session = get_session_factory()
    async with async_session() as session:
        try:
            job_repo = PostgreSQLJobRepository(session)
            job = await job_repo.get_by_id(job_id)
            return job
        except Exception as e:
            logger.error(f"Failed to fetch job details: {e}")
            return None
        finally:
            await session.close()


async def generate_video_async(job: GenerationJob) -> str:
    """
    Generate video asynchronously using MoviePyVideoGenerator.

    Args:
        job: GenerationJob entity with job details

    Returns:
        URL of the generated video

    Raises:
        Exception: If video generation fails
    """
    logger.info(f"Starting video generation for job {job.id}")
    logger.info(f"Prompt: {job.prompt}")
    logger.info(f"Content type: {job.content_type.value}")
    logger.info(f"Model: {job.model_name}")
    logger.info(f"Parameters: {job.parameters}")

    # Import here to avoid circular imports
    from ..adapters.storage import S3Storage
    from ..services import MoviePyVideoGenerator
    from ..services.huggingface_video_generator import HuggingFaceVideoGenerator

    # Initialize services based on video provider
    if settings.video_provider == "huggingface":
        video_generator = HuggingFaceVideoGenerator(settings, storage_adapter)
    else:
        video_generator = MoviePyVideoGenerator(settings, storage_adapter)

    storage_adapter = S3Storage(
        access_key_id=settings.s3_access_key_id,
        secret_access_key=settings.s3_secret_access_key,
        bucket_name=settings.s3_bucket_name,
        region=settings.s3_region,
        endpoint_url=settings.s3_endpoint_url,
        use_ssl=settings.use_ssl,
    )

    audio_path = None
    video_path = None

    try:
        # Update progress: 10% - Starting
        await update_job_status(job.id, JobStatus.PROCESSING, progress=10)

        # Step 1: Generate script (10% -> 30%)
        logger.info("Step 1: Generating video script...")
        script = await video_generator.generate_script(
            prompt=job.prompt,
            parameters=job.parameters,
            progress_callback=None,
        )
        await update_job_status(job.id, JobStatus.PROCESSING, progress=30)
        logger.info(f"Script generated: {len(script)} characters")

        # Step 2: Generate voiceover (30% -> 50%)
        logger.info("Step 2: Generating voiceover...")
        audio_path = await video_generator.generate_voiceover(
            script=script,
            voice=None,  # Use default from settings
            progress_callback=None,
        )
        await update_job_status(job.id, JobStatus.PROCESSING, progress=50)
        logger.info(f"Voiceover generated: {audio_path}")

        # Step 3: Generate video (50% -> 70%)
        logger.info("Step 3: Composing video...")
        video_path = await video_generator.generate_video(
            script=script,
            audio_path=audio_path,
            parameters=job.parameters,
            progress_callback=None,
        )
        await update_job_status(job.id, JobStatus.PROCESSING, progress=70)
        logger.info(f"Video generated: {video_path}")

        # Step 4: Upload to S3 (70% -> 90%)
        logger.info("Step 4: Uploading to storage...")
        video_url = await video_generator.upload_video(
            video_path=video_path,
            job_id=job.id,
            progress_callback=None,
        )
        await update_job_status(job.id, JobStatus.PROCESSING, progress=90)
        logger.info(f"Video uploaded: {video_url}")

        # Clean up temporary files
        await video_generator.cleanup_temp_files(audio_path, video_path)

        logger.info(f"Video generation completed successfully: {video_url}")
        return video_url

    except Exception as e:
        logger.error(f"Video generation failed: {e}")

        # Clean up temporary files on error
        if audio_path or video_path:
            try:
                await video_generator.cleanup_temp_files(
                    *(f for f in [audio_path, video_path] if f)
                )
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp files: {cleanup_error}")

        raise


@celery_app.task(
    bind=True,
    base=VideoGenerationTask,
    name="src.infrastructure.tasks.video_generation.generate_video_task",
    queue="video_generation",
)
def generate_video_task(self, job_id: str) -> dict:
    """
    Celery task for video generation.

    This task:
    1. Fetches job details from database
    2. Updates job status to PROCESSING
    3. Generates the video (placeholder for now)
    4. Updates job status to COMPLETED or FAILED
    5. Stores the result URL in the database

    Args:
        job_id: UUID of the job to process (as string)

    Returns:
        dict: Task result with status and video URL

    Raises:
        Exception: If task fails after all retries
    """
    # Convert job_id string to UUID
    try:
        job_uuid = UUID(job_id)
    except ValueError as e:
        logger.error(f"Invalid job_id format: {job_id}")
        raise ValueError(f"Invalid job_id: {job_id}") from e

    logger.info(f"Starting video generation task for job {job_uuid}")
    logger.info(f"Task ID: {self.request.id}")
    logger.info(f"Retry count: {self.request.retries}")

    try:
        # Run async code in event loop
        loop = asyncio.get_event_loop()

        # Fetch job details
        job = loop.run_until_complete(get_job_details(job_uuid))
        if not job:
            error_msg = f"Job {job_uuid} not found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Check if job is already in terminal state
        if job.status in [JobStatus.COMPLETED, JobStatus.CANCELLED]:
            logger.warning(f"Job {job_uuid} is already in terminal state: {job.status.value}")
            return {
                "status": "skipped",
                "job_id": str(job_uuid),
                "message": f"Job already {job.status.value}",
            }

        # Update status to PROCESSING
        loop.run_until_complete(update_job_status(job_uuid, JobStatus.PROCESSING, progress=0))

        # Generate video
        video_url = loop.run_until_complete(generate_video_async(job))

        # Update job with result URL and mark as completed
        loop.run_until_complete(
            update_job_status(
                job_uuid,
                JobStatus.COMPLETED,
                progress=100,
                result_url=video_url,
            )
        )

        logger.info(f"Video generation completed successfully: {video_url}")

        return {
            "status": "success",
            "job_id": str(job_uuid),
            "video_url": video_url,
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Video generation task failed: {e}")
        logger.exception(e)

        # Update job status to FAILED
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                update_job_status(
                    job_uuid,
                    JobStatus.FAILED,
                    error_message=str(e),
                )
            )
        except Exception as update_error:
            logger.error(f"Failed to update job status: {update_error}")

        # Re-raise to trigger Celery retry
        raise


__all__ = ["generate_video_task"]
