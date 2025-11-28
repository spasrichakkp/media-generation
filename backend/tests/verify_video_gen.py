import sys
import os
from unittest.mock import MagicMock

# Add backend to path
sys.path.append(os.path.abspath("backend"))

# Mock dependencies that might be missing in this environment
sys.modules["edge_tts"] = MagicMock()
sys.modules["moviepy"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["aiohttp"] = MagicMock()
sys.modules["loguru"] = MagicMock()
sys.modules["pydantic"] = MagicMock()
sys.modules["pydantic_settings"] = MagicMock()
sys.modules["aioboto3"] = MagicMock()
sys.modules["botocore"] = MagicMock()
sys.modules["botocore.exceptions"] = MagicMock()

from src.infrastructure.services import MoviePyVideoGenerator
from src.domain.services import VideoGeneratorService

def verify_service():
    print("Verifying Video Generator Service...")
    
    # Mock settings and storage
    settings = MagicMock()
    settings.llm_provider = "openai"
    settings.openai_api_key = "test-key"
    
    storage = MagicMock()
    
    # Instantiate service
    try:
        service = MoviePyVideoGenerator(settings, storage)
        print("✅ MoviePyVideoGenerator instantiated successfully")
    except Exception as e:
        print(f"❌ MoviePyVideoGenerator instantiation failed: {e}")
        
    # Check inheritance
    if isinstance(service, VideoGeneratorService):
        print("✅ MoviePyVideoGenerator implements VideoGeneratorService")
    else:
        print("❌ MoviePyVideoGenerator does not implement VideoGeneratorService")

if __name__ == "__main__":
    verify_service()
