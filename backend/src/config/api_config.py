from dataclasses import dataclass
from typing import Optional

@dataclass
class OpenRouterConfig:
    base_url: str
    api_key: str
    model_name: str
    max_tokens: int

@dataclass
class GroqConfig:
    base_url: str
    api_key: str
    model_name: str
    max_tokens: int

class APIConfig:
    def __init__(self, provider: str):
        self.provider = provider
        if provider == "openrouter":
            self.config = OpenRouterConfig(
                base_url="https://openrouter.ai/api/v1",
                api_key="",
                model_name="",
                max_tokens=500
            )
        elif provider == "groq":
            self.config = GroqConfig(
                base_url="https://api.groq.com/openai/v1",
                api_key="",
                model_name="mixtral-8x7b-32768",
                max_tokens=500
            )
