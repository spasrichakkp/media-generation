# Media Generation Platform

A production-ready backend API for AI-powered video generation with clean hexagonal architecture, asynchronous processing, and scalable infrastructure.

---

## 1. Project Overview and Purpose

The Media Generation Platform is a containerized backend service designed for automated video content generation using AI and modern software engineering practices.

**Core Capabilities:**
- **Video Generation**: Text-to-video using MoviePy, LLM script generation (Ollama/OpenAI), and text-to-speech (Edge TTS)
- **Asynchronous Job Processing**: Celery-based task queue with Redis broker for scalable, non-blocking execution
- **Clean Architecture**: Hexagonal (Ports & Adapters) pattern with clear separation between domain, application, infrastructure, and API layers
- **RESTful API**: FastAPI-powered with automatic OpenAPI documentation, authentication, and comprehensive error handling
- **Object Storage**: S3-compatible storage (AWS S3 or MinIO) for generated media assets
- **Production Ready**: Health checks, structured logging, monitoring hooks, and Docker/Compose deployment

**Architecture Layers:**
- **Domain**: Core business entities (GenerationJob, User, GeneratedContent) and repository interfaces
- **Application**: Use cases (CreateJob, GetJobStatus, CancelJob, ListJobs) and DTOs
- **Infrastructure**: Adapters for database (PostgreSQL via SQLAlchemy), cache (Redis), storage (S3), and AI services (MoviePy video generator)
- **API**: FastAPI REST endpoints with authentication, validation, and error handling

**Tech Stack:**
- Python 3.11+, FastAPI, Celery, SQLAlchemy, Pydantic
- PostgreSQL 16, Redis 7, MinIO (or AWS S3)
- MoviePy, Edge TTS, OpenAI/Ollama LLM integration

---

## 2. Prerequisites and Dependencies

**Required:**
- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Python 3.11+** (only for local development without Docker)
- **PostgreSQL 16+** (provided via Docker Compose)
- **Redis 7.0+** (provided via Docker Compose)
- **MinIO** or AWS S3 (MinIO provided via Docker Compose)

**Optional:**
- **Ollama** (for local LLM) or **OpenAI API key** (for cloud LLM)
- **Kubernetes** (for production orchestration)
- **Poetry** or **pip** (for local Python dependency management)

**System Requirements:**
- 2+ CPU cores
- 4GB+ RAM (8GB+ recommended for video generation)
- 10GB+ free disk space

---

## 3. Installation Instructions

### Quick Start with Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd media-generation

# 2. Create environment file for backend
cp backend/.env.example backend/.env

# 3. Edit backend/.env and set required variables (minimum):
#    API_SECRET_KEY=<generate with: openssl rand -hex 32>
#    Other defaults are pre-configured in docker-compose.yml

# 4. Start all services
docker-compose up -d

# 5. Run database migrations
docker-compose exec api alembic upgrade head

# 6. Verify health
curl http://localhost:8000/health
```

**Services Started:**
- API Server: http://localhost:8000 (FastAPI + Swagger docs at /docs)
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- MinIO: http://localhost:9000 (API), http://localhost:9001 (Console - minioadmin/minioadmin)
- Celery Worker: Processes video generation jobs
- Flower (Celery Monitor): http://localhost:5555

### Local Development (Without Docker)

```bash
# 1. Start external services only
docker-compose up -d postgres redis minio minio-init

# 2. Install Python dependencies
cd backend
pip install -r requirements.txt

# 3. Set environment variables
export API_SECRET_KEY="dev-secret-key"
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/media_generation"
export REDIS_URL="redis://localhost:6379/0"
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/1"
export S3_ENDPOINT_URL="http://localhost:9000"
export S3_ACCESS_KEY_ID="minioadmin"
export S3_SECRET_ACCESS_KEY="minioadmin"
export S3_BUCKET_NAME="media-generation"

# 4. Run migrations
alembic upgrade head

# 5. Start API server (Terminal 1)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 6. Start Celery worker (Terminal 2)
celery -A src.infrastructure.tasks.celery_app:celery_app worker \
  --loglevel=info --concurrency=2 -Q video_generation,default
