FROM python:3.11

WORKDIR /app

# Install uv for faster package installation
RUN pip install --upgrade pip && pip install uv

COPY requirements.txt .

# Install dependencies
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/chroma data/logs

# Expose API port
EXPOSE 8001

# Run FastAPI server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
