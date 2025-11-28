#!/usr/bin/env python3
"""
Test script for video generation functionality.
This script tests the video generation capabilities with the updated Pillow-based text rendering.
"""

import asyncio
import json
import uuid
import sys
import time
from datetime import datetime

import aiohttp
from loguru import logger


async def test_video_generation():
    """Test video generation functionality."""
    logger.info("Testing video generation with new Pillow-based text rendering...")
    
    api_url = "http://localhost:8000"
    api_key = "123e4567-e89b-12d3-a456-426614174000"  # Default from environment
    
    # Step 1: Create a video generation job
    job_data = {
        "content_type": "video",
        "prompt": "A beautiful sunset over mountains with a serene lake in the foreground. The sky shows vibrant colors of orange and pink.",
        "model_name": "moneyprinter-turbo",
        "parameters": {
            "duration": 10,
            "style": "cinematic",
            "tone": "peaceful"
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    print("Step 1: Creating video generation job...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_url}/api/v1/jobs",
                json=job_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    job_id = result.get("id")
                    print(f"✅ Job created successfully: {job_id}")
                    print(f"   Status: {result.get('status')}")
                    print(f"   Prompt: {result.get('prompt')[:50]}...")
                else:
                    print(f"❌ Failed to create job. Status: {response.status}")
                    response_text = await response.text()
                    print(f"   Response: {response_text}")
                    return False
    except Exception as e:
        print(f"❌ Error creating job: {e}")
        return False

    # Step 2: Monitor job progress
    print("\nStep 2: Monitoring job progress...")
    max_attempts = 60  # 5 minutes with 5-second intervals
    attempt = 0
    
    try:
        async with aiohttp.ClientSession() as session:
            while attempt < max_attempts:
                attempt += 1
                await asyncio.sleep(5)
                
                async with session.get(
                    f"{api_url}/api/v1/jobs/{job_id}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        job_status = await response.json()
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
                    else:
                        print(f"  Attempt {attempt}: Failed to get job status - {response.status}")
    except Exception as e:
        print(f"❌ Error monitoring job: {e}")
        return False
    
    print(f"⏰ Job monitoring timed out after {max_attempts * 5} seconds")
    return False


async def main():
    """Main test function."""
    print("=" * 70)
    print("VIDEO GENERATION TEST WITH PILLOW-BASED TEXT RENDERING")
    print("=" * 70)
    
    success = await test_video_generation()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ VIDEO GENERATION TEST PASSED!")
        print("The updated code with Pillow-based text rendering is working correctly.")
    else:
        print("❌ VIDEO GENERATION TEST FAILED!")
        print("There may be issues with the video generation process.")
    print("=" * 70)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)