import os
import requests
from typing import Optional
from dataclasses import dataclass

from ..domain.entities.generation_job import GenerationJob
from ..domain.value_objects.model_type import ModelType

@dataclass
class APIResponse:
    video_url: str
    status: str

class APIVideoGenerator:
    def __init__(self, provider: str):
        self.provider = provider
        self.base_url = os.getenv(f"{provider.upper()}_BASE_URL")
        self.api_key = os.getenv(f"{provider.upper()}_API_KEY")
        self.model_name = os.getenv(f"{provider.upper()}_MODEL_NAME", "mixtral-8x7b-32768")

    def generate_video(self, prompt: str) -> Optional[GenerationJob]:
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            if data.get("choices"):
                return GenerationJob(
                    id="api-generated",
                    status="completed",
                    output_url=data["choices"][0]["message"]["content"],
                )
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
        return None
