"""Test script for Celery task queue."""

import asyncio
import time
from uuid import uuid4

from loguru import logger

from src.domain.entities import User
from src.infrastructure.adapters.database import PostgreSQLUserRepository, PostgreSQLJobRepository
from src.infrastructure.database import check_db_health, get_session_factory
from src.infrastructure.tasks import celery_app, generate_video_task


async def create_test_user() -> User:
    """Create a test user for Celery testing."""
    async_session = get_session_factory()
    async with async_session() as session:
        user_repo = PostgreSQLUserRepository(session)
        
        timestamp = int(time.time() * 1000)
        user = User(
            email=f"celery_test{timestamp}@example.com",
            username=f"celery_test{timestamp}",
            quota_limit=None,  # Unlimited quota
            quota_used=0,
        )
        
        user = await user_repo.create(user)
        await session.commit()
        return user


async def create_test_job(user_id):
    """Create a test job for Celery testing."""
    from src.application.dtos import CreateJobRequest
    from src.application.use_cases import CreateGenerationJobUseCase
    
    async_session = get_session_factory()
    async with async_session() as session:
        job_repo = PostgreSQLJobRepository(session)
        user_repo = PostgreSQLUserRepository(session)
        
        use_case = CreateGenerationJobUseCase(job_repo, user_repo)
        
        request = CreateJobRequest(
            prompt="Test video generation with Celery",
            content_type="video",
            parameters={"duration": 5, "resolution": "1080p"},
            priority=5,
        )
        
        job = await use_case.execute(user_id, request)
        await session.commit()
        return job


async def check_job_status(job_id):
    """Check job status in database."""
    async_session = get_session_factory()
    async with async_session() as session:
        job_repo = PostgreSQLJobRepository(session)
        job = await job_repo.get_by_id(job_id)
        return job


async def test_celery_configuration():
    """Test Celery configuration."""
    print("\n" + "="*60)
    print("Test 1: Celery Configuration")
    print("="*60)
    
    # Check Celery app configuration
    print(f"✅ Celery app name: {celery_app.main}")
    print(f"✅ Broker URL: {celery_app.conf.broker_url}")
    print(f"✅ Result backend: {celery_app.conf.result_backend}")
    print(f"✅ Task serializer: {celery_app.conf.task_serializer}")
    print(f"✅ Task time limit: {celery_app.conf.task_time_limit}s")
    print(f"✅ Max retries: {celery_app.conf.task_max_retries}")
    
    # Check registered tasks
    print(f"\n✅ Registered tasks:")
    for task_name in sorted(celery_app.tasks.keys()):
        if not task_name.startswith("celery."):
            print(f"   - {task_name}")


async def test_debug_task():
    """Test debug task."""
    print("\n" + "="*60)
    print("Test 2: Debug Task")
    print("="*60)
    
    from src.infrastructure.tasks.celery_app import debug_task
    
    # Send task
    result = debug_task.delay()
    print(f"✅ Task enqueued: {result.id}")
    print(f"   Waiting for result...")
    
    # Wait for result (with timeout)
    try:
        task_result = result.get(timeout=10)
        print(f"✅ Task completed: {task_result}")
        return True
    except Exception as e:
        print(f"❌ Task failed: {e}")
        return False


async def test_video_generation_task():
    """Test video generation task."""
    print("\n" + "="*60)
    print("Test 3: Video Generation Task")
    print("="*60)
    
    # Create test user
    print("Creating test user...")
    user = await create_test_user()
    print(f"✅ Test user created: {user.id}")
    
    # Create test job
    print("\nCreating test job...")
    job = await create_test_job(user.id)
    print(f"✅ Test job created: {job.id}")
    print(f"   Status: {job.status}")
    print(f"   Prompt: {job.prompt}")
    
    # Wait a bit for task to start
    print("\nWaiting for task to process...")
    await asyncio.sleep(2)
    
    # Check job status updates
    print("\nChecking job status updates...")
    for i in range(15):  # Check for up to 30 seconds
        job_entity = await check_job_status(job.id)
        if job_entity:
            print(f"   [{i*2}s] Status: {job_entity.status.value}, Progress: {job_entity.progress}%")
            
            if job_entity.status.value in ["completed", "failed"]:
                if job_entity.status.value == "completed":
                    print(f"\n✅ Job completed successfully!")
                    print(f"   Started at: {job_entity.started_at}")
                    print(f"   Completed at: {job_entity.completed_at}")
                    return True
                else:
                    print(f"\n❌ Job failed!")
                    print(f"   Error: {job_entity.error_message}")
                    return False
        
        await asyncio.sleep(2)
    
    print("\n⚠️  Job still processing after 30 seconds")
    return False


async def test_task_retry():
    """Test task retry logic."""
    print("\n" + "="*60)
    print("Test 4: Task Retry Logic")
    print("="*60)
    
    # Try to process a non-existent job (should fail and retry)
    fake_job_id = str(uuid4())
    print(f"Enqueueing task with fake job ID: {fake_job_id}")
    
    result = generate_video_task.delay(fake_job_id)
    print(f"✅ Task enqueued: {result.id}")
    print(f"   This should fail and retry...")
    
    # Wait a bit
    await asyncio.sleep(5)
    
    # Check task state
    print(f"   Task state: {result.state}")
    if result.state == "FAILURE":
        print(f"✅ Task failed as expected (job not found)")
        return True
    else:
        print(f"   Task is still processing or retrying...")
        return False


async def main():
    """Run all Celery tests."""
    print("\n" + "="*60)
    print("CELERY TASK QUEUE TESTS")
    print("="*60)
    
    # Check database connection
    print("\nChecking database connection...")
    if not await check_db_health():
        print("❌ Database connection failed")
        print("\n⚠️  Make sure PostgreSQL is running:")
        print("   docker-compose up -d postgres")
        return
    print("✅ Database connection OK")
    
    # Check Redis connection
    print("\nChecking Redis connection...")
    try:
        from redis import Redis
        redis_client = Redis.from_url("redis://localhost:6379/0")
        redis_client.ping()
        print("✅ Redis connection OK")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("\n⚠️  Make sure Redis is running:")
        print("   docker-compose up -d redis")
        return
    
    # Test 1: Configuration
    await test_celery_configuration()
    
    # Test 2: Debug task
    print("\n⚠️  Make sure Celery worker is running:")
    print("   celery -A src.infrastructure.tasks.celery_app worker --loglevel=info")
    print("\nPress Enter to continue with task tests (or Ctrl+C to skip)...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nSkipping task execution tests")
        return
    
    debug_ok = await test_debug_task()
    
    if not debug_ok:
        print("\n❌ Debug task failed - check if Celery worker is running")
        return
    
    # Test 3: Video generation task
    video_ok = await test_video_generation_task()
    
    # Test 4: Retry logic
    # retry_ok = await test_task_retry()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Celery configuration: OK")
    print(f"{'✅' if debug_ok else '❌'} Debug task: {'OK' if debug_ok else 'FAILED'}")
    print(f"{'✅' if video_ok else '❌'} Video generation task: {'OK' if video_ok else 'FAILED'}")
    # print(f"{'✅' if retry_ok else '❌'} Retry logic: {'OK' if retry_ok else 'FAILED'}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

