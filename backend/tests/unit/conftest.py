"""Conftest for unit tests."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.config import Settings  # noqa: E402
from src.domain.services import VideoGeneratorService  # noqa: E402
from src.infrastructure.services import (  # noqa: E402
    MoviePyVideoGenerator,
    HuggingFaceVideoGenerator,
)
from src.infrastructure.adapters.storage import S3Storage  # noqa: E402
