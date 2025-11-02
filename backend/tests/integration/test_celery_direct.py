#!/usr/bin/env python3
"""Test script to directly call Celery video generation task."""

import asyncio
import time
from uuid import uuid4

from src.config import get_settings
from src.domain.entities import GenerationJob, JobStatus, User
from src.domain.value_objects import ContentType, ModelType
from src.infrastructure.adapters.database import PostgreSQLGenerationJobRepository
from src.infrastructure.database import get_session_factory
from src.infrastructure.tasks.video_generation import generate_video_task


async def test_celery_task():
    """Test Celery task directly."""
    
    print("=" * 60)
    print("Testing Celery Video Generation Task (Direct Call)")
    print("=" * 60)
    print()
    
    # Get settings
    settings = get_settings()
    
    # Create a test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        quota_limit=None,  # Unlimited
        quota_used=0,
    )
    
    # Create a test job
    job = GenerationJob(
        id=uuid4(),
        user_id=user.id,
        prompt="Create a 10-second video about the beauty of ocean waves",
        content_type=ContentType.VIDEO,
        model_name=ModelType.MOVIEPY_GENERATOR,
        parameters={
            "duration": 10,
            "style": "cinematic",
            "tone": "peaceful"
        },
        status=JobStatus.PENDING,
        progress=0,
    )
    
    print(f"Job ID: {job.id}")
    print(f"Prompt: {job.prompt}")
    print(f"Parameters: {job.parameters}")
    print()
    
    # Save job to database
    print("Saving job to database...")
    session_factory = get_session_factory(settings)
    async with session_factory() as session:
        repo = PostgreSQLGenerationJobRepository(session)
        await repo.create(job)
        await session.commit()
    print("✅ Job saved to database")
    print()
    
    # Send task to Celery worker
    print("Sending task to Celery worker...")
    result = generate_video_task.delay(str(job.id))
    print(f"✅ Task sent! Task ID: {result.id}")
    print()
    
    # Poll task status
    print("Polling task status (will check every 5 seconds)...")
    print("=" * 60)
    
    max_polls = 60  # 5 minutes max
    poll_count = 0
    
    while poll_count < max_polls:
        poll_count += 1
        
        # Wait before polling
        time.sleep(5)
        
        # Check task status
        task_status = result.status
        
        # Get job from database
        async with session_factory() as session:
            repo = PostgreSQLGenerationJobRepository(session)
            updated_job = await repo.get_by_id(job.id)
        
        if updated_job:
            status = updated_job.status.value
            progress = updated_job.progress
            
            print(f"[Poll {poll_count}] Task: {task_status:12s} | Job: {status:12s} | Progress: {progress:3d}%", end="")
            
            if status == "completed":
                print(" ✅")
                print()
                print("=" * 60)
                print("🎉 Video generation completed successfully!")
                print("=" * 60)
                print(f"\nResult URL: {updated_job.result_url}")
                print(f"Total time: ~{poll_count * 5} seconds")
                print()
                break
                
            elif status == "failed":
                print(" ❌")
                print()
                print("=" * 60)
                print("❌ Video generation failed!")
                print("=" * 60)
                print(f"\nError: {updated_job.error_message}")
                print()
                break
                
            elif status == "cancelled":
                print(" ⚠️")
                print()
                print("Job was cancelled")
                break
                
            else:
                # Still processing
                print()
        else:
            print(f"[Poll {poll_count}] ⚠️ Job not found in database")
            break
            
    else:
        print()
        print("⚠️ Polling timeout reached (5 minutes)")
        if updated_job:
            print(f"Last known status: {updated_job.status.value} ({updated_job.progress}%)")


if __name__ == "__main__":
    asyncio.run(test_celery_task())

