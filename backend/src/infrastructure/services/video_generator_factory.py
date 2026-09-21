"""Resolve a requested model without silently changing its renderer."""
from ...domain.value_objects import ModelType


def default_video_model(settings):
    return {"huggingface_api": ModelType.WAN_2_2_API.value,
            "huggingface": ModelType.WAN_2_2_LOCAL.value,
            "moviepy": ModelType.MONEYPRINTER_TURBO.value}[settings.video_provider]


def create_video_generator(settings, storage, model_name):
    model = model_name or default_video_model(settings)
    if model in (ModelType.WAN_2_2_API, ModelType.WAN_2_2_LOCAL):
        from .huggingface_video_generator import HuggingFaceVideoGenerator
        return HuggingFaceVideoGenerator(settings, storage, hosted=model == ModelType.WAN_2_2_API)
    if model == ModelType.MONEYPRINTER_TURBO:
        from .moviepy_video_generator import MoviePyVideoGenerator
        return MoviePyVideoGenerator(settings, storage)
    raise ValueError(f"Video model {model!r} has no implemented generator. Use wan-2.2-api or wan-2.2-local.")
