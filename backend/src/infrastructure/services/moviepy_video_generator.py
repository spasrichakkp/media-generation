"""MoviePy-based video generator implementation."""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

import aiohttp
import edge_tts
from loguru import logger
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    TextClip,
    ImageClip,                # <— add this
    concatenate_videoclips,
)
from openai import AsyncOpenAI
import textwrap                               # <— add this
import numpy as np                             # <— add this
from PIL import Image, ImageDraw, ImageFont  # <— add this

from ...config import Settings
from ...domain.services import VideoGeneratorService
from ..adapters.storage import S3Storage


class MoviePyVideoGenerator(VideoGeneratorService):
    """
    MoviePy-based implementation of video generator service.

    This implementation uses:
    - OpenAI GPT for script generation
    - Edge TTS for voiceover generation
    - MoviePy for video composition
    - S3/MinIO for video storage

    For MVP, generates simple text-based videos with colored backgrounds
    and voiceover narration.
    """

    def __init__(
        self,
        settings: Settings,
        storage_adapter: S3Storage,
    ) -> None:
        """
        Initialize the video generator.

        Args:
            settings: Application settings
            storage_adapter: S3 storage adapter for uploading videos
        """
        self.settings = settings
        self.storage = storage_adapter

        # Initialize LLM client based on provider
        self.llm_provider = settings.llm_provider.lower()

        if self.llm_provider == "openai":
            if settings.openai_api_key:
                self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info("Using OpenAI for script generation")
            else:
                logger.error("OpenAI API key not configured")
                self.openai_client = None
        elif self.llm_provider == "openrouter":
            if settings.openrouter_api_key:
                self.openai_client = AsyncOpenAI(
                    api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url
                )
                self.openrouter_model = settings.openrouter_model
                logger.info(f"Using OpenRouter for script generation: {self.openrouter_model}")
                logger.info(f"OpenRouter endpoint: {settings.openrouter_base_url}")
            else:
                logger.error("OpenRouter API key not configured")
                self.openai_client = None
        elif self.llm_provider == "ollama":
            self.ollama_base_url = settings.ollama_base_url
            self.ollama_model = settings.ollama_model
            logger.info(f"Using Ollama for script generation: {self.ollama_model}")
            logger.info(f"Ollama endpoint: {self.ollama_base_url}")
        elif self.llm_provider == "mock":
            logger.info("Using Mock LLM for script generation")
        else:
            logger.error(f"Unknown LLM provider: {self.llm_provider}")

        # Create temp directory for video generation
        self.temp_dir = Path(tempfile.gettempdir()) / "media_generation"
        self.temp_dir.mkdir(exist_ok=True)

        logger.info("MoviePyVideoGenerator initialized")
        logger.info(f"Temp directory: {self.temp_dir}")
        logger.info(
            f"Video resolution: {settings.video_resolution_width}x{settings.video_resolution_height}"
        )
        logger.info(f"TTS provider: {settings.tts_provider}")
        logger.info(f"TTS voice: {settings.tts_voice}")

    async def generate_script(
        self,
        prompt: str,
        parameters: dict[str, Any] | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """
        Generate video script using configured LLM provider (Ollama or OpenAI).

        Creates a structured script with scene descriptions and narration
        text based on the user's prompt.
        """
        logger.info(f"Generating script for prompt: {prompt}")
        logger.info(f"Using LLM provider: {self.llm_provider}")

        if self.llm_provider == "ollama":
            return await self._generate_script_ollama(prompt, parameters, progress_callback)
        elif self.llm_provider in ["openai", "openrouter"]:
            return await self._generate_script_openai(prompt, parameters, progress_callback)
        elif self.llm_provider == "mock":
            return """SCENE 1: A beautiful sunset over the ocean.
NARRATION: The sun dips below the horizon, painting the sky in vibrant orange and purple hues.

SCENE 2: Waves gently crashing on the shore.
NARRATION: The rhythmic sound of waves brings a sense of peace and tranquility to the ending day."""
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}")

    async def _generate_script_ollama(
        self,
        prompt: str,
        parameters: dict[str, Any] | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """Generate script using Ollama local LLM."""
        # Extract parameters
        params = parameters or {}
        duration = params.get("duration", 30)  # Default 30 seconds
        style = params.get("style", "engaging")
        tone = params.get("tone", "professional")

        # Create system prompt
        system_prompt = f"""You are a professional video script writer. Create an engaging video script based on the user's prompt.

The script should be:
- Approximately {duration} seconds long when narrated
- Written in a {tone} tone
- {style} and captivating
- Structured with clear scenes and narration

Format the script as follows:
SCENE 1: [Brief scene description]
NARRATION: [What to say in this scene]

SCENE 2: [Brief scene description]
NARRATION: [What to say in this scene]

... and so on.

Keep narration concise and impactful. Each scene should be 5-10 seconds."""

        # Combine system prompt and user prompt
        full_prompt = f"{system_prompt}\n\nUser request: {prompt}"

        try:
            if progress_callback:
                progress_callback(10)

            # Call Ollama API
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.ollama_model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.settings.ollama_temperature,
                        "num_predict": self.settings.ollama_max_tokens,
                    },
                }

                logger.debug(f"Calling Ollama API: {self.ollama_base_url}/api/generate")

                async with session.post(
                    f"{self.ollama_base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),  # 2 minute timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {response.status} - {error_text}")

                    result = await response.json()
                    script = result.get("response", "")

                    if not script:
                        raise Exception("Ollama returned empty response")

            if progress_callback:
                progress_callback(100)

            logger.info(f"Script generated successfully with Ollama ({len(script)} characters)")
            logger.debug(f"Script:\n{script}")

            return script

        except Exception as e:
            logger.error(f"Failed to generate script with Ollama: {e}")
            raise

    async def _generate_script_openai(
        self,
        prompt: str,
        parameters: dict[str, Any] | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """Generate script using OpenAI GPT."""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")

        # Extract parameters
        params = parameters or {}
        duration = params.get("duration", 30)  # Default 30 seconds
        style = params.get("style", "engaging")
        tone = params.get("tone", "professional")

        # Create system prompt
        system_prompt = f"""You are a professional video script writer. Create an engaging video script based on the user's prompt.

The script should be:
- Approximately {duration} seconds long when narrated
- Written in a {tone} tone
- {style} and captivating
- Structured with clear scenes and narration

Format the script as follows:
SCENE 1: [Brief scene description]
NARRATION: [What to say in this scene]

SCENE 2: [Brief scene description]
NARRATION: [What to say in this scene]

... and so on.

Keep narration concise and impactful. Each scene should be 5-10 seconds."""

        # Call OpenAI API
        try:
            if progress_callback:
                progress_callback(10)

            # Use appropriate model and settings based on provider
            if self.llm_provider == "openrouter":
                model = self.openrouter_model
                temperature = self.settings.openrouter_temperature
                max_tokens = self.settings.openrouter_max_tokens
            else:  # openai
                model = self.settings.openai_model
                temperature = self.settings.openai_temperature
                max_tokens = self.settings.openai_max_tokens

            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            script = response.choices[0].message.content

            if progress_callback:
                progress_callback(100)

            logger.info(
                f"Script generated successfully with {self.llm_provider} ({len(script)} characters)"
            )
            logger.debug(f"Script:\n{script}")

            return script

        except Exception as e:
            logger.error(f"Failed to generate script with OpenAI: {e}")
            raise

    async def generate_voiceover(
        self,
        script: str,
        voice: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """
        Generate voiceover using Edge TTS.

        Converts the script text to speech and saves as an audio file.
        """
        logger.info("Generating voiceover")

        # Use configured voice or default
        voice_id = voice or self.settings.tts_voice

        # Extract narration text from script
        narration_text = self._extract_narration(script)
        logger.info(f"Narration text: {narration_text[:100]}...")

        # Generate unique filename
        audio_filename = f"voiceover_{os.urandom(8).hex()}.mp3"
        audio_path = str(self.temp_dir / audio_filename)

        try:
            if progress_callback:
                progress_callback(10)

            # Create TTS communicator
            communicate = edge_tts.Communicate(
                text=narration_text,
                voice=voice_id,
                rate=self.settings.tts_rate,
                volume=self.settings.tts_volume,
            )

            # Save audio file
            await communicate.save(audio_path)

            if progress_callback:
                progress_callback(100)

            logger.info(f"Voiceover generated: {audio_path}")

            # Verify file exists
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not created: {audio_path}")

            return audio_path

        except Exception as e:
            logger.error(f"Failed to generate voiceover: {e}")
            raise

    def _extract_narration(self, script: str) -> str:
        """
        Extract narration text from script.

        Looks for lines starting with "NARRATION:" and combines them.
        """
        narration_lines = []

        for line in script.split("\n"):
            line = line.strip()
            if line.startswith("NARRATION:"):
                # Extract text after "NARRATION:"
                narration = line[len("NARRATION:") :].strip()
                narration_lines.append(narration)

        # If no NARRATION markers found, use entire script
        if not narration_lines:
            logger.warning("No NARRATION markers found in script, using entire script")
            return script

        return " ".join(narration_lines)

    async def generate_video(
        self,
        script: str,
        audio_path: str,
        parameters: dict[str, Any] | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """
        Generate video using MoviePy.

        Creates a simple text-based video with colored backgrounds
        and the voiceover audio track.
        """
        logger.info("Generating video with MoviePy")

        # Extract parameters
        params = parameters or {}
        width = params.get("width", self.settings.video_resolution_width)
        height = params.get("height", self.settings.video_resolution_height)
        fps = params.get("fps", self.settings.video_fps)

        # Generate unique filename
        video_filename = f"video_{os.urandom(8).hex()}.mp4"
        video_path = str(self.temp_dir / video_filename)

        try:
            if progress_callback:
                progress_callback(10)

            # Load audio to get duration
            audio_clip = AudioFileClip(audio_path)
            total_duration = audio_clip.duration
            logger.info(f"Audio duration: {total_duration:.2f} seconds")

            if progress_callback:
                progress_callback(30)

            # Parse script into scenes
            scenes = self._parse_scenes(script)
            logger.info(f"Parsed {len(scenes)} scenes from script")

            # Create video clips for each scene
            video_clips = await self._create_scene_clips(
                scenes=scenes,
                total_duration=total_duration,
                width=width,
                height=height,
                fps=fps,
            )

            if progress_callback:
                progress_callback(60)

            # Concatenate all clips
            logger.info("Concatenating video clips")
            final_video = concatenate_videoclips(video_clips, method="compose")

            # Add audio
            final_video = final_video.with_audio(audio_clip)

            if progress_callback:
                progress_callback(80)

            # Export video
            logger.info(f"Exporting video to {video_path}")
            final_video.write_videofile(
                video_path,
                fps=fps,
                codec=self.settings.video_codec,
                audio_codec=self.settings.audio_codec,
                bitrate=self.settings.video_bitrate or "1500k",  # e.g., 1.5 Mbps
                logger=None,  # Suppress moviepy's verbose logging
            )

            # Clean up clips
            final_video.close()
            audio_clip.close()
            for clip in video_clips:
                clip.close()

            if progress_callback:
                progress_callback(100)

            logger.info(f"Video generated successfully: {video_path}")

            # Verify file exists
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not created: {video_path}")

            return video_path

        except Exception as e:
            logger.error(f"Failed to generate video: {e}")
            raise

    def _parse_scenes(self, script: str) -> list[dict[str, str]]:
        """
        Parse script into scenes.

        Returns a list of scenes with description and narration.
        """
        scenes = []
        current_scene = {}

        for line in script.split("\n"):
            line = line.strip()

            if line.startswith("SCENE"):
                # Save previous scene if exists
                if current_scene:
                    scenes.append(current_scene)

                # Start new scene
                # Extract scene description after "SCENE X:"
                parts = line.split(":", 1)
                description = parts[1].strip() if len(parts) > 1 else "Scene"
                current_scene = {
                    "description": description,
                    "narration": "",
                }

            elif line.startswith("NARRATION:"):
                # Add narration to current scene
                narration = line[len("NARRATION:") :].strip()
                if current_scene:
                    current_scene["narration"] = narration

        # Add last scene
        if current_scene:
            scenes.append(current_scene)

        # If no scenes found, create a single scene with the entire script
        if not scenes:
            scenes = [
                {
                    "description": "Video",
                    "narration": script,
                }
            ]

        return scenes

    async def _create_scene_clips(
        self,
        scenes: list[dict[str, str]],
        total_duration: float,
        width: int,
        height: int,
        fps: int,
    ) -> list:
        """
        Create video clips for each scene.

        For MVP, creates simple colored backgrounds with text overlays.
        """
        clips = []
        duration_per_scene = total_duration / len(scenes)

        # Color palette for backgrounds
        colors = [
            (41, 128, 185),  # Blue
            (142, 68, 173),  # Purple
            (39, 174, 96),  # Green
            (230, 126, 34),  # Orange
            (231, 76, 60),  # Red
            (52, 73, 94),  # Dark blue
        ]

        for i, scene in enumerate(scenes):
            logger.info(
                f"Creating clip for scene {i + 1}/{len(scenes)}: {scene['description'][:50]}"
            )

            # Select color
            color = colors[i % len(colors)]

            # Create colored background
            background = ColorClip(
                size=(width, height),
                color=color,
                duration=duration_per_scene,
            )

            # Create colored background
            background = ColorClip(size=(width, height), color=color, duration=duration_per_scene)

            try:
                # Try MoviePy's TextClip first (will work if ImageMagick & font are OK)
                text_clip = TextClip(
                    font="Arial-Bold",
                    text=scene["description"],
                    font_size=60,
                    color="white",
                    size=(width - 100, None),
                    method="caption",
                    duration=duration_per_scene,
                ).with_position("center")
                clip = CompositeVideoClip([background, text_clip])
            except Exception as e:
                logger.warning(f"TextClip failed ({e}); using Pillow fallback")
                try:
                    text_img_clip = self._pillow_text_clip(
                        text=scene["description"],
                        width=width,
                        height=height,
                        duration=duration_per_scene,
                        fps=fps,
                    )
                    clip = CompositeVideoClip([background, text_img_clip])
                except Exception as e2:
                    logger.error(f"Pillow fallback failed ({e2}); using plain background")
                    clip = background

            clips.append(clip)

        return clips

    async def upload_video(
        self,
        video_path: str,
        job_id: UUID,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """
        Upload video to S3/MinIO storage.
        """
        logger.info(f"Uploading video to S3: {video_path}")

        try:
            if progress_callback:
                progress_callback(10)

            # Generate S3 key
            filename = f"videos/{job_id}.mp4"

            # Read video file
            with open(video_path, "rb") as f:
                video_data = f.read()

            # Upload to S3
            await self.storage.upload(
                key=filename,
                data=video_data,
                content_type="video/mp4",
            )

            if progress_callback:
                progress_callback(80)

            # Get public URL or presigned URL
            # For now, construct URL manually
            # In production, you might want to use CloudFront or presigned URLs
            url = f"{self.settings.s3_endpoint_url}/{self.settings.s3_bucket_name}/{filename}"

            if progress_callback:
                progress_callback(100)

            logger.info(f"Video uploaded successfully: {url}")

            return url

        except Exception as e:
            logger.error(f"Failed to upload video: {e}")
            raise

    def _pillow_text_clip(self, text: str, width: int, height: int,
                          duration: float, fps: int,
                          font_candidates=("DejaVuSans-Bold.ttf", "Arial-Bold.ttf", "Arial.ttf"),
                          font_size=60, fill="white", margin_ratio=0.08) -> ImageClip:
        # Transparent canvas
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Choose a font that exists
        font = None
        for name in font_candidates:
            try:
                font = ImageFont.truetype(name, font_size)
                break
            except Exception:
                pass
        if font is None:
            font = ImageFont.load_default()

        # Wrap text to fit
        margin = int(width * margin_ratio)
        max_w = width - 2 * margin
        words = text.split()
        lines, line = [], ""
        for w in words:
            test = (line + " " + w).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_w and line:
                lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)

        # Vertically center
        line_h = draw.textbbox((0, 0), "Ay", font=font)[3]
        total_h = len(lines) * line_h + max(0, len(lines) - 1) * int(line_h * 0.4)
        y = (height - total_h) // 2
        for ln in lines:
            bbox = draw.textbbox((0, 0), ln, font=font)
            tw = bbox[2] - bbox[0]
            x = (width - tw) // 2
            draw.text((x, y), ln, font=font, fill=fill)
            y += line_h + int(line_h * 0.4)

        arr = np.array(img)
        return ImageClip(arr).with_duration(duration).with_fps(fps)

    async def cleanup_temp_files(
        self,
        *file_paths: str,
    ) -> None:
        """
        Clean up temporary files.
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {e}")


__all__ = ["MoviePyVideoGenerator"]
