"""Model type value object."""

from enum import Enum


class ModelType(str, Enum):
    """Represents the AI model used for generation."""
    
    # Image Models
    HUNYUAN_IMAGE_3_0 = "hunyuan-image-3.0"
    STABLE_DIFFUSION = "stable-diffusion"
    
    # Video Models
    MONEYPRINTER_TURBO = "moneyprinter-turbo"
    
    # Text Models
    GPT_TEXT = "gpt-text-generator"
    
    def get_content_type(self) -> str:
        """Get the content type this model generates."""
        from .content_type import ContentType
        
        model_to_content = {
            ModelType.HUNYUAN_IMAGE_3_0: ContentType.IMAGE,
            ModelType.STABLE_DIFFUSION: ContentType.IMAGE,
            ModelType.MONEYPRINTER_TURBO: ContentType.VIDEO,
            ModelType.GPT_TEXT: ContentType.TEXT,
        }
        return model_to_content[self].value
    
    def requires_gpu(self) -> bool:
        """Check if this model requires GPU for inference."""
        gpu_models = {
            ModelType.HUNYUAN_IMAGE_3_0,
            ModelType.STABLE_DIFFUSION,
            ModelType.MONEYPRINTER_TURBO,
        }
        return self in gpu_models
    
    def get_estimated_time(self) -> int:
        """Get estimated generation time in seconds."""
        estimates = {
            ModelType.HUNYUAN_IMAGE_3_0: 25,
            ModelType.STABLE_DIFFUSION: 15,
            ModelType.MONEYPRINTER_TURBO: 240,
            ModelType.GPT_TEXT: 5,
        }
        return estimates.get(self, 30)

