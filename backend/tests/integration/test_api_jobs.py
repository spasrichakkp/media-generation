#!/usr/bin/env python3
"""Test script to create a video generation job via REST API."""

import asyncio
import json
import time

import httpx


async def create_job():
    """Create a video generation job via REST API."""
    
    # Job request payload
    payload = {
        "prompt": "Create a 10-second video about the beauty of ocean waves",
        "content_type": "video",
        "model_name": "moviepy-generator",
        "parameters": {
            "duration": 10,
            "style": "cinematic",
            "tone": "peaceful"
        }
    }
    
    print("=" * 60)
    print("Creating Video Generation Job via REST API")
    print("=" * 60)
    print(f"\nPayload:")
    print(json.dumps(payload, indent=2))
    print()
    
    # Create job
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/jobs",
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            
            job = response.json()
            job_id = job["id"]
            
            print("✅ Job created successfully!")
            print(f"\nJob ID: {job_id}")
            print(f"Status: {job['status']}")
            print(f"Progress: {job['progress']}%")
            print()
            
            # Poll job status
            print("Polling job status (will check every 5 seconds)...")
            print("=" * 60)
            
            max_polls = 60  # 5 minutes max
            poll_count = 0
            
            while poll_count < max_polls:
                poll_count += 1
                
                # Wait before polling
                await asyncio.sleep(5)
                
                # Get job status
                status_response = await client.get(
                    f"http://localhost:8000/api/v1/jobs/{job_id}",
                    timeout=10.0,
                )
                status_response.raise_for_status()
                
                job_status = status_response.json()
                status = job_status["status"]
                progress = job_status["progress"]
                
                print(f"[Poll {poll_count}] Status: {status:12s} | Progress: {progress:3d}%", end="")
                
                if status == "completed":
                    print(" ✅")
                    print()
                    print("=" * 60)
                    print("🎉 Job completed successfully!")
                    print("=" * 60)
                    print(f"\nResult URL: {job_status['result_url']}")
                    print(f"Total time: ~{poll_count * 5} seconds")
                    print()
                    
                    # Show full job details
                    print("Full Job Details:")
                    print(json.dumps(job_status, indent=2))
                    break
                    
                elif status == "failed":
                    print(" ❌")
                    print()
                    print("=" * 60)
                    print("❌ Job failed!")
                    print("=" * 60)
                    print(f"\nError: {job_status.get('error_message', 'Unknown error')}")
                    print()
                    print("Full Job Details:")
                    print(json.dumps(job_status, indent=2))
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
                print()
                print("⚠️ Polling timeout reached (5 minutes)")
                print(f"Last known status: {status} ({progress}%)")
                
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error: {e.response.status_code}")
            print(f"Response: {e.response.text}")
            
        except httpx.RequestError as e:
            print(f"❌ Request Error: {e}")
            print("Make sure the FastAPI server is running on http://localhost:8000")
            
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")


if __name__ == "__main__":
    asyncio.run(create_job())

