#!/usr/bin/env python3
"""
Demo script to test video generation via Celery worker.
This script creates a user and job in the database and sends it to the Celery worker.
"""

import asyncio
import sys
import time
from uuid import uuid4

from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}")

from src.config import get_settings
from src.domain.entities import GenerationJob, User
from src.domain.value_objects import ContentType, JobStatus, ModelType
from src.infrastructure.adapters.database import (
    PostgreSQLJobRepository,
    PostgreSQLUserRepository,
)
from src.infrastructure.database import get_session_factory
from src.infrastructure.tasks.video_generation import generate_video_task


async def main():
    """Run the demo."""

    logger.info("=" * 70)
    logger.info("VIDEO GENERATION DEMO - Celery Worker Test")
    logger.info("=" * 70)
    logger.info("")

    # Get settings and session factory
    settings = get_settings()
    session_factory = get_session_factory()  # Will create engine automatically

    # Create a test user
    user_id = uuid4()
    logger.info(f"Step 1: Creating test user")
    logger.info(f"  User ID: {user_id}")
    logger.info(f"  Email: demo@example.com")

    user = User(
        id=user_id,
        email="demo@example.com",
        username="demouser",
        quota_limit=None,  # Unlimited quota
        quota_used=0,
    )

    # Save user to database
    async with session_factory() as session:
        user_repo = PostgreSQLUserRepository(session)
        await user_repo.create(user)
        await session.commit()

    logger.success("✅ User created and saved to database")
    logger.info("")
    
    # Create a video generation job
    job_id = uuid4()
    logger.info(f"Step 2: Creating video generation job")
    logger.info(f"  Job ID: {job_id}")

    job = GenerationJob(
        id=job_id,
        user_id=user.id,
        prompt="Create a 10-second video about the beauty of ocean waves",
        content_type=ContentType.VIDEO,
        model_name=ModelType.MONEYPRINTER_TURBO,
        parameters={
            "duration": 10,
            "style": "cinematic",
            "tone": "peaceful"
        },
        status=JobStatus.PENDING,
        progress=0,
    )

    logger.info(f"  Prompt: {job.prompt}")
    logger.info(f"  Content Type: {job.content_type.value}")
    logger.info(f"  Model: {job.model_name.value}")
    logger.info(f"  Parameters: {job.parameters}")
    logger.info("")

    # Save job to database
    async with session_factory() as session:
        repo = PostgreSQLJobRepository(session)
        await repo.create(job)
        await session.commit()

    logger.success("✅ Job saved to database")
    logger.info("")
    
    # Send task to Celery worker
    logger.info("Step 3: Sending task to Celery worker")
    logger.info(f"  Task: generate_video_task")
    logger.info(f"  Queue: video_generation")
    logger.info(f"  Job ID: {job_id}")
    logger.info("")

    result = generate_video_task.delay(str(job_id))

    logger.success(f"✅ Task sent to Celery!")
    logger.info(f"  Celery Task ID: {result.id}")
    logger.info("")
    logger.info("=" * 70)
    logger.info("Step 4: MONITORING JOB PROGRESS")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Polling job status every 5 seconds...")
    logger.info("(Watch the Celery worker terminal for detailed execution logs)")
    logger.info("")
    
    # Poll job status
    max_polls = 60  # 5 minutes max
    poll_count = 0
    last_progress = -1
    
    while poll_count < max_polls:
        poll_count += 1
        
        # Wait before polling
        await asyncio.sleep(5)
        
        # Get job from database
        async with session_factory() as session:
            repo = PostgreSQLJobRepository(session)
            updated_job = await repo.get_by_id(job.id)
        
        if not updated_job:
            logger.error("❌ Job not found in database!")
            break
        
        status = updated_job.status.value
        progress = updated_job.progress
        
        # Only log if progress changed
        if progress != last_progress:
            logger.info(f"[Poll {poll_count:2d}] Status: {status:12s} | Progress: {progress:3d}%")
            last_progress = progress
        
        # Check if job is complete
        if status == "completed":
            logger.info("")
            logger.info("=" * 70)
            logger.success("🎉 VIDEO GENERATION COMPLETED SUCCESSFULLY!")
            logger.info("=" * 70)
            logger.info("")
            logger.info(f"Result URL: {updated_job.result_url}")
            logger.info(f"Total time: ~{poll_count * 5} seconds")
            logger.info("")
            logger.info("You can download the video from:")
            logger.info(f"  {updated_job.result_url}")
            logger.info("")
            logger.info("Or access it via MinIO console:")
            logger.info("  http://localhost:9001")
            logger.info("  Username: minioadmin")
            logger.info("  Password: minioadmin")
            logger.info("")
            return True
            
        elif status == "failed":
            logger.info("")
            logger.info("=" * 70)
            logger.error("❌ VIDEO GENERATION FAILED!")
            logger.info("=" * 70)
            logger.info("")
            logger.error(f"Error: {updated_job.error_message}")
            logger.info("")
            return False
            
        elif status == "cancelled":
            logger.info("")
            logger.warning("⚠️  Job was cancelled")
            return False
    
    # Timeout
    logger.info("")
    logger.warning("⚠️  Polling timeout reached (5 minutes)")
    logger.info(f"Last known status: {status} ({progress}%)")
    logger.info("")
    logger.info("The job may still be processing. Check the Celery worker logs.")
    return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("")
        logger.warning("⚠️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("")
        logger.error(f"❌ Unexpected error: {e}")
        logger.exception(e)
        sys.exit(1)

