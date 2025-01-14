# Dockerfile
FROM python:3.11-slim


ENV PYTHONUNBUFFERED=1


WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY src/ ./src/
COPY main.py .


RUN mkdir -p /app/data/processed/faiss_index \
    /app/data/processed/chunks \
    /app/data/raw


ENV PORT 8080


CMD exec uvicorn main:app --host 0.0.0.0 --port 8080