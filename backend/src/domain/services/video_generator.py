"""Video generator service interface (port)."""

from abc import ABC, abstractmethod
from typing import Any, Callable
from uuid import UUID


class VideoGeneratorService(ABC):
    """
    Abstract interface for video generation services.
    
    This interface defines the contract for video generation implementations.
    Following the Dependency Inversion Principle, the domain layer defines
    the interface, and the infrastructure layer provides the implementation.
    
    The video generation process consists of four main stages:
    1. Script Generation - Convert user prompt into a structured video script
    2. Voiceover Generation - Convert script text to speech audio
    3. Video Composition - Create video from script and audio
    4. Upload - Upload the final video to storage and return URL
    
    Example:
        ```python
        # Infrastructure provides the implementation
        generator = MoviePyVideoGenerator(settings, storage_adapter)
        
        # Generate video
        script = await generator.generate_script(
            prompt="A beautiful sunset",
            parameters={"duration": 5}
        )
        
        audio_path = await generator.generate_voiceover(
            script=script,
            voice="en-US-AriaNeural"
        )
        
        video_path = await generator.generate_video(
            script=script,
            audio_path=audio_path,
            parameters={"resolution": "1080x1920"}
        )
        
        url = await generator.upload_video(
            video_path=video_path,
            job_id=job.id
        )
        ```
    """
    
    @abstractmethod
    async def generate_script(
        self,
        prompt: str,
        parameters: dict[str, Any] | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """
        Generate a video script from a user prompt.
        
        This method uses an LLM (e.g., OpenAI GPT) to convert a user's
        prompt into a structured video script with scene descriptions
        and narration text.
        
        Args:
            prompt: User's prompt describing the desired video content
            parameters: Optional parameters for script generation:
                - duration: Target video duration in seconds
                - style: Video style (e.g., "educational", "entertaining")
                - tone: Narration tone (e.g., "professional", "casual")
            progress_callback: Optional callback to report progress (0-100)
            
        Returns:
            Generated script as a string
            
        Raises:
            Exception: If script generation fails (API errors, etc.)
        """
        pass
    
    @abstractmethod
    async def generate_voiceover(
        self,
        script: str,
        voice: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """
        Generate voiceover audio from script text.
        
        This method uses a text-to-speech service (e.g., edge-tts, OpenAI TTS)
        to convert the script text into spoken audio.
        
        Args:
            script: Script text to convert to speech
            voice: Voice ID to use (e.g., "en-US-AriaNeural")
                   If None, uses default from settings
            progress_callback: Optional callback to report progress (0-100)
            
        Returns:
            Path to the generated audio file (temporary file)
            
        Raises:
            Exception: If voiceover generation fails
        """
        pass
    
    @abstractmethod
    async def generate_video(
        self,
        script: str,
        audio_path: str,
        parameters: dict[str, Any] | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """
        Generate video from script and audio.
        
        This method uses a video composition library (e.g., moviepy) to
        create the final video by combining visual elements with the
        voiceover audio.
        
        Args:
            script: Video script with scene descriptions
            audio_path: Path to the voiceover audio file
            parameters: Optional parameters for video generation:
                - resolution: Video resolution (e.g., "1080x1920")
                - fps: Frames per second (default: 30)
                - background_color: Background color for text scenes
                - font_size: Font size for text overlays
            progress_callback: Optional callback to report progress (0-100)
            
        Returns:
            Path to the generated video file (temporary file)
            
        Raises:
            Exception: If video generation fails
        """
        pass
    
    @abstractmethod
    async def upload_video(
        self,
        video_path: str,
        job_id: UUID,
        progress_callback: Callable[[int], None] | None = None,
    ) -> str:
        """
        Upload generated video to storage.
        
        This method uploads the video file to object storage (S3/MinIO)
        and returns a URL that can be used to access the video.
        
        Args:
            video_path: Path to the video file to upload
            job_id: Job ID (used for organizing files in storage)
            progress_callback: Optional callback to report progress (0-100)
            
        Returns:
            URL to access the uploaded video (public URL or presigned URL)
            
        Raises:
            Exception: If upload fails
        """
        pass
    
    @abstractmethod
    async def cleanup_temp_files(
        self,
        *file_paths: str,
    ) -> None:
        """
        Clean up temporary files.
        
        This method removes temporary files created during video generation
        (audio files, video files, etc.) to free up disk space.
        
        Args:
            *file_paths: Variable number of file paths to delete
        """
        pass


__all__ = ["VideoGeneratorService"]

