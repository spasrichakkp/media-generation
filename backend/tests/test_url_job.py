import asyncio
import aiohttp
import json
import sys
from uuid import uuid4

API_URL = "http://localhost:8000/api/v1"

async def test_url_job():
    print("Testing URL-to-Video Job...")
    
    # 1. Create Job
    job_id = str(uuid4())
    payload = {
        "user_id": "e9c94f44-6977-4802-9a4d-ff659081bb14", # Admin ID
        "content_type": "url",
        "prompt": "https://example.com",
        "model_name": "moviepy-generator",
        "parameters": {
            "duration": 5
        }
    }
    
    headers = {
        "X-API-Key": "e9c94f44-6977-4802-9a4d-ff659081bb14",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        print(f"Creating job with payload: {json.dumps(payload, indent=2)}")
        async with session.post(f"{API_URL}/jobs", json=payload, headers=headers) as response:
            if response.status not in (200, 201):
                print(f"Failed to create job: {await response.text()}")
                return
            
            data = await response.json()
            job_id = data["id"]
            print(f"Job created: {job_id}")
            
        # 2. Poll Status
        print("Polling job status...")
        for _ in range(30): # Wait up to 30 seconds
            async with session.get(f"{API_URL}/jobs/{job_id}", headers=headers) as response:
                data = await response.json()
                status = data["status"]
                print(f"Status: {status}")
                
                if status == "completed":
                    print(f"Job completed! Result URL: {data.get('result_url')}")
                    print(f"Final Prompt (Summary): {data.get('prompt')}")
                    return
                elif status == "failed":
                    print(f"Job failed: {data.get('error_message')}")
                    return
                
            await asyncio.sleep(1)
            
    print("Timeout waiting for job completion")

if __name__ == "__main__":
    asyncio.run(test_url_job())
