"""Application settings using Pydantic v2."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses Pydantic v2 settings management with automatic .env file loading.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),  # Disable protected namespace warnings
    )

    # Application
    app_name: str = Field(default="Media Generation Platform", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_secret_key: str = Field(alias="API_SECRET_KEY")
    api_rate_limit: int = Field(default=100, alias="API_RATE_LIMIT")

    # Database
    database_url: str = Field(alias="DATABASE_URL")
    database_pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    # Redis
    redis_url: str = Field(alias="REDIS_URL")
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")

    # Celery
    celery_broker_url: str = Field(alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(alias="CELERY_RESULT_BACKEND")
    celery_task_always_eager: bool = Field(default=False, alias="CELERY_TASK_ALWAYS_EAGER")

    # Storage (S3/MinIO)
    s3_endpoint_url: Optional[str] = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_access_key_id: str = Field(alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(alias="S3_SECRET_ACCESS_KEY")
    s3_bucket_name: str = Field(alias="S3_BUCKET_NAME")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    use_ssl: bool = Field(default=True, alias="USE_SSL")

    # CDN
    cdn_url: Optional[str] = Field(default=None, alias="CDN_URL")

    # AI Models
    hunyuan_model_path: str = Field(default="/models/hunyuan", alias="HUNYUAN_MODEL_PATH")
    moneyprinter_path: str = Field(default="/models/moneyprinter", alias="MONEYPRINTER_PATH")
    model_cache_dir: str = Field(default="/tmp/model_cache", alias="MODEL_CACHE_DIR")

    # Content Generation
    max_image_size: int = Field(default=2048, alias="MAX_IMAGE_SIZE")
    max_video_duration: int = Field(default=300, alias="MAX_VIDEO_DURATION")
    default_image_format: str = Field(default="png", alias="DEFAULT_IMAGE_FORMAT")
    default_video_format: str = Field(default="mp4", alias="DEFAULT_VIDEO_FORMAT")

    # Video Generation Settings
    video_resolution_width: int = Field(default=1080, alias="VIDEO_RESOLUTION_WIDTH")
    video_resolution_height: int = Field(default=1920, alias="VIDEO_RESOLUTION_HEIGHT")
    video_fps: int = Field(default=30, alias="VIDEO_FPS")
    video_bitrate: str = Field(default="5000k", alias="VIDEO_BITRATE")
    video_codec: str = Field(default="libx264", alias="VIDEO_CODEC")
    audio_codec: str = Field(default="aac", alias="AUDIO_CODEC")

    # Text-to-Speech Settings
    tts_provider: str = Field(default="edge", alias="TTS_PROVIDER")  # edge, openai, azure
    tts_voice: str = Field(default="en-US-AriaNeural", alias="TTS_VOICE")
    tts_rate: str = Field(default="+0%", alias="TTS_RATE")  # Speech rate adjustment
    tts_volume: str = Field(default="+0%", alias="TTS_VOLUME")  # Volume adjustment

    # LLM Settings (for script generation)
    llm_provider: str = Field(
        default="openrouter", alias="LLM_PROVIDER"
    )  # ollama, openai, or openrouter

    # Ollama Settings (local LLM)
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL")
    ollama_temperature: float = Field(default=0.7, alias="OLLAMA_TEMPERATURE")
    ollama_max_tokens: int = Field(default=2000, alias="OLLAMA_MAX_TOKENS")

    # OpenAI Settings (alternative LLM provider)
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.7, alias="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=2000, alias="OPENAI_MAX_TOKENS")

    # OpenRouter Settings (unified LLM gateway)
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="google/gemini-2.5-flash", alias="OPENROUTER_MODEL")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    openrouter_temperature: float = Field(default=0.7, alias="OPENROUTER_TEMPERATURE")
    openrouter_max_tokens: int = Field(default=2000, alias="OPENROUTER_MAX_TOKENS")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=10, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=100, alias="RATE_LIMIT_PER_HOUR")

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000", alias="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS", alias="CORS_ALLOW_METHODS"
    )
    cors_allow_headers: str = Field(default="*", alias="CORS_ALLOW_HEADERS")

    # Monitoring & Observability
    prometheus_enabled: bool = Field(default=True, alias="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(default=9090, alias="PROMETHEUS_PORT")
    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_service_name: str = Field(default="media-gen-api", alias="OTEL_SERVICE_NAME")

    # Security
    nsfw_detection_enabled: bool = Field(default=True, alias="NSFW_DETECTION_ENABLED")
    nsfw_threshold: float = Field(default=0.7, alias="NSFW_THRESHOLD")
    content_moderation_enabled: bool = Field(default=True, alias="CONTENT_MODERATION_ENABLED")

    # Webhooks
    webhook_timeout: int = Field(default=30, alias="WEBHOOK_TIMEOUT")
    webhook_max_retries: int = Field(default=3, alias="WEBHOOK_MAX_RETRIES")
    webhook_retry_delay: int = Field(default=60, alias="WEBHOOK_RETRY_DELAY")

    # Background Tasks
    task_timeout: int = Field(default=3600, alias="TASK_TIMEOUT")
    task_max_retries: int = Field(default=3, alias="TASK_MAX_RETRIES")
    task_retry_delay: int = Field(default=300, alias="TASK_RETRY_DELAY")

    # Development
    reload: bool = Field(default=False, alias="RELOAD")
    workers: int = Field(default=1, alias="WORKERS")

    # Testing
    test_database_url: Optional[str] = Field(default=None, alias="TEST_DATABASE_URL")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"debug", "info", "warning", "error", "critical"}
        if v.lower() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.lower()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = {"development", "staging", "production"}
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v.lower()

    @field_validator("nsfw_threshold")
    @classmethod
    def validate_nsfw_threshold(cls, v: float) -> float:
        """Validate NSFW threshold."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("NSFW threshold must be between 0.0 and 1.0")
        return v

    def get_cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def get_cors_methods_list(self) -> list[str]:
        """Get CORS methods as a list."""
        return [method.strip() for method in self.cors_allow_methods.split(",")]

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once.

    Returns:
        Settings instance
    """
    return Settings()
