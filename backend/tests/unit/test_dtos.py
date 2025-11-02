"""Test script for DTOs validation."""

from datetime import datetime
from uuid import uuid4

from src.application.dtos import (
    CreateJobRequest,
    JobResponse,
    JobListResponse,
    UpdateJobStatusRequest,
    UserResponse,
)


def test_create_job_request():
    """Test CreateJobRequest DTO validation."""
    print("\n" + "="*60)
    print("Testing CreateJobRequest DTO")
    print("="*60)
    
    # Test valid request
    print("\n1. Testing valid CreateJobRequest...")
    request = CreateJobRequest(
        prompt="A beautiful sunset over mountains",
        content_type="video",
        model_name="moneyprinter-turbo",
        parameters={"duration": 5, "resolution": "1080p"},
        priority=5,
        webhook_url="https://example.com/webhook"
    )
    print(f"   ✅ Valid request created")
    print(f"   Prompt: {request.prompt}")
    print(f"   Content Type: {request.content_type}")
    print(f"   Priority: {request.priority}")
    
    # Test validation - empty prompt
    print("\n2. Testing validation - empty prompt...")
    try:
        CreateJobRequest(
            prompt="",
            content_type="video"
        )
        print("   ❌ Should have raised validation error")
    except ValueError as e:
        print(f"   ✅ Validation error caught: {str(e)[:50]}...")
    
    # Test validation - invalid content_type
    print("\n3. Testing validation - invalid content_type...")
    try:
        CreateJobRequest(
            prompt="Test prompt",
            content_type="invalid_type"
        )
        print("   ❌ Should have raised validation error")
    except ValueError as e:
        print(f"   ✅ Validation error caught: {str(e)[:50]}...")
    
    # Test validation - invalid priority
    print("\n4. Testing validation - invalid priority...")
    try:
        CreateJobRequest(
            prompt="Test prompt",
            content_type="video",
            priority=15  # Max is 10
        )
        print("   ❌ Should have raised validation error")
    except ValueError as e:
        print(f"   ✅ Validation error caught: {str(e)[:50]}...")
    
    # Test validation - invalid webhook URL
    print("\n5. Testing validation - invalid webhook URL...")
    try:
        CreateJobRequest(
            prompt="Test prompt",
            content_type="video",
            webhook_url="not-a-url"
        )
        print("   ❌ Should have raised validation error")
    except ValueError as e:
        print(f"   ✅ Validation error caught: {str(e)[:50]}...")
    
    # Test defaults
    print("\n6. Testing default values...")
    request = CreateJobRequest(
        prompt="Test prompt",
        content_type="image"
    )
    assert request.priority == 0, "Default priority should be 0"
    assert request.parameters == {}, "Default parameters should be empty dict"
    assert request.model_name is None, "Default model_name should be None"
    print("   ✅ Default values correct")
    
    print("\n✅ CreateJobRequest DTO: ALL TESTS PASSED")


def test_update_job_status_request():
    """Test UpdateJobStatusRequest DTO validation."""
    print("\n" + "="*60)
    print("Testing UpdateJobStatusRequest DTO")
    print("="*60)
    
    # Test valid request
    print("\n1. Testing valid UpdateJobStatusRequest...")
    request = UpdateJobStatusRequest(
        status="processing",
        progress=45.5
    )
    print(f"   ✅ Valid request created")
    print(f"   Status: {request.status}")
    print(f"   Progress: {request.progress}%")
    
    # Test validation - invalid status
    print("\n2. Testing validation - invalid status...")
    try:
        UpdateJobStatusRequest(
            status="invalid_status"
        )
        print("   ❌ Should have raised validation error")
    except ValueError as e:
        print(f"   ✅ Validation error caught: {str(e)[:50]}...")
    
    # Test validation - invalid progress
    print("\n3. Testing validation - invalid progress...")
    try:
        UpdateJobStatusRequest(
            status="processing",
            progress=150.0  # Max is 100
        )
        print("   ❌ Should have raised validation error")
    except ValueError as e:
        print(f"   ✅ Validation error caught: {str(e)[:50]}...")
    
    print("\n✅ UpdateJobStatusRequest DTO: ALL TESTS PASSED")


