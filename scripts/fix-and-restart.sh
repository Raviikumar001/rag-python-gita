#!/bin/bash
# scripts/fix-and-restart.sh - Clean rebuild with latest rate limiting fixes

echo "=== Stopping containers ==="
docker-compose down

echo ""
echo "=== Removing old Qdrant data ==="
docker volume rm rag-python-gita_qdrant_data 2>/dev/null || echo "Volume already removed or not found"

echo ""
echo "=== Rebuilding image (no cache) ==="
docker-compose build --no-cache gita-assistant

echo ""
echo "=== Starting services ==="
docker-compose up -d

echo ""
echo "=== Watching logs. First boot takes 5-10 minutes due to: ==="
echo "  - Processing gita.md into chunks"
echo "  - Generating embeddings (with rate limiting delays between batches)"
echo "  - Storing vectors in Qdrant"
echo ""
echo "Wait for 'Gita RAG API is ready!' message..."
echo ""
docker-compose logs -f gita-assistant
