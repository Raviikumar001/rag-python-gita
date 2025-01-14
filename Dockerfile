# Dockerfile
FROM python:3.11-slim

# Set environment variables from your current time and user
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY main.py .

# Create necessary directories
RUN mkdir -p /app/data/processed/faiss_index \
    /app/data/processed/chunks \
    /app/data/raw

# Cloud Run uses PORT environment variable
ENV PORT 8080

# Command to run FastAPI with uvicorn
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}