# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .

# Install build dependencies and create virtual environment
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create necessary directories and set permissions
RUN mkdir -p data/processed/faiss_index data/processed/chunks logs && \
    chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "main.py"]