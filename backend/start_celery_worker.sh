#!/bin/bash

# Start Celery worker for video generation tasks
# Usage: ./start_celery_worker.sh

# Determine the virtual environment path
VENV_PATH="/Users/sahil-mac/ai/.venv"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "Please create a virtual environment first."
    exit 1
fi

# Export environment variables
export APP_NAME="Media Generation Platform"
export APP_VERSION="0.1.0"
export ENVIRONMENT="development"
export DEBUG="true"
export LOG_LEVEL="info"
export API_HOST="0.0.0.0"
export API_PORT="8000"
export API_SECRET_KEY="123e4567-e89b-12d3-a456-426614174000"
export API_RATE_LIMIT="100"
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/media_generation"
export DATABASE_POOL_SIZE="20"
export DATABASE_MAX_OVERFLOW="10"
export DATABASE_ECHO="false"
export REDIS_URL="redis://localhost:6379/0"
export REDIS_MAX_CONNECTIONS="50"
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/1"
export CELERY_TASK_ALWAYS_EAGER="false"
export S3_ENDPOINT_URL="http://localhost:9000"
export S3_ACCESS_KEY_ID="minioadmin"
export S3_SECRET_ACCESS_KEY="minioadmin"
export S3_BUCKET_NAME="media-generation"
export S3_REGION="us-east-1"
export USE_SSL="false"
export LLM_PROVIDER="ollama"
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="llama3.2"
export OLLAMA_TEMPERATURE="0.7"
export OLLAMA_MAX_TOKENS="2000"
export RELOAD="true"
export WORKERS="1"
export NSFW_DETECTION_ENABLED="false"
export CONTENT_MODERATION_ENABLED="false"
export CORS_ORIGINS="*"
export CORS_ALLOW_CREDENTIALS="true"
export CORS_ALLOW_METHODS="GET,POST,PUT,DELETE,OPTIONS"
export CORS_ALLOW_HEADERS="*"
export CDN_URL=""
export OPENAI_API_KEY=""
export TTS_PROVIDER="edge"
export TTS_VOICE="en-US-AriaNeural"
export TTS_RATE="+0%"
export TTS_VOLUME="+0%"
export VIDEO_RESOLUTION_WIDTH="1080"
export VIDEO_RESOLUTION_HEIGHT="1920"
export VIDEO_FPS="30"
export VIDEO_BITRATE="5000k"
export VIDEO_CODEC="libx264"
export AUDIO_CODEC="aac"
export MAX_IMAGE_SIZE="2048"
export MAX_VIDEO_DURATION="300"
export DEFAULT_IMAGE_FORMAT="png"
export DEFAULT_VIDEO_FORMAT="mp4"
export HUNYUAN_MODEL_PATH="/models/hunyuan"
export MONEYPRINTER_PATH="/models/moneyprinter"
export MODEL_CACHE_DIR="/tmp/model_cache"
export PROMETHEUS_ENABLED="false"
export OTEL_ENABLED="false"
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_SERVICE_NAME="media-gen-api"
export WEBHOOK_TIMEOUT="30"
export WEBHOOK_MAX_RETRIES="3"
export WEBHOOK_RETRY_DELAY="60"
export TASK_TIMEOUT="3600"
export TASK_MAX_RETRIES="3"
export TASK_RETRY_DELAY="300"
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/media_generation_test"
export RATE_LIMIT_ENABLED="false"
export RATE_LIMIT_PER_MINUTE="10"
export RATE_LIMIT_PER_HOUR="100"

echo "Starting Celery worker for Media Generation Platform..."
echo "=========================================="
echo ""
echo "Virtual environment: $VENV_PATH"
echo "Worker configuration:"
echo "  - Queue: video_generation, default"
echo "  - Concurrency: 2 workers"
echo "  - Log level: info"
echo ""
echo "Press Ctrl+C to stop the worker"
echo "=========================================="
echo ""

# Start Celery worker using the virtual environment's Python
$VENV_PATH/bin/celery -A src.infrastructure.tasks.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=video_generation,default \
    --max-tasks-per-child=50 \
    --time-limit=3600 \
    --soft-time-limit=3300