```

---

## 4. Configuration Guide

### Environment Variables

**Required Variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `API_SECRET_KEY` | Secret key for API security (REQUIRED) | `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | Celery message broker (Redis) | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result storage (Redis) | `redis://localhost:6379/1` |
| `S3_ACCESS_KEY_ID` | S3/MinIO access key | `minioadmin` (local) / AWS key (prod) |
| `S3_SECRET_ACCESS_KEY` | S3/MinIO secret key | `minioadmin` (local) / AWS secret (prod) |
| `S3_BUCKET_NAME` | S3 bucket for media storage | `media-generation` |

**Optional Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_ENDPOINT_URL` | AWS S3 | Custom S3 endpoint (e.g., `http://minio:9000`) |
| `S3_REGION` | `us-east-1` | S3 region |
| `USE_SSL` | `true` | Use SSL for S3 (`false` for local MinIO) |
| `LLM_PROVIDER` | `ollama` | LLM provider: `ollama` or `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `OPENAI_API_KEY` | None | OpenAI API key (if using OpenAI) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `TTS_PROVIDER` | `edge` | Text-to-speech provider |
| `TTS_VOICE` | `en-US-AriaNeural` | TTS voice |
| `LOG_LEVEL` | `info` | Logging level: `debug`, `info`, `warning`, `error` |
| `ENVIRONMENT` | `development` | Environment: `development`, `staging`, `production` |

### Docker Compose Configuration

The `docker-compose.yml` file includes default configurations for local development. For production, override with environment-specific values or use Docker secrets.

---

## 5. Usage Examples

### API Authentication

All endpoints (except `/health`) require authentication via API key header:

```bash
X-API-Key: your-api-key-here
```

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "api": "healthy",
    "database": "healthy"
  }
}
```

### Create a Video Generation Job

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "content_type": "video",
    "prompt": "Create a 30-second promotional video about a new smartwatch with fitness tracking features",
    "model_name": "moviepy-basic",
    "parameters": {
      "duration": 30,
      "resolution": "1080x1920",
      "fps": 30
    }
  }'
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user-uuid",
  "content_type": "video",
  "prompt": "Create a 30-second promotional video...",
  "model_name": "moviepy-basic",
  "parameters": {"duration": 30, "resolution": "1080x1920", "fps": 30},
  "status": "queued",
  "priority": 5,
  "progress": null,
  "created_at": "2025-01-20T12:00:00Z",
  "updated_at": "2025-01-20T12:00:00Z",
  "started_at": null,
  "completed_at": null,
  "error_message": null,
  "retry_count": 0,
  "result_url": null
}
```

### Get Job Status

```bash
curl http://localhost:8000/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000 \
  -H "X-API-Key: your-api-key"
```

**Response (Processing):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "progress": 45,
  "started_at": "2025-01-20T12:00:05Z",
  ...
}
```

**Response (Completed):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 100,
  "completed_at": "2025-01-20T12:02:30Z",
  "result_url": "https://s3.amazonaws.com/media-generation/videos/123e4567.mp4",
  ...
}
```

### List User Jobs

```bash
curl "http://localhost:8000/api/v1/jobs?page=1&page_size=10&status=completed" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "jobs": [...],
  "total": 42,
  "page": 1,
  "page_size": 10,
  "has_next": true,
  "has_prev": false
}
```

### Cancel a Job

```bash
curl -X POST http://localhost:8000/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000/cancel \
  -H "X-API-Key: your-api-key"
```

### Interactive API Documentation

Visit http://localhost:8000/docs for Swagger UI with interactive API exploration and testing.

---

## 6. Docker Deployment Instructions

### Build Docker Image

```bash
cd backend
docker build -t media-gen-backend:latest .
```

### Run Single Container (Simple)

```bash
docker run --rm -p 8000:8000 \
  -e API_SECRET_KEY="your-secret-key" \
  -e DATABASE_URL="postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/media_generation" \
  -e REDIS_URL="redis://host.docker.internal:6379/0" \
  -e CELERY_BROKER_URL="redis://host.docker.internal:6379/0" \
  -e CELERY_RESULT_BACKEND="redis://host.docker.internal:6379/1" \
  -e S3_ENDPOINT_URL="http://host.docker.internal:9000" \
  -e S3_ACCESS_KEY_ID="minioadmin" \
  -e S3_SECRET_ACCESS_KEY="minioadmin" \
  -e S3_BUCKET_NAME="media-generation" \
  media-gen-backend:latest
