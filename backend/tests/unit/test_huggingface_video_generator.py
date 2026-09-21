"""Regression tests: model frames must survive encoding; errors must not become slides."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from moviepy import ImageSequenceClip, VideoFileClip, ColorClip

from src.infrastructure.services.huggingface_video_generator import HuggingFaceVideoGenerator
from src.infrastructure.services.video_generator_factory import create_video_generator, default_video_model


@pytest.fixture
def generator(tmp_path):
    settings = SimpleNamespace(hf_token="test-token", hf_video_api_model="Wan-AI/Wan2.2-T2V-A14B",
                               hf_video_timeout=60, video_provider="huggingface_api")
    gen = HuggingFaceVideoGenerator(settings, AsyncMock(), hosted=True)
    gen.temp_dir = tmp_path
    return gen


def moving_video(path):
    frames = []
    for i in range(16):
        f = np.zeros((64, 96, 3), dtype=np.uint8)
        f[:, :, 1] = np.arange(96, dtype=np.uint8)[None, :] * 2
        f[16:40, i * 3:i * 3 + 20, 0] = 255
        frames.append(f)
    with ImageSequenceClip(frames, fps=16) as clip:
        clip.write_videofile(str(path), codec="libx264", logger=None)


@pytest.mark.asyncio
async def test_hosted_bytes_preserved_and_decodable(generator, tmp_path):
    source = tmp_path / 'source.mp4'
    moving_video(source)
    data = source.read_bytes()
    source.unlink()
    with patch('huggingface_hub.InferenceClient') as factory:
        factory.return_value.text_to_video.return_value = data
        result = await generator.generate_video('fox walking', parameters={'seed':42})
        assert Path(result).read_bytes() == data
        args = factory.return_value.text_to_video.call_args
        assert args.args == ('fox walking',)
        assert args.kwargs['num_frames'] == 81
        assert args.kwargs['extra_body']['aspect_ratio'] == '16:9'
        with VideoFileClip(result) as clip:
            assert np.abs(clip.get_frame(.1).astype(float) - clip.get_frame(.8)).mean() > 1
    await generator.cleanup_temp_files(result)
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
async def test_provider_failure_is_not_a_successful_placeholder(generator):
    with patch('huggingface_hub.InferenceClient') as factory:
        factory.return_value.text_to_video.side_effect = RuntimeError('quota exhausted')
        with pytest.raises(RuntimeError, match='quota exhausted'):
            await generator.generate_video('fox')
    assert not list(generator.temp_dir.iterdir())


@pytest.mark.asyncio
async def test_invalid_provider_output_is_rejected(generator):
    with patch('huggingface_hub.InferenceClient') as factory:
        factory.return_value.text_to_video.return_value = b'{"error":"bad"}'
        with pytest.raises(Exception):
            await generator.generate_video('fox')
    assert not list(generator.temp_dir.iterdir())


def test_blank_video_rejected(tmp_path):
    path = tmp_path / 'blank.mp4'
    with ColorClip((64,64), color=(200,0,0), duration=1) as clip:
        clip.write_videofile(str(path), fps=16, codec='libx264', logger=None)
    with pytest.raises(RuntimeError, match='solid-color'):
        HuggingFaceVideoGenerator._validate_video(path)


@pytest.mark.parametrize('params', [{'duration':30}, {'duration':float('nan')}, {'seed':-1},
                                  {'fps':30}, {'width':1080}, {'aspect_ratio':'4:3'},
                                  {'num_inference_steps':1}, {'narration':True}])
def test_invalid_parameters_rejected_before_inference(params):
    with pytest.raises(ValueError):
        HuggingFaceVideoGenerator.validate_parameters(params, True)


@pytest.mark.asyncio
async def test_missing_token_fails_without_request(generator):
    generator.settings.hf_token = ''
    with patch('huggingface_hub.InferenceClient') as client:
        with pytest.raises(ValueError, match='HF_TOKEN'):
            await generator.generate_video('fox')
        client.assert_not_called()


@pytest.mark.asyncio
async def test_upload_uses_storage_contract(generator, tmp_path):
    path = tmp_path / 'sample.mp4'
    path.write_bytes(b'video')
    generator.storage.get_presigned_url.return_value = 'https://storage/video'
    assert await generator.upload_video(str(path), 'job') == 'https://storage/video'
    assert generator.storage.upload.call_args.kwargs['key'] == 'videos/job.mp4'
    generator.storage.upload.return_value = False
    with pytest.raises(RuntimeError, match='upload failed'):
        await generator.upload_video(str(path), 'job')


def test_explicit_model_overrides_provider(generator):
    settings = generator.settings
    settings.video_provider = 'moviepy'
    assert create_video_generator(settings, None, 'wan-2.2-api').hosted
    assert not create_video_generator(settings, None, 'wan-2.2-local').hosted
    assert default_video_model(settings) == 'moneyprinter-turbo'
    with pytest.raises(ValueError, match='no implemented generator'):
        create_video_generator(settings, None, 'luma-dream-machine')


@pytest.mark.asyncio
async def test_local_pipeline_frames_are_exported(generator, monkeypatch):
    import sys
    import contextlib
    from src.infrastructure.services.huggingface_video_generator import _LOCAL_PIPELINES
    pipeline = MagicMock()
    frames = [np.zeros((32,32,3),dtype=np.uint8), np.ones((32,32,3),dtype=np.uint8)]
    pipeline.return_value.frames = [frames]
    diffusers = MagicMock()
    diffusers.WanPipeline.from_pretrained.return_value = pipeline
    torch = MagicMock()
    torch.cuda.is_available.return_value = True
    torch.inference_mode = contextlib.nullcontext
    utils = MagicMock()
    monkeypatch.setitem(sys.modules, 'torch', torch)
    monkeypatch.setitem(sys.modules, 'diffusers', diffusers)
    monkeypatch.setitem(sys.modules, 'diffusers.utils', utils)
    generator.settings.hf_model_name = 'Wan-AI/Wan2.2-TI2V-5B-Diffusers'
    _LOCAL_PIPELINES.clear()
    generator._generate_local('fox', {'duration':5}, generator.temp_dir / 'out.mp4')
    assert utils.export_to_video.call_args.args[0] is frames
    assert pipeline.call_args.kwargs['num_frames'] == 121
    assert 'duration' not in pipeline.call_args.kwargs
    assert 'fps' not in pipeline.call_args.kwargs
    _LOCAL_PIPELINES.clear()


def test_narration_mux_preserves_video_and_rejects_overlong_audio(tmp_path):
    from moviepy import AudioClip
    video = tmp_path / 'visual.mp4'
    audio = tmp_path / 'short.wav'
    long_audio = tmp_path / 'long.wav'
    output = tmp_path / 'muxed.mp4'
    moving_video(video)
    for path, duration in [(audio,.5), (long_audio,2)]:
        with AudioClip(lambda t: .1*np.sin(2*np.pi*440*t), duration=duration, fps=44100) as clip:
            clip.write_audiofile(str(path), logger=None)
    HuggingFaceVideoGenerator._add_audio(video, str(audio), output)
    with VideoFileClip(str(output)) as clip:
        assert clip.audio is not None
        assert clip.duration == pytest.approx(1, abs=.1)
    with pytest.raises(ValueError, match='Narration exceeds'):
        HuggingFaceVideoGenerator._add_audio(video, str(long_audio), tmp_path/'too-long.mp4')


@pytest.mark.asyncio
async def test_exhausted_credits_are_actionable_and_not_retried(generator):
    error = RuntimeError('Payment required')
    error.response = SimpleNamespace(status_code=402)
    with patch('huggingface_hub.InferenceClient') as factory:
        factory.return_value.text_to_video.side_effect = error
        with pytest.raises(RuntimeError, match='credits are exhausted'):
            await generator.generate_video('fox')
        assert factory.return_value.text_to_video.call_count == 1
    assert not list(generator.temp_dir.iterdir())
