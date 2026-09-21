"""Real Wan video generation. Never substitute slides for failed inference."""

import asyncio
from contextlib import ExitStack
from pathlib import Path
import tempfile
import threading
from uuid import uuid4

from ...domain.services import VideoGeneratorService

NEGATIVE_PROMPT = "subtitles, text overlays, watermark, blurry, distorted anatomy, static image"
_LOCAL_LOCK = threading.Lock()
_LOCAL_PIPELINES = {}


class HuggingFaceVideoGenerator(VideoGeneratorService):
    """Hosted Wan 2.2 A14B or local Wan 2.2 5B with lazy GPU loading."""

    def __init__(self, settings, storage_adapter, *, hosted=False):
        self.settings = settings
        self.storage = storage_adapter
        self.hosted = hosted
        self.temp_dir = Path(tempfile.gettempdir()) / "media_generation_hf"
        self.temp_dir.mkdir(exist_ok=True)

    @staticmethod
    def validate_parameters(parameters, hosted):
        p = dict(parameters or {})
        allowed = {"duration", "aspect_ratio", "seed", "negative_prompt", "num_inference_steps", "narration"}
        unknown = set(p) - allowed
        if unknown:
            raise ValueError(f"Unsupported video parameters: {', '.join(sorted(unknown))}. Use duration, aspect_ratio, seed, negative_prompt, num_inference_steps, narration.")
        duration = p.get("duration", 5)
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not 1 <= duration <= 5:
            raise ValueError("Wan clips support duration from 1 to 5 seconds. Generate separate shots for longer videos.")
        if p.get("aspect_ratio", "16:9") not in ("16:9", "9:16"):
            raise ValueError("aspect_ratio must be 16:9 or 9:16")
        steps = p.get("num_inference_steps", 27 if hosted else 50)
        if type(steps) is not int or not 20 <= steps <= 60:
            raise ValueError("num_inference_steps must be an integer from 20 to 60")
        if "seed" in p and (type(p["seed"]) is not int or not 0 <= p["seed"] <= 2**31 - 1):
            raise ValueError("seed must be an integer between 0 and 2147483647")
        for key in ("negative_prompt", "narration"):
            if key in p and (not isinstance(p[key], str) or len(p[key]) > 2000):
                raise ValueError(f"{key} must be text of at most 2000 characters")
        return p

    async def generate_script(self, prompt, parameters=None, progress_callback=None):
        # Preserve visual intent; do not send SCENE/NARRATION scripts to diffusion.
        if not prompt.strip():
            raise ValueError("Video prompt cannot be empty")
        return prompt.strip()

    async def generate_voiceover(self, script, voice=None, progress_callback=None):
        import edge_tts
        path = self.temp_dir / f"{uuid4().hex}.mp3"
        try:
            await edge_tts.Communicate(script, voice or self.settings.tts_voice).save(str(path))
            return str(path)
        except BaseException:
            path.unlink(missing_ok=True)
            raise

    def _generate_hosted(self, prompt, params, path):
        from huggingface_hub import InferenceClient
        if not self.settings.hf_token or not self.settings.hf_token.strip():
            raise ValueError("Set HF_TOKEN with Inference Providers permission, or use wan-2.2-local on a CUDA worker.")
        # fal's Wan A14B schema is explicitly supported here, not arbitrary provider schemas.
        if self.settings.hf_video_api_model != "Wan-AI/Wan2.2-T2V-A14B":
            raise ValueError("This adapter supports HF_VIDEO_API_MODEL=Wan-AI/Wan2.2-T2V-A14B")
        frames = max(17, 4 * round(params.get("duration", 5) * 16 / 4) + 1)
        client = InferenceClient(provider="fal-ai", api_key=self.settings.hf_token,
                                 timeout=self.settings.hf_video_timeout)
        try:
            data = client.text_to_video(
                prompt, model=self.settings.hf_video_api_model,
                num_frames=frames, seed=params.get("seed"),
                num_inference_steps=params.get("num_inference_steps", 27),
                extra_body={
                    "negative_prompt": params.get("negative_prompt", NEGATIVE_PROMPT),
                    "frames_per_second": 16, "resolution": "720p",
                    "aspect_ratio": params.get("aspect_ratio", "16:9"),
                    "enable_prompt_expansion": False,
                },
            )
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            messages = {
                401: "Hugging Face rejected HF_TOKEN. Configure a valid token.",
                403: "HF_TOKEN needs Inference Providers permission and access to the selected model.",
                402: "Hugging Face inference credits are exhausted. Add credits or use wan-2.2-local on a CUDA worker.",
                429: "Hugging Face rate limit reached. Try again later; no automatic paid retry was submitted.",
            }
            if status in messages:
                raise RuntimeError(messages[status]) from exc
            raise
        if not isinstance(data, bytes) or not data:
            raise RuntimeError("Video provider returned no video bytes")
        path.write_bytes(data)

    def _generate_local(self, prompt, params, path):
        try:
            import torch
            from diffusers import AutoencoderKLWan, WanPipeline
            from diffusers.utils import export_to_video
        except ImportError as exc:
            raise RuntimeError("Install backend/requirements-video-local.txt on a CUDA worker") from exc
        if not torch.cuda.is_available():
            raise RuntimeError("Local Wan requires an NVIDIA CUDA GPU; use wan-2.2-api on this machine")
        model = self.settings.hf_model_name
        if model != "Wan-AI/Wan2.2-TI2V-5B-Diffusers":
            raise ValueError("Local adapter requires Wan-AI/Wan2.2-TI2V-5B-Diffusers")
        # Serialize GPU use and reuse weights between jobs in a worker process.
        with _LOCAL_LOCK:
            pipe = _LOCAL_PIPELINES.get(model)
            if pipe is None:
                vae = AutoencoderKLWan.from_pretrained(model, subfolder="vae", torch_dtype=torch.float32)
                pipe = WanPipeline.from_pretrained(model, vae=vae, torch_dtype=torch.bfloat16)
                pipe.enable_model_cpu_offload()
                pipe.vae.enable_tiling()
                _LOCAL_PIPELINES[model] = pipe
            width, height = (1280, 704) if params.get("aspect_ratio", "16:9") == "16:9" else (704, 1280)
            frames = 4 * round(params.get("duration", 5) * 24 / 4) + 1
            generator = torch.Generator(device="cpu").manual_seed(params["seed"]) if "seed" in params else None
            with torch.inference_mode():
                result = pipe(prompt=prompt, negative_prompt=params.get("negative_prompt", NEGATIVE_PROMPT),
                              width=width, height=height, num_frames=frames,
                              num_inference_steps=params.get("num_inference_steps", 50),
                              guidance_scale=5.0, generator=generator)
            frames_out = result.frames[0]
            if len(frames_out) < 2:
                raise RuntimeError("Wan returned no usable video frames")
            export_to_video(frames_out, str(path), fps=24)

    @staticmethod
    def _validate_video(path):
        from moviepy import VideoFileClip
        import numpy as np
        with VideoFileClip(str(path)) as clip:
            if not clip.duration or clip.duration <= 0 or min(clip.size) < 16:
                raise RuntimeError("Provider returned an invalid video")
            # Catch the former blank ColorClip failure without claiming semantic quality scoring.
            samples = [clip.get_frame(clip.duration * t) for t in (0.1, 0.5, 0.9)]
            if all(float(np.std(frame.astype(float), axis=(0, 1)).max()) < 1 for frame in samples):
                raise RuntimeError("Generated video contains only solid-color frames")
            return clip.duration

    @staticmethod
    def _add_audio(video_path, audio_path, output):
        from moviepy import VideoFileClip, AudioFileClip
        with ExitStack() as stack:
            video = stack.enter_context(VideoFileClip(str(video_path)))
            audio = stack.enter_context(AudioFileClip(audio_path))
            if audio.duration > video.duration + 0.1:
                raise ValueError("Narration exceeds the video duration; shorten narration or generate more shots")
            composed = video.with_audio(audio)
            stack.callback(composed.close)
            composed.write_videofile(str(output), codec="libx264", audio_codec="aac", logger=None)

    async def generate_video(self, script, audio_path="", parameters=None, progress_callback=None):
        params = self.validate_parameters(parameters, self.hosted)
        raw = self.temp_dir / f"{uuid4().hex}.mp4"
        final = self.temp_dir / f"{uuid4().hex}.mp4"
        try:
            if progress_callback:
                progress_callback(10)
            generate = self._generate_hosted if self.hosted else self._generate_local
            await asyncio.to_thread(generate, script, params, raw)
            await asyncio.to_thread(self._validate_video, raw)
            if audio_path:
                await asyncio.to_thread(self._add_audio, raw, audio_path, final)
                await asyncio.to_thread(self._validate_video, final)
                raw.unlink(missing_ok=True)
            else:
                raw.replace(final)
            if progress_callback:
                progress_callback(100)
            return str(final)
        except Exception:
            raw.unlink(missing_ok=True)
            final.unlink(missing_ok=True)
            raise

    async def upload_video(self, video_path, job_id, progress_callback=None):
        key = f"videos/{job_id}.mp4"
        with open(video_path, "rb") as stream:
            success = await self.storage.upload(key=key, data=stream, content_type="video/mp4")
        if not success:
            raise RuntimeError("Video upload failed")
        url = await self.storage.get_presigned_url(key)
        if not url:
            raise RuntimeError("Could not create a video download URL")
        return url

    async def cleanup_temp_files(self, *file_paths):
        for path in file_paths:
            if path:
                Path(path).unlink(missing_ok=True)
