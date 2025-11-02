"""Test script for video generation."""

import asyncio
import os
import time
from pathlib import Path
from uuid import uuid4

from loguru import logger

from src.config import Settings, get_settings
from src.domain.entities import User
from src.infrastructure.adapters.database import PostgreSQLUserRepository
from src.infrastructure.adapters.storage import S3Storage
from src.infrastructure.database import check_db_health, get_session_factory
from src.infrastructure.services import MoviePyVideoGenerator


def create_storage(settings: Settings) -> S3Storage:
    """Helper function to create S3Storage from settings."""
    return S3Storage(
        access_key_id=settings.s3_access_key_id,
        secret_access_key=settings.s3_secret_access_key,
        bucket_name=settings.s3_bucket_name,
        region=settings.s3_region,
        endpoint_url=settings.s3_endpoint_url,
        use_ssl=settings.use_ssl,
    )


async def test_script_generation():
    """Test script generation with configured LLM (Ollama or OpenAI)."""
    print("\n" + "="*60)
    print("Test 1: Script Generation")
    print("="*60)

    settings = get_settings()

    # Check LLM provider configuration
    if settings.llm_provider == "openai" and not settings.openai_api_key:
        print("❌ OpenAI API key not configured")
        print("   Set OPENAI_API_KEY in .env file or switch to Ollama (LLM_PROVIDER=ollama)")
        return False
    elif settings.llm_provider == "ollama":
        # Test Ollama connectivity
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{settings.ollama_base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status != 200:
                        print(f"❌ Ollama not accessible at {settings.ollama_base_url}")
                        print("   Make sure Ollama is running: ollama serve")
                        return False
        except Exception as e:
            print(f"❌ Failed to connect to Ollama: {e}")
            print(f"   Make sure Ollama is running at {settings.ollama_base_url}")
            return False

    storage = create_storage(settings)
    generator = MoviePyVideoGenerator(settings, storage)
    
    try:
        prompt = "Create a short video about the beauty of nature"
        print(f"Prompt: {prompt}")
        print("Generating script...")
        
        script = await generator.generate_script(
            prompt=prompt,
            parameters={"duration": 15, "style": "engaging", "tone": "calm"},
        )
        
        print(f"\n✅ Script generated ({len(script)} characters):")
        print("-" * 60)
        print(script)
        print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Script generation failed: {e}")
        logger.exception(e)
        return False


async def test_voiceover_generation():
    """Test voiceover generation with Edge TTS."""
    print("\n" + "="*60)
    print("Test 2: Voiceover Generation")
    print("="*60)
    
    settings = get_settings()
    storage = create_storage(settings)
    generator = MoviePyVideoGenerator(settings, storage)
    
    try:
        script = """
SCENE 1: A beautiful sunrise over mountains
NARRATION: Welcome to the beauty of nature. Watch as the sun rises over majestic mountains.

SCENE 2: A flowing river through a forest
NARRATION: Listen to the peaceful sound of water flowing through ancient forests.

SCENE 3: A colorful sunset
NARRATION: End your day with the breathtaking colors of a sunset.
"""
        
        print("Generating voiceover...")
        print(f"Voice: {settings.tts_voice}")
        
        audio_path = await generator.generate_voiceover(
            script=script,
            voice=None,  # Use default
        )
        
        # Check if file exists
        if os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path)
            print(f"✅ Voiceover generated: {audio_path}")
            print(f"   File size: {file_size:,} bytes")
            
            # Clean up
            await generator.cleanup_temp_files(audio_path)
            print(f"   Cleaned up temp file")
            
            return True
        else:
            print(f"❌ Audio file not found: {audio_path}")
            return False
        
    except Exception as e:
        print(f"❌ Voiceover generation failed: {e}")
        logger.exception(e)
        return False


async def test_video_composition():
    """Test video composition with MoviePy."""
    print("\n" + "="*60)
    print("Test 3: Video Composition")
    print("="*60)
    
    settings = get_settings()
    storage = create_storage(settings)
    generator = MoviePyVideoGenerator(settings, storage)

    audio_path = None
    video_path = None
    
    try:
        script = """
SCENE 1: Nature's Beauty
NARRATION: Welcome to the beauty of nature.

SCENE 2: Mountains and Rivers
NARRATION: Explore majestic mountains and flowing rivers.

SCENE 3: Peaceful Sunset
NARRATION: End your day with a peaceful sunset.
"""
        
        print("Step 1: Generating voiceover...")
        audio_path = await generator.generate_voiceover(script=script)
        print(f"✅ Audio: {audio_path}")
        
        print("\nStep 2: Composing video...")
        print("   This may take a minute...")
        
        video_path = await generator.generate_video(
            script=script,
            audio_path=audio_path,
            parameters={
                "width": 1080,
                "height": 1920,
                "fps": 30,
            },
        )
        
        # Check if file exists
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
            print(f"✅ Video generated: {video_path}")
            print(f"   File size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")
            
            # Clean up
            await generator.cleanup_temp_files(audio_path, video_path)
            print(f"   Cleaned up temp files")
            
            return True
        else:
            print(f"❌ Video file not found: {video_path}")
            return False
        
    except Exception as e:
        print(f"❌ Video composition failed: {e}")
        logger.exception(e)
        
        # Clean up on error
        if audio_path or video_path:
            await generator.cleanup_temp_files(
                *(f for f in [audio_path, video_path] if f)
            )
        
        return False


