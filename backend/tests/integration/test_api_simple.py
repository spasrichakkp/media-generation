"""Simple API integration tests using async client."""

import asyncio
from uuid import uuid4

import httpx
from httpx import ASGITransport

from src.api.main import app
from src.domain.entities import User
from src.infrastructure.adapters.database import PostgreSQLUserRepository
from src.infrastructure.database import check_db_health, get_session_factory


async def setup_test_user() -> User:
    """Create a test user for API testing."""
    async_session = get_session_factory()
    async with async_session() as session:
        user_repo = PostgreSQLUserRepository(session)
        
        import time
        timestamp = int(time.time() * 1000)
        user = User(
            email=f"api_test{timestamp}@example.com",
            username=f"api_test{timestamp}",
            quota_limit=None,  # Unlimited quota
            quota_used=0,
        )
        
        user = await user_repo.create(user)
        await session.commit()
        return user


async def main():
    """Run API tests."""
    print("\n" + "="*60)
    print("API INTEGRATION TESTS (Async)")
    print("="*60)
    
    # Check database connection
    print("\nChecking database connection...")
    if not await check_db_health():
        print("❌ Database connection failed")
        return
    print("✅ Database connection OK")
    
    # Create async HTTP client
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        
        # Test 1: Root endpoint
        print("\n" + "="*60)
        print("Test 1: Root Endpoint")
        print("="*60)
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Root endpoint: {data['message']}")
        
        # Test 2: Health check
        print("\n" + "="*60)
        print("Test 2: Health Check")
        print("="*60)
        response = await client.get("/health")
        data = response.json()
        print(f"✅ Health check: {data['status']}")
        print(f"   Components: {data['components']}")
        
        # Test 3: Create job without auth
        print("\n" + "="*60)
        print("Test 3: Create Job Without Auth")
        print("="*60)
        response = await client.post(
            "/api/v1/jobs",
            json={"prompt": "test", "content_type": "video"}
        )
        assert response.status_code == 401
        print(f"✅ Authentication required (401)")
        
        # Test 4: Create job with invalid API key
        print("\n" + "="*60)
        print("Test 4: Create Job With Invalid API Key")
        print("="*60)
        response = await client.post(
            "/api/v1/jobs",
            headers={"X-API-Key": "invalid"},
            json={"prompt": "test", "content_type": "video"}
        )
        assert response.status_code == 401
        print(f"✅ Invalid API key rejected (401)")
        
        # Create test user
        user = await setup_test_user()
        print(f"\n✅ Test user created: {user.id}")
        
        # Test 5: Create job with valid auth
        print("\n" + "="*60)
        print("Test 5: Create Job With Valid Auth")
        print("="*60)
        response = await client.post(
            "/api/v1/jobs",
            headers={"X-API-Key": str(user.id)},
            json={
                "prompt": "A beautiful sunset over mountains",
                "content_type": "video",
                "parameters": {"duration": 5},
                "priority": 5,
            }
        )
        assert response.status_code == 201
        job_data = response.json()
        job_id = job_data["id"]
        print(f"✅ Job created (201)")
        print(f"   Job ID: {job_id}")
        print(f"   Status: {job_data['status']}")
        
        # Test 6: Get job status
        print("\n" + "="*60)
        print("Test 6: Get Job Status")
        print("="*60)

        # Small delay to ensure database commit is complete
        await asyncio.sleep(0.1)

        response = await client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"X-API-Key": str(user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Job status retrieved (200)")
        print(f"   Status: {data['status']}")
        
        # Test 7: Get non-existent job
        print("\n" + "="*60)
        print("Test 7: Get Non-Existent Job")
        print("="*60)
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/jobs/{fake_id}",
            headers={"X-API-Key": str(user.id)},
        )
        assert response.status_code == 404
        data = response.json()
        print(f"✅ Job not found (404)")
        print(f"   Error: {data['error']['message']}")
        
        # Test 8: List jobs
        print("\n" + "="*60)
        print("Test 8: List Jobs")
        print("="*60)
        
        # Create a few more jobs
        for i in range(2):
            await client.post(
                "/api/v1/jobs",
                headers={"X-API-Key": str(user.id)},
                json={"prompt": f"Test {i}", "content_type": "image"}
            )
        
        response = await client.get(
            "/api/v1/jobs",
            headers={"X-API-Key": str(user.id)},
            params={"page": 1, "page_size": 10},
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Jobs listed (200)")
        print(f"   Total: {data['total']}")
        print(f"   Jobs in page: {len(data['jobs'])}")
        
        # Test 9: Cancel job
        print("\n" + "="*60)
        print("Test 9: Cancel Job")
        print("="*60)
        response = await client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            headers={"X-API-Key": str(user.id)},
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Job cancelled (200)")
        print(f"   Status: {data['status']}")
        
        # Test 10: Cancel already cancelled job
        print("\n" + "="*60)
        print("Test 10: Cancel Already Cancelled Job")
        print("="*60)
        response = await client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            headers={"X-API-Key": str(user.id)},
        )
        assert response.status_code == 400
        data = response.json()
        print(f"✅ Cannot cancel already cancelled job (400)")
        print(f"   Error: {data['error']['message']}")
        
        # Test 11: Invalid pagination
        print("\n" + "="*60)
        print("Test 11: Invalid Pagination")
        print("="*60)
        response = await client.get(
            "/api/v1/jobs",
            headers={"X-API-Key": str(user.id)},
            params={"page": 0, "page_size": 10},
        )
        assert response.status_code == 422
        print(f"✅ Invalid pagination rejected (422)")
        
        # Test 12: Validation error
        print("\n" + "="*60)
        print("Test 12: Validation Error")
        print("="*60)
        response = await client.post(
            "/api/v1/jobs",
            headers={"X-API-Key": str(user.id)},
            json={"prompt": "test", "content_type": "invalid_type"}
        )
        assert response.status_code == 422
        data = response.json()
        print(f"✅ Validation error (422)")
        print(f"   Error: {data['error']['message']}")
        
    print("\n" + "="*60)
    print("🎉 ALL API TESTS PASSED!")
    print("="*60)
    print("\n✅ Root endpoint: Working")
    print("✅ Health check: Working")
    print("✅ Authentication: Working")
    print("✅ Create job: Working")
    print("✅ Get job status: Working")
    print("✅ List jobs: Working")
    print("✅ Cancel job: Working")
    print("✅ Error handling: Working")
    print("✅ Validation: Working")
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(main())