```

### Docker Compose (Recommended for Full Stack)

#### Step 1: Start all services
```bash
# Start all services (API, Celery worker, PostgreSQL, Redis, MinIO)
docker-compose up -d

# Build and start all services (if changes were made to backend)
docker-compose up -d --build
```

#### Step 2: Run database migrations
```bash
# Apply database schema changes
docker-compose exec api alembic upgrade head
```

#### Step 3: Verify all services are healthy
```bash
# Check status of all services
docker-compose ps

# Expected output should show all services as "Up" and "healthy":
# media-generation-api-1             Up (healthy)
# media-generation-celery_worker-1   Up
# media-generation-db-1              Up (healthy)
# media-generation-redis-1           Up (healthy)
# media-generation-minio-1           Up (healthy)
```

#### Step 4: Check service logs
```bash
# View all logs
docker-compose logs

# Follow logs for specific service
docker-compose logs -f api               # API server logs
docker-compose logs -f celery_worker     # Celery worker logs
docker-compose logs -f db                # Database logs
docker-compose logs -f redis             # Redis logs
docker-compose logs -f minio             # MinIO logs

# View recent logs with tail
docker-compose logs --tail=50 api        # Last 50 lines of API logs
docker-compose logs --tail=100 celery_worker  # Last 100 lines of Celery logs

# Check only error logs
docker-compose logs api | grep -i error
docker-compose logs celery_worker | grep -i error
```

#### Step 5: Test Celery worker connectivity
```bash
# Execute test inside API container to verify Celery connection
docker-compose exec api python -c "
import sys
sys.path.append('/app')
from src.infrastructure.tasks.celery_app import celery_app

# Check if Celery workers are responsive
result = celery_app.control.inspect().stats()
if result:
    print('✅ Celery workers are running and responsive')
    print(f'Workers found: {list(result.keys())}')
else:
    print('⚠️ No Celery workers responded')
"
```

#### Step 6: Stop all services
```bash
# Stop all services
docker-compose down

# Stop and remove all data (WARNING: deletes database)
docker-compose down -v

# Rebuild and restart everything
docker-compose down && docker-compose up -d --build
```

### Production Deployment Checklist

- [ ] Set strong `API_SECRET_KEY` (not default)
- [ ] Configure production database with connection pooling
- [ ] Use AWS S3 (not MinIO) with proper IAM roles
- [ ] Enable SSL/TLS for all connections
- [ ] Configure CORS origins to production domains only
- [ ] Set `ENVIRONMENT=production` and `DEBUG=false`
- [ ] Configure rate limiting and quotas
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation (Loki/ELK)
- [ ] Enable automated backups for PostgreSQL
- [ ] Set up auto-scaling for API and workers
- [ ] Configure health checks and readiness probes
- [ ] Use secrets management (AWS Secrets Manager, Vault)

---

## 7. Video Generation Testing with cURL

### Prerequisites
- Services must be running (follow steps in Section 6)
- Database migrations completed
- API secret key configured

### Step 1: Generate an API Key
```bash
# Create a new API key by calling the registration endpoint
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123"
  }'
```

If registration is not available, use your configured API key from the environment.

### Step 2: Health Check
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "components": {
    "api": "healthy",
    "database": "healthy"
  }
}
```

### Step 3: Create a Video Generation Job
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "content_type": "video",
    "prompt": "A beautiful sunset over mountains with a serene lake in the foreground",
    "model_name": "moneyprinter-turbo",
    "parameters": {
      "duration": 10,
      "style": "cinematic",
      "tone": "peaceful"
    }
  }'
