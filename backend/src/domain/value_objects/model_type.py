"""Model type value object."""

import os
from enum import Enum
from typing import Dict, Iterable, Tuple


class ModelType(str, Enum):
    """Represents the AI model used for generation."""
    
    # Image Models
    HUNYUAN_IMAGE_3_0 = "hunyuan-image-3.0"
    STABLE_DIFFUSION = "stable-diffusion"
    
    # Video Models
    LUMA_DREAM_MACHINE = "luma-dream-machine"
    MONEYPRINTER_TURBO = "moneyprinter-turbo"
    
    # Text Models
    GPT_TEXT = "gpt-text-generator"

    @classmethod
    def get_video_model_priority(cls) -> Iterable["ModelType"]:
        """Return video models ordered from highest to lowest fidelity."""
        return (
            cls.LUMA_DREAM_MACHINE,
            cls.MONEYPRINTER_TURBO,
        )

    @classmethod
    def get_preferred_video_model(cls) -> "ModelType":
        """Pick the best available video model with MoneyPrinter fallback."""
        for model in cls.get_video_model_priority():
            if cls._is_model_available(model):
                return model
        return cls.MONEYPRINTER_TURBO

    @classmethod
    def _is_model_available(cls, model: "ModelType") -> bool:
        """Check whether the runtime has enough credentials for the model."""
        requirements: Dict[ModelType, Tuple[str, ...]] = {
            cls.LUMA_DREAM_MACHINE: ("LUMAAI_API_KEY",),
            cls.MONEYPRINTER_TURBO: tuple(),
        }
        required_env = requirements.get(model, tuple())
        return all(os.getenv(var) for var in required_env)
    
    def get_content_type(self) -> str:
        """Get the content type this model generates."""
        from .content_type import ContentType
        
        model_to_content = {
            ModelType.HUNYUAN_IMAGE_3_0: ContentType.IMAGE,
            ModelType.STABLE_DIFFUSION: ContentType.IMAGE,
            ModelType.LUMA_DREAM_MACHINE: ContentType.VIDEO,
            ModelType.MONEYPRINTER_TURBO: ContentType.VIDEO,
            ModelType.GPT_TEXT: ContentType.TEXT,
        }
        return model_to_content[self].value
    
    def requires_gpu(self) -> bool:
        """Check if this model requires GPU for inference."""
        gpu_models = {
            ModelType.HUNYUAN_IMAGE_3_0,
            ModelType.STABLE_DIFFUSION,
            ModelType.LUMA_DREAM_MACHINE,
            ModelType.MONEYPRINTER_TURBO,
        }
        return self in gpu_models
    
    def get_estimated_time(self) -> int:
        """Get estimated generation time in seconds."""
        estimates = {
            ModelType.HUNYUAN_IMAGE_3_0: 25,
            ModelType.STABLE_DIFFUSION: 15,
            ModelType.LUMA_DREAM_MACHINE: 180,
            ModelType.MONEYPRINTER_TURBO: 240,
            ModelType.GPT_TEXT: 5,
        }
        return estimates.get(self, 30)
