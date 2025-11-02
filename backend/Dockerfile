FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (robust: force IPv4, retry loops, minimal packages)
RUN set -eux; \
    # Retry apt-get update a few times (force IPv4 to avoid transient IPv6/DNS issues)
    for i in 1 2 3; do \
      apt-get update -o Acquire::ForceIPv4=true && break || sleep 5; \
    done; \
    # Install required packages with retries and minimal extras
    for i in 1 2 3; do \
      apt-get install -y --no-install-recommends \
        ca-certificates \
        dnsutils \
        gcc \
        g++ \
        libpq-dev \
        curl && break || sleep 5; \
    done; \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose.yml)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
