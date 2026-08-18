"""Test script for HuggingFace Wan2.2 video generator."""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import Settings, get_settings
from src.infrastructure.services.huggingface_video_generator import HuggingFaceVideoGenerator
from src.infrastructure.adapters.storage import S3Storage


class TestHuggingFaceVideoGenerator:
    """Test cases for HuggingFace video generator."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return get_settings()

    @pytest.fixture
    def storage(self, settings):
        """Create S3 storage adapter for testing."""
        return S3Storage(
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            bucket_name=settings.s3_bucket_name,
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            use_ssl=settings.use_ssl,
        )

    @pytest.fixture
    def hf_generator(self, settings, storage):
        """Create HuggingFace video generator instance with mocked model."""
        with patch("diffusers.WanPipeline.from_pretrained") as mock_load:
            mock_pipe = MagicMock()
            mock_load.return_value = mock_pipe
            generator = HuggingFaceVideoGenerator(settings, storage)
            # Replace the actual pipe with the mock since init already ran
            generator.pipe = mock_pipe
            yield generator

    def test_initialization_sets_attributes(self, settings, storage):
        """Test that initialization sets correct attributes."""
        with patch("diffusers.WanPipeline.from_pretrained") as mock_load:
            mock_pipe = MagicMock()
            mock_load.return_value = mock_pipe
            generator = HuggingFaceVideoGenerator(settings, storage)

            assert generator is not None
            assert generator.pipe == mock_pipe
            assert str(generator.temp_dir) == os.path.join(
                tempfile.gettempdir(), "media_generation_hf"
            )
            assert generator.model_name == "Wan-AI/Wan2.2-TI2V-5B"
            logger.info("✅ Initialization attributes test passed")

    def test_health_check_when_pipe_loaded(self, hf_generator):
        """Test health check returns True when pipe is loaded."""
        # health_check checks if pipe is not None
        is_healthy = hf_generator.health_check()
        assert is_healthy is True
        logger.info("✅ Health check (healthy) test passed")

    def test_health_check_when_pipe_missing(self, settings, storage):
        """Test health check returns False when pipe is None."""
        # Test the health_check method directly
        from unittest.mock import PropertyMock
        generator = HuggingFaceVideoGenerator.__new__(HuggingFaceVideoGenerator)
        generator.pipe = None
        generator.settings = settings
        generator.storage = storage
        generator.temp_dir = Path(tempfile.gettempdir()) / "media_generation_hf"

        # Mock temp_dir existence check
        with patch.object(generator.temp_dir, "__bool__", return_value=False):
            is_healthy = generator.health_check()
            assert is_healthy is False
        logger.info("✅ Health check (unhealthy) test passed")

    @pytest.mark.asyncio
    async def test_generate_script_passthrough(self, hf_generator):
        """Test generate_script returns the original prompt."""
        result = await hf_generator.generate_script(prompt="Test prompt about nature")
        assert result == "Test prompt about nature"
        logger.info("✅ Generate script passthrough test passed")

    @pytest.mark.asyncio
    async def test_generate_voiceover_falls_back_to_edge(self, hf_generator, settings):
        """Test generate_voiceover falls back to Edge TTS."""
        import edge_tts

        with patch("edge_tts.Communicate") as mock_commute:
            mock_communicate = MagicMock()
            mock_commute.return_value = mock_communicate

            # Mock the save method to be async
            async def mock_save():
                pass

            mock_communicate.save = mock_save

            result = await hf_generator.generate_voiceover(
                script="Test script for voiceover",
                voice="en-US-AriaNeural",
            )

            # Should return an audio path
            assert isinstance(result, str)
            assert len(result) > 0
            logger.info("✅ Generate voiceover fallback test passed")

    @pytest.mark.asyncio
    async def test_upload_video_uses_storage(self, hf_generator, settings, storage):
        """Test upload_video uses the storage adapter."""
        with patch.object(storage, "upload_file") as mock_upload:
            mock_upload.return_value = None

            job_id = "test-job-123"
            result = await hf_generator.upload_video(
                video_path="/tmp/test_video.mp4",
                job_id=job_id,
            )

            # Verify storage upload was called
            mock_upload.assert_called_once()
            logger.info("✅ Upload video test passed")

    @pytest.mark.asyncio
    async def test_cleanup_temp_files(self, hf_generator):
        """Test cleanup_temp_files removes files."""
        # Create a temp file
        temp_file = str(hf_generator.temp_dir / "test_file.mp4")
        os.makedirs(hf_generator.temp_dir, exist_ok=True)
        with open(temp_file, "w") as f:
            f.write("test content")

        # Call cleanup
        await hf_generator.cleanup_temp_files(temp_file)

        # File should be removed
        assert not os.path.exists(temp_file)
        logger.info("✅ Cleanup temp files test passed")