```

**Expected response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user-uuid",
  "content_type": "video",
  "prompt": "A beautiful sunset over mountains with a serene lake in the foreground",
  "model_name": "moneyprinter-turbo",
  "parameters": {"duration": 10, "style": "cinematic", "tone": "peaceful"},
  "status": "queued",
  "priority": 5,
  "progress": null,
  "created_at": "2025-01-20T12:00:00Z",
  "updated_at": "2025-01-20T12:00:00Z",
  "started_at": null,
  "completed_at": null,
  "error_message": null,
  "retry_count": 0,
  "result_url": null
}
```

### Step 4: Monitor Job Progress
```bash
curl http://localhost:8000/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000 \
  -H "X-API-Key: your-api-key-here"
```

**Response (Processing):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "progress": 45,
  "started_at": "2025-01-20T12:00:05Z",
  ...
}
```

**Response (Completed):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 100,
  "completed_at": "2025-01-20T12:02:30Z",
  "result_url": "http://localhost:9000/media-generation/videos/123e4567.mp4",
  ...
}
```

### Step 5: List User Jobs
```bash
curl "http://localhost:8000/api/v1/jobs?page=1&page_size=10&status=processing" \
  -H "X-API-Key: your-api-key-here"
```

### Step 6: Check Celery Worker Processing
Monitor the Celery worker logs to see real-time processing:

```bash
# In a separate terminal, watch Celery logs
docker-compose logs -f celery_worker
```

You should see logs similar to:
```
celery_worker-1  | 2025-11-15 09:12:17.218 | INFO | Starting video generation task for job c293abaf-577c-47b2-8320-ad51af254bd9
celery_worker-1  | 2025-11-15 09:12:18.042 | INFO | Step 1: Generating video script...
celery_worker-1  | 2025-11-15 09:12:34.625 | INFO | Script generated successfully (1787 characters)
```

### Step 7: Cancel a Job (if needed)
```bash
curl -X POST http://localhost:8000/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000/cancel \
  -H "X-API-Key: your-api-key-here"
```

### Testing Tips
- Check Celery logs after creating jobs to see if they're being processed
- Use the health endpoint to verify API status before testing
- Monitor job status at regular intervals to track progress
- Check database directly if needed: `docker-compose exec postgres psql -U postgres -d media_generation -c "SELECT * FROM generation_jobs;"`
- Access generated videos through MinIO at http://localhost:9001 (minioadmin/minioadmin)

### Common Test Scenarios
- Create a simple video job and verify it processes
- Create multiple jobs to test queue handling
- Cancel a job that is queued but not yet started
- Create a job with invalid parameters to test error handling
- Monitor progress updates during processing

---

## 7. Troubleshooting

### Common Issues

#### 1. API Won't Start: Missing API_SECRET_KEY

**Symptom:**
```
ValueError: API_SECRET_KEY is required
```

**Solution:**
```bash
# Generate a secure key
openssl rand -hex 32

# Set in .env or docker-compose.yml
API_SECRET_KEY=<generated-key>
```

#### 2. Database Connection Failed

**Symptom:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Verify connection string format
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

#### 3. Celery Worker Not Processing Jobs

**Symptom:**
Jobs stuck in "queued" status for minutes.

**Solution:**
```bash
# Check worker logs (note: service name is celery_worker, not worker)
docker-compose logs celery_worker

# Verify worker is running
docker-compose ps celery_worker

# Check Redis connection
docker-compose exec redis redis-cli ping
# Should return: PONG

# Restart worker
docker-compose restart celery_worker
```

#### 4. Jobs Fail Immediately

**Symptom:**
Job status changes to "failed" right after creation.

**Solution:**
```bash
# Check worker logs for errors
docker-compose logs worker | grep ERROR

# Common causes:
# - Missing LLM provider (Ollama not running or OpenAI key not set)
# - S3/MinIO connection failed
# - Insufficient disk space

# Verify Ollama (if using)
curl http://localhost:11434/api/tags

# Verify MinIO
curl http://localhost:9000/minio/health/live
```

#### 5. MinIO Connection Error