async def test_s3_upload():
    """Test S3 upload."""
    print("\n" + "="*60)
    print("Test 4: S3 Upload")
    print("="*60)
    
    settings = get_settings()
    storage = create_storage(settings)

    try:
        # Create a test file
        test_content = b"This is a test video file"
        test_file = Path(tempfile.gettempdir()) / f"test_{os.urandom(4).hex()}.mp4"
        test_file.write_bytes(test_content)
        
        print(f"Test file: {test_file}")
        print("Uploading to S3...")
        
        job_id = uuid4()
        key = f"videos/{job_id}.mp4"
        
        await storage.upload_file(
            file_path=str(test_file),
            key=key,
            content_type="video/mp4",
        )
        
        # Construct URL
        url = f"{settings.s3_endpoint_url}/{settings.s3_bucket_name}/{key}"
        print(f"✅ File uploaded: {url}")
        
        # Clean up
        test_file.unlink()
        print("   Cleaned up test file")
        
        return True
        
    except Exception as e:
        print(f"❌ S3 upload failed: {e}")
        logger.exception(e)
        return False


async def test_end_to_end():
    """Test end-to-end video generation."""
    print("\n" + "="*60)
    print("Test 5: End-to-End Video Generation")
    print("="*60)
    
    settings = get_settings()
    storage = create_storage(settings)
    generator = MoviePyVideoGenerator(settings, storage)

    audio_path = None
    video_path = None

    try:
        prompt = "Create a 10-second video about the importance of clean water"
        print(f"Prompt: {prompt}")
        
        # Step 1: Generate script
        print("\nStep 1: Generating script...")
        script = await generator.generate_script(
            prompt=prompt,
            parameters={"duration": 10, "style": "educational"},
        )
        print(f"✅ Script: {len(script)} characters")
        
        # Step 2: Generate voiceover
        print("\nStep 2: Generating voiceover...")
        audio_path = await generator.generate_voiceover(script=script)
        print(f"✅ Audio: {audio_path}")
        
        # Step 3: Generate video
        print("\nStep 3: Composing video...")
        print("   This may take a minute...")
        video_path = await generator.generate_video(
            script=script,
            audio_path=audio_path,
            parameters={"width": 1080, "height": 1920, "fps": 30},
        )
        print(f"✅ Video: {video_path}")
        
        # Step 4: Upload to S3
        print("\nStep 4: Uploading to S3...")
        job_id = uuid4()
        video_url = await generator.upload_video(
            video_path=video_path,
            job_id=job_id,
        )
        print(f"✅ Uploaded: {video_url}")
        
        # Clean up
        await generator.cleanup_temp_files(audio_path, video_path)
        print("\n✅ End-to-end test completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ End-to-end test failed: {e}")
        logger.exception(e)
        
        # Clean up on error
        if audio_path or video_path:
            await generator.cleanup_temp_files(
                *(f for f in [audio_path, video_path] if f)
            )
        
        return False


async def main():
    """Run all video generator tests."""
    print("\n" + "="*60)
    print("VIDEO GENERATOR TESTS")
    print("="*60)
    
    # Check database connection
    print("\nChecking database connection...")
    if not await check_db_health():
        print("❌ Database connection failed")
        return
    print("✅ Database connection OK")
    
    # Check configuration
    settings = get_settings()
    print("\nConfiguration:")
    print(f"  LLM Provider: {settings.llm_provider}")
    if settings.llm_provider == "ollama":
        print(f"  Ollama URL: {settings.ollama_base_url}")
        print(f"  Ollama Model: {settings.ollama_model}")
    else:
        print(f"  OpenAI API Key: {'✅ Set' if settings.openai_api_key else '❌ Not set'}")
        print(f"  OpenAI Model: {settings.openai_model}")
    print(f"  TTS Provider: {settings.tts_provider}")
    print(f"  TTS Voice: {settings.tts_voice}")
    print(f"  Video Resolution: {settings.video_resolution_width}x{settings.video_resolution_height}")
    print(f"  S3 Endpoint: {settings.s3_endpoint_url}")
    
    # Run tests
    results = {}
    
    # Test 1: Script generation
    results["script"] = await test_script_generation()
    
    # Test 2: Voiceover generation
    results["voiceover"] = await test_voiceover_generation()
    
    # Test 3: Video composition
    results["video"] = await test_video_composition()
    
    # Test 4: S3 upload (skip if MinIO not running)
    # results["s3"] = await test_s3_upload()
    
    # Test 5: End-to-end (only if all previous tests passed)
    if all([results["script"], results["voiceover"], results["video"]]):
        results["end_to_end"] = await test_end_to_end()
    else:
        print("\n⚠️  Skipping end-to-end test due to previous failures")
        results["end_to_end"] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20} {status}")
    print("="*60)
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed")


if __name__ == "__main__":
    import tempfile
    asyncio.run(main())

