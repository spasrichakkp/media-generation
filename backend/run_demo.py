#!/usr/bin/env python3
"""
Video Generation Demo - Test Celery Worker
Creates a user, job, and sends it to the Celery worker for processing.
"""

import asyncio
import sys
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
    """Run the video generation demo."""
    
    logger.info("=" * 70)
    logger.info("VIDEO GENERATION DEMO - Celery Worker Test")
    logger.info("=" * 70)
    logger.info("")
    
    # Get session factory
    session_factory = get_session_factory()
    
    # Step 1: Create test user
    user_id = uuid4()
    logger.info(f"Step 1: Creating test user")
    logger.info(f"  User ID: {user_id}")
    logger.info(f"  Email: demo@example.com")
    
    user = User(
        id=user_id,
        email="demo@example.com",
        username="demouser",
        quota_limit=None,
        quota_used=0,
    )
    
    async with session_factory() as session:
        user_repo = PostgreSQLUserRepository(session)
        await user_repo.create(user)
        await session.commit()
    
    logger.success("✅ User created")
    logger.info("")
    
    # Step 2: Create video generation job
    job_id = uuid4()
    logger.info(f"Step 2: Creating video generation job")
    logger.info(f"  Job ID: {job_id}")
    logger.info(f"  Prompt: Create a 10-second video about ocean waves")
    
    job = GenerationJob(
        id=job_id,
        user_id=user.id,
        prompt="Create a 10-second video about the beauty of ocean waves",
        content_type=ContentType.VIDEO,
        model_name=ModelType.MONEYPRINTER_TURBO,
        parameters={"duration": 10, "style": "cinematic"},
        status=JobStatus.PENDING,
        progress=0,
    )
    
    async with session_factory() as session:
        job_repo = PostgreSQLJobRepository(session)
        await job_repo.create(job)
        await session.commit()
    
    logger.success("✅ Job created")
    logger.info("")
    
    # Step 3: Send to Celery worker
    logger.info("Step 3: Sending task to Celery worker")
    result = generate_video_task.delay(str(job_id))
    logger.success(f"✅ Task sent! Celery Task ID: {result.id}")
    logger.info("")
    
    # Step 4: Monitor progress
    logger.info("=" * 70)
    logger.info("Step 4: MONITORING PROGRESS")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Polling every 5 seconds... (Watch Celery worker for details)")
    logger.info("")
    
    max_polls = 60
    poll_count = 0
    last_progress = -1
    
    while poll_count < max_polls:
        poll_count += 1
        await asyncio.sleep(5)
        
        async with session_factory() as session:
            job_repo = PostgreSQLJobRepository(session)
            updated_job = await job_repo.get_by_id(job.id)
        
        if not updated_job:
            logger.error("❌ Job not found!")
            return False
        
        status = updated_job.status.value
        progress = updated_job.progress
        
        if progress != last_progress:
            logger.info(f"[Poll {poll_count:2d}] Status: {status:12s} | Progress: {progress:3d}%")
            last_progress = progress
        
        if status == "completed":
            logger.info("")
            logger.info("=" * 70)
            logger.success("🎉 VIDEO GENERATION COMPLETED!")
            logger.info("=" * 70)
            logger.info("")
            logger.info(f"Result URL: {updated_job.result_url}")
            logger.info(f"Total time: ~{poll_count * 5} seconds")
            logger.info("")
            logger.info("Access video at:")
            logger.info(f"  {updated_job.result_url}")
            logger.info("")
            logger.info("Or via MinIO console:")
            logger.info("  http://localhost:9001")
            logger.info("  Username: minioadmin")
            logger.info("  Password: minioadmin")
            logger.info("")
            return True
            
        elif status == "failed":
            logger.info("")
            logger.error("❌ VIDEO GENERATION FAILED!")
            logger.error(f"Error: {updated_job.error_message}")
            logger.info("")
            return False
            
        elif status == "cancelled":
            logger.warning("⚠️  Job cancelled")
            return False
    
    logger.warning("⚠️  Timeout (5 minutes)")
    logger.info(f"Last status: {status} ({progress}%)")
    return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        logger.exception(e)
        sys.exit(1)