**Symptom:**
```
botocore.exceptions.EndpointConnectionError
```

**Solution:**
```bash
# Verify MinIO is running
docker-compose ps minio

# Check if bucket exists
docker-compose exec minio mc ls myminio/

# Recreate bucket
docker-compose exec minio mc mb myminio/media-generation --ignore-existing

# For local development, ensure USE_SSL=false
```

#### 6. Port Already in Use

**Symptom:**
```
Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use
```

**Solution:**
```bash
# Find process using port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port in docker-compose.yml
ports:
  - "8001:8000"  # Host:Container
```

#### 7. "No module named 'src'" Error

**Symptom:**
```
ModuleNotFoundError: No module named 'src'
```

**Solution:**
Ensure you're running commands from the correct directory:
```bash
# API should be started from backend/ directory
cd backend
uvicorn src.api.main:app --reload
```

### Debugging Commands

```bash
# Check all container statuses
docker-compose ps

# Follow logs for specific service
docker-compose logs -f api
docker-compose logs -f celery_worker  # Celery worker logs

# Execute command in container
docker-compose exec api python -c "from src.config import get_settings; print(get_settings())"

# Access PostgreSQL shell
docker-compose exec postgres psql -U postgres -d media_generation

# Access Redis CLI
docker-compose exec redis redis-cli

# Check job queue length
docker-compose exec redis redis-cli llen celery

# View recent jobs in database
docker-compose exec postgres psql -U postgres -d media_generation -c \
  "SELECT id, status, created_at FROM generation_jobs ORDER BY created_at DESC LIMIT 5;"
```

### Getting Help

- **Logs**: Always check `docker-compose logs -f` for errors
- **Documentation**: Visit http://localhost:8000/docs for API docs
- **Health Status**: Check http://localhost:8000/health
- **Celery Monitor**: Visit http://localhost:5555 for Flower dashboard

---

## 8. Contributing Guidelines

### Development Workflow

1. **Fork and Clone**
   ```bash
   git clone <your-fork-url>
   cd media-generation
   git checkout -b feature/your-feature-name
   ```

2. **Set Up Development Environment**
   ```bash
   cd backend
   pip install -r requirements-dev.txt
   pre-commit install  # Install git hooks (optional)
   ```

3. **Make Changes**
   - Follow hexagonal architecture patterns
   - Write tests for new features
   - Update documentation if needed

4. **Code Quality Checks**
   ```bash
   # Format code
   black src/ tests/

   # Lint code
   ruff check src/ tests/

   # Type checking
   mypy src/

   # Run tests
   pytest

   # Run with coverage
   pytest --cov=src --cov-report=html
   ```

5. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   git push origin feature/your-feature-name
   ```

6. **Open Pull Request**
   - Provide clear description of changes
   - Reference any related issues
   - Ensure CI checks pass

### Code Style

- **Python**: Follow PEP 8, use Black formatter (line length: 100)
- **Naming**: Use descriptive names (e.g., `GenerationJob`, not `Job`)
- **Type Hints**: All functions must have type annotations
- **Docstrings**: Use Google-style docstrings for public APIs

### Testing Guidelines

- **Unit Tests**: Test business logic in isolation (domain/application layers)
- **Integration Tests**: Test database and external services
- **E2E Tests**: Test complete API workflows
- **Coverage**: Aim for >80% code coverage

### Architecture Principles

- **Hexagonal Architecture**: Keep domain layer dependency-free
- **Single Responsibility**: Each class/function has one clear purpose
- **Dependency Injection**: Use constructor injection for dependencies
- **Repository Pattern**: All data access through repository interfaces

### Commit Message Convention

```
<type>: <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Example:**
```
feat: add video duration validation

Validate that video duration is between 1 and 300 seconds.
Raises ValidationError if out of range.

Closes #42
```

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

---

## License

MIT License - See LICENSE file for details.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/media-generation/issues)
- **Documentation**: http://localhost:8000/docs (when running)
- **Architecture**: See hexagonal architecture in `backend/src/` directory structure

---

**Built with FastAPI, Celery, and Hexagonal Architecture** 🚀