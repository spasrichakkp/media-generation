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

