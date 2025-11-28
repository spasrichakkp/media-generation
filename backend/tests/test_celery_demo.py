#!/usr/bin/env python3
"""
Simple test to verify Celery worker functionality for video generation.
This script tests the connection to the running Celery worker.
"""

import asyncio
import sys
from uuid import uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.domain.entities import GenerationJob, User
from src.domain.value_objects import ContentType, JobStatus, ModelType
from src.infrastructure.adapters.database import (
    PostgreSQLJobRepository,
    PostgreSQLUserRepository,
)
from src.infrastructure.database import get_session_factory
from src.infrastructure.tasks.video_generation import generate_video_task


async def create_test_job():
    """Create a test job in the database and send it to Celery."""
    print("=" * 70)
    print("CELERY VIDEO GENERATION TEST")
    print("=" * 70)
    
    # Get settings and session factory
    settings = get_settings()
    session_factory = get_session_factory()
    
    print(f"Database URL: {settings.database_url}")
    print(f"Redis URL: {settings.redis_url}")
    print(f"Celery Broker: {settings.celery_broker_url}")
    print()
    
    # Create a test user
    print("Step 1: Creating test user...")
    user_id = uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        quota_limit=None,
        quota_used=0,
    )
    
    async with session_factory() as session:
        user_repo = PostgreSQLUserRepository(session)
        await user_repo.create(user)
        await session.commit()
    
    print(f"✅ User created: {user_id}")
    
    # Create a video generation job
    print("\nStep 2: Creating video generation job...")
    job_id = uuid4()
    
    job = GenerationJob(
        id=job_id,
        user_id=user.id,
        prompt="A beautiful sunset over mountains",
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
    
    print(f"✅ Job created: {job_id}")
    print(f"   Prompt: {job.prompt}")
    print(f"   Parameters: {job.parameters}")
    
    # Save job to database
    async with session_factory() as session:
        repo = PostgreSQLJobRepository(session)
        await repo.create(job)
        await session.commit()
    
    print("\nStep 3: Sending task to Celery worker...")
    
    # Send task to Celery worker
    result = generate_video_task.delay(str(job_id))
    
    print(f"✅ Task sent to Celery!")
    print(f"   Celery Task ID: {result.id}")
    print(f"   Job ID: {job_id}")
    print()
    print("Check the Celery worker logs for processing details.")
    print("The task should be picked up by the worker running in Docker.")
    print()
    print("Example command to check Celery worker logs:")
    print("  docker-compose logs celery_worker")
    print()
    
    return job_id, result.id


async def main():
    """Run the test."""
    try:
        job_id, celery_task_id = await create_test_job()
        
        print("To monitor job progress, you can check the database:")
        print(f"  SELECT * FROM jobs WHERE id = '{job_id}' LIMIT 1;")
        print()
        
        print("To see detailed logs of the Celery worker processing:")
        print("  docker-compose logs celery_worker -f")
        print()
        
        print("SUCCESS: Celery task was successfully sent to the worker!")
        print("The Celery worker running in Docker should now process this task.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)