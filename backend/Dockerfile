FROM python:3.11-slim

WORKDIR /app

# Install uv for faster package installation
RUN pip install --upgrade pip && pip install uv

COPY requirements.txt .

RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
