#!/bin/bash
# scripts/rebuild.sh - Helper to rebuild and restart the Docker containers

echo "Stopping existing containers..."
docker-compose down

echo "Removing old Qdrant data to force re-indexing (optional)..."
# Uncomment the next line if you want to wipe the vector DB and start fresh
# docker volume rm rag-python-gita_qdrant_data

echo "Building and starting..."
docker-compose up --build -d

echo ""
echo "Containers starting. First boot takes 3-5 minutes for:"
echo "  - Processing gita.md into chunks"
echo "  - Generating embeddings via Gemini API"
echo "  - Storing vectors in Qdrant"
echo ""
echo "Tail logs:"
echo "  docker-compose logs -f"
echo ""
echo "Check health (wait ~3 minutes):"
echo "  curl http://localhost:8080/health"