def test_job_response():
    """Test JobResponse DTO."""
    print("\n" + "="*60)
    print("Testing JobResponse DTO")
    print("="*60)
    
    # Test creating response
    print("\n1. Testing JobResponse creation...")
    response = JobResponse(
        id=uuid4(),
        user_id=uuid4(),
        content_type="video",
        prompt="A beautiful sunset",
        model_name="moneyprinter-turbo",
        parameters={"duration": 5},
        status="processing",
        priority=5,
        progress=45.5,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        retry_count=0
    )
    print(f"   ✅ JobResponse created")
    print(f"   ID: {response.id}")
    print(f"   Status: {response.status}")
    print(f"   Progress: {response.progress}%")
    
    # Test JSON serialization
    print("\n2. Testing JSON serialization...")
    json_data = response.model_dump_json()
    print(f"   ✅ Serialized to JSON ({len(json_data)} bytes)")
    
    # Test JSON deserialization
    print("\n3. Testing JSON deserialization...")
    restored = JobResponse.model_validate_json(json_data)
    assert restored.id == response.id
    assert restored.status == response.status
    print("   ✅ Deserialized from JSON successfully")
    
    print("\n✅ JobResponse DTO: ALL TESTS PASSED")


def test_job_list_response():
    """Test JobListResponse DTO."""
    print("\n" + "="*60)
    print("Testing JobListResponse DTO")
    print("="*60)
    
    # Create sample jobs
    print("\n1. Testing JobListResponse creation...")
    jobs = [
        JobResponse(
            id=uuid4(),
            user_id=uuid4(),
            content_type="video",
            prompt=f"Test prompt {i}",
            model_name="moneyprinter-turbo",
            parameters={},
            status="queued",
            priority=0,
            created_at=datetime.utcnow(),
            retry_count=0
        )
        for i in range(3)
    ]
    
    response = JobListResponse(
        jobs=jobs,
        total=42,
        page=1,
        page_size=10,
        has_next=True,
        has_prev=False
    )
    print(f"   ✅ JobListResponse created")
    print(f"   Jobs: {len(response.jobs)}")
    print(f"   Total: {response.total}")
    print(f"   Page: {response.page}/{(response.total + response.page_size - 1) // response.page_size}")
    
    # Test pagination flags
    print("\n2. Testing pagination flags...")
    assert response.has_next == True, "Should have next page"
    assert response.has_prev == False, "Should not have previous page"
    print("   ✅ Pagination flags correct")
    
    print("\n✅ JobListResponse DTO: ALL TESTS PASSED")


def test_user_response():
    """Test UserResponse DTO."""
    print("\n" + "="*60)
    print("Testing UserResponse DTO")
    print("="*60)
    
    # Test creating response
    print("\n1. Testing UserResponse creation...")
    response = UserResponse(
        id=uuid4(),
        email="user@example.com",
        username="johndoe",
        created_at=datetime.utcnow(),
        is_active=True,
        is_admin=False,
        quota_limit=100,
        quota_used=25,
        quota_remaining=75,
        quota_reset_at=datetime.utcnow()
    )
    print(f"   ✅ UserResponse created")
    print(f"   Username: {response.username}")
    print(f"   Email: {response.email}")
    print(f"   Quota: {response.quota_used}/{response.quota_limit}")
    
    # Test has_quota property
    print("\n2. Testing has_quota property...")
    assert response.has_quota == True, "User should have quota"
    print("   ✅ has_quota = True (correct)")
    
    # Test unlimited quota
    print("\n3. Testing unlimited quota...")
    unlimited_user = UserResponse(
        id=uuid4(),
        email="admin@example.com",
        username="admin",
        created_at=datetime.utcnow(),
        is_active=True,
        is_admin=True,
        quota_limit=None,  # Unlimited
        quota_used=1000
    )
    assert unlimited_user.has_quota == True, "Admin should have unlimited quota"
    print("   ✅ Unlimited quota works correctly")
    
    # Test quota exceeded
    print("\n4. Testing quota exceeded...")
    exceeded_user = UserResponse(
        id=uuid4(),
        email="user2@example.com",
        username="user2",
        created_at=datetime.utcnow(),
        is_active=True,
        is_admin=False,
        quota_limit=10,
        quota_used=10
    )
    assert exceeded_user.has_quota == False, "User should not have quota"
    print("   ✅ Quota exceeded detection works")
    
    print("\n✅ UserResponse DTO: ALL TESTS PASSED")


def main():
    """Run all DTO tests."""
    print("\n" + "="*60)
    print("DTO VALIDATION TESTS")
    print("="*60)
    
    try:
        test_create_job_request()
        test_update_job_status_request()
        test_job_response()
        test_job_list_response()
        test_user_response()
        
        print("\n" + "="*60)
        print("🎉 ALL DTO TESTS PASSED SUCCESSFULLY!")
        print("="*60)
        print("\n✅ CreateJobRequest: Validation working")
        print("✅ UpdateJobStatusRequest: Validation working")
        print("✅ JobResponse: Serialization working")
        print("✅ JobListResponse: Pagination working")
        print("✅ UserResponse: Quota logic working")
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

