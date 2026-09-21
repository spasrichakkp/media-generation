"""Verify worker orchestration without database, storage or inference requests."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.domain.value_objects import ContentType
from src.infrastructure.tasks.video_generation import generate_video_async


@pytest.mark.asyncio
async def test_worker_routes_model_and_skips_unrequested_tts():
    job = SimpleNamespace(id=uuid4(), prompt='ocean waves', content_type=ContentType.VIDEO,
                          model_name='wan-2.2-api', parameters={})
    generator = AsyncMock()
    generator.generate_script.return_value = job.prompt
    generator.generate_video.return_value = '/tmp/render.mp4'
    generator.upload_video.return_value = 'https://storage/video.mp4'
    with patch('src.infrastructure.tasks.video_generation.update_job_status', new_callable=AsyncMock), \
         patch('src.infrastructure.adapters.storage.S3Storage') as storage, \
         patch('src.infrastructure.services.video_generator_factory.create_video_generator', return_value=generator) as factory:
        assert await generate_video_async(job) == 'https://storage/video.mp4'
        assert factory.call_args.args[1] is storage.return_value
        assert factory.call_args.args[2] == 'wan-2.2-api'
        generator.generate_voiceover.assert_not_called()
        generator.generate_video.assert_awaited_once_with(script=job.prompt, audio_path=None,
                                                          parameters={}, progress_callback=None)
        generator.cleanup_temp_files.assert_awaited_once_with('/tmp/render.mp4')


@pytest.mark.asyncio
async def test_failed_generation_does_not_upload():
    job = SimpleNamespace(id=uuid4(), prompt='ocean', content_type=ContentType.VIDEO,
                          model_name='wan-2.2-api', parameters={})
    generator = AsyncMock()
    generator.generate_script.return_value = job.prompt
    generator.generate_video.side_effect = RuntimeError('provider unavailable')
    with patch('src.infrastructure.tasks.video_generation.update_job_status', new_callable=AsyncMock), \
         patch('src.infrastructure.adapters.storage.S3Storage'), \
         patch('src.infrastructure.services.video_generator_factory.create_video_generator', return_value=generator):
        with pytest.raises(RuntimeError, match='provider unavailable'):
            await generate_video_async(job)
        generator.upload_video.assert_not_called()


@pytest.mark.asyncio
async def test_creation_commits_before_enqueue_and_selects_configured_model():
    from src.application.use_cases.create_job import CreateGenerationJobUseCase
    from src.application.dtos import CreateJobRequest
    from src.domain.entities import User
    user = User(email='test@example.test', username='test')
    users, jobs = AsyncMock(), AsyncMock()
    users.get_by_id.return_value = user
    jobs.create.side_effect = lambda job: job
    order = []
    async def commit():
        order.append('commit')
    def enqueue(_):
        order.append('enqueue')
        return SimpleNamespace(id='task')
    with patch('src.application.use_cases.create_job.get_settings', return_value=SimpleNamespace(video_provider='huggingface_api')), \
         patch('src.infrastructure.tasks.generate_video_task.delay', side_effect=enqueue):
        response = await CreateGenerationJobUseCase(jobs,users,commit).execute(user.id,CreateJobRequest(prompt='ocean',content_type='video'))
    assert response.model_name == 'wan-2.2-api'
    assert order == ['commit', 'enqueue']


def test_database_timezone_aware_quota_does_not_break_job_creation():
    from datetime import datetime, timedelta, timezone
    from src.domain.entities import User
    user = User(email='test@example.test', username='test',
                quota_reset_at=datetime.now(timezone.utc)+timedelta(hours=1))
    assert user.can_create_job()
