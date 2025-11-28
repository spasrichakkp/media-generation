#!/usr/bin/env python3
"""
Test script for video generation functionality using urllib (no external dependencies).
"""

import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

def wait_for_api(api_url, timeout=300):
    print(f"Waiting for API at {api_url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(f"{api_url}/health") as response:
                if response.status == 200:
                    print("✅ API is ready!")
                    return True
        except Exception:
            time.sleep(2)
    print("❌ API failed to start within timeout.")
    return False

def test_video_generation():
    api_url = "http://0.0.0.0:8000"
    
    if not wait_for_api(api_url):
        return False

    print("Testing video generation...")
    api_key = "123e4567-e89b-12d3-a456-426614174000"
    
    # Step 1: Create a video generation job
    job_data = {
        "content_type": "video",
        "prompt": "A beautiful sunset over mountains with a serene lake in the foreground.",
        "model_name": "moneyprinter-turbo",
        "parameters": {
            "duration": 5,
            "style": "cinematic"
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    print("Step 1: Creating video generation job...")
    try:
        req = urllib.request.Request(
            f"{api_url}/api/v1/jobs",
            data=json.dumps(job_data).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                job_id = result.get("id")
                print(f"✅ Job created successfully: {job_id}")
            else:
                print(f"❌ Failed to create job. Status: {response.status}")
                return False
    except urllib.error.URLError as e:
        print(f"❌ Error creating job: {e}")
        if hasattr(e, 'read'):
            print(f"   Response: {e.read().decode('utf-8')}")
        return False

    # Step 2: Monitor job progress
    print("\nStep 2: Monitoring job progress...")
    max_attempts = 60
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        time.sleep(5)
        
        try:
            req = urllib.request.Request(
                f"{api_url}/api/v1/jobs/{job_id}",
                headers=headers,
                method="GET"
            )
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    job_status = json.loads(response.read().decode('utf-8'))
                    status = job_status.get("status")
                    progress = job_status.get("progress", 0)
                    
                    print(f"  Attempt {attempt}: Status={status}, Progress={progress}%")
                    
                    if status == "completed":
                        print(f"✅ Video generation completed!")
                        print(f"   Result URL: {job_status.get('result_url')}")
                        return True
                    elif status == "failed":
                        print(f"❌ Video generation failed!")
                        print(f"   Error: {job_status.get('error_message')}")
                        return False
                    elif status == "cancelled":
                        print(f"❌ Job was cancelled")
                        return False
        except Exception as e:
            print(f"❌ Error monitoring job: {e}")
            return False
    
    print(f"⏰ Job monitoring timed out")
    return False

if __name__ == "__main__":
    success = test_video_generation()
    sys.exit(0 if success else 1)
