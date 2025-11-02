"""Test repository implementations."""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.entities import GenerationJob, User
from src.domain.value_objects import ContentType, JobStatus
from src.infrastructure.adapters.database import (
    PostgreSQLJobRepository,
    PostgreSQLUserRepository,
)
from src.infrastructure.database import get_session_factory


async def test_user_repository():
    """Test user repository operations."""
    print("\n" + "="*60)
    print("Testing User Repository")
    print("="*60)
    
    async_session = get_session_factory()
    
    async with async_session() as session:
        repo = PostgreSQLUserRepository(session)
        
        # Create a test user
        user = User(
            email=f"test_{uuid4().hex[:8]}@example.com",
            username=f"testuser_{uuid4().hex[:8]}",
            api_key_hash="hashed_api_key_123",
            is_active=True,
        )
        
        print(f"\n1. Creating user: {user.email}")
        created_user = await repo.create(user)
        print(f"   ✅ User created with ID: {created_user.id}")
        
        # Get by ID
        print(f"\n2. Fetching user by ID: {created_user.id}")
        fetched_user = await repo.get_by_id(created_user.id)
        assert fetched_user is not None
        assert fetched_user.email == user.email
        print(f"   ✅ User fetched: {fetched_user.email}")
        
        # Get by email
        print(f"\n3. Fetching user by email: {user.email}")
        user_by_email = await repo.get_by_email(user.email)
        assert user_by_email is not None
        assert user_by_email.id == created_user.id
        print(f"   ✅ User found by email")
        
        # Update user
        print(f"\n4. Updating user quota")
        fetched_user.quota_used = 5
        updated_user = await repo.update(fetched_user)
        assert updated_user.quota_used == 5
        print(f"   ✅ User quota updated: {updated_user.quota_used}")
        
        # List users
        print(f"\n5. Listing users")
        users = await repo.get_all(limit=10)
        assert len(users) > 0
        print(f"   ✅ Found {len(users)} users")
        
        print(f"\n✅ User Repository: ALL TESTS PASSED")
        
        await session.commit()


async def test_job_repository():
    """Test job repository operations."""
    print("\n" + "="*60)
    print("Testing Job Repository")
    print("="*60)
    
    async_session = get_session_factory()
    
    async with async_session() as session:
        # First create a user
        user_repo = PostgreSQLUserRepository(session)
        user = User(
            email=f"jobtest_{uuid4().hex[:8]}@example.com",
            username=f"jobuser_{uuid4().hex[:8]}",
            api_key_hash="hashed_api_key_123",
            is_active=True,
        )
        user = await user_repo.create(user)
        print(f"\n0. Created test user: {user.email}")
        
        # Create a test job
        job_repo = PostgreSQLJobRepository(session)
        job = GenerationJob(
            user_id=user.id,
            content_type=ContentType.IMAGE,
            prompt="A beautiful sunset over mountains",
            model_name="hunyuan-image-3.0",
        )
        
        print(f"\n1. Creating job: {job.prompt[:50]}...")
        created_job = await job_repo.create(job)
        print(f"   ✅ Job created with ID: {created_job.id}")
        print(f"   Status: {created_job.status.value}")
        
        # Get by ID
        print(f"\n2. Fetching job by ID: {created_job.id}")
        fetched_job = await job_repo.get_by_id(created_job.id)
        assert fetched_job is not None
        assert fetched_job.prompt == job.prompt
        print(f"   ✅ Job fetched: {fetched_job.status.value}")
        
        # Update job status
        print(f"\n3. Updating job status to PROCESSING")
        fetched_job._transition_to(JobStatus.PROCESSING)
        updated_job = await job_repo.update(fetched_job)
        assert updated_job.status == JobStatus.PROCESSING
        print(f"   ✅ Job status updated: {updated_job.status.value}")

        # Get by user ID
        print(f"\n4. Fetching jobs for user: {user.id}")
        user_jobs = await job_repo.get_by_user_id(user.id, limit=10)
        assert len(user_jobs) > 0
        print(f"   ✅ Found {len(user_jobs)} jobs for user")

        # Get by status
        print(f"\n5. Fetching PROCESSING jobs")
        processing_jobs = await job_repo.get_by_status(JobStatus.PROCESSING, limit=10)
        assert len(processing_jobs) > 0
        print(f"   ✅ Found {len(processing_jobs)} PROCESSING jobs")
        
        print(f"\n✅ Job Repository: ALL TESTS PASSED")
        
        await session.commit()


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("REPOSITORY INTEGRATION TESTS")
    print("="*60)
    
    try:
        await test_user_repository()
        await test_job_repository()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
        print("="*60)
        print("\n✅ Database connection: Working")
        print("✅ User repository: Working")
        print("✅ Job repository: Working")
        print("✅ ORM models: Working")
        print("✅ Migrations: Applied successfully")
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())

