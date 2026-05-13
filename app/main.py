# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import get_settings
from app.state import app_state
from app.utils.logger import get_logger
from app.services.gemini import GeminiService
from app.services.cache import create_cache
from app.core.embedder import DocumentEmbedder
from app.core.searcher import QdrantSearcher
from app.core.chunker import DocumentChunker
from app.services.rag_engine import RAGEngine
from app.api.routes import router

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Gita RAG API v2.0...")

    # Initialize services
    cache = create_cache(settings.redis_url)
    gemini = GeminiService(
        api_key=settings.gemini_api_key, model=settings.gemini_model
    )
    embedder = DocumentEmbedder(
        gemini, cache, model=settings.gemini_embedding_model
    )
    searcher = QdrantSearcher(
        path=settings.qdrant_path,
        collection_name=settings.qdrant_collection,
        vector_size=3072,
    )

    # Reranker is lazy-loaded on first search request for fast startup
    if settings.enable_reranker:
        logger.info(f"Reranker configured: {settings.reranker_model} (lazy-loaded)")
    else:
        logger.info("Reranker disabled by configuration")

    # Index documents if collection is empty
    if searcher.count() == 0:
        logger.info("Qdrant collection empty. Processing gita.md...")
        chunker = DocumentChunker()
        chunks = chunker.process_documentation("./data/raw/gita.md")

        texts = [c["content"] for c in chunks]
        embeddings = await embedder.embed_batch(texts)

        ids = [c["id"] for c in chunks]
        payloads = [
            {"content": c["content"], "metadata": c.get("metadata", {})}
            for c in chunks
        ]
        searcher.add_points(ids, embeddings, payloads)
        logger.info(f"Indexed {len(chunks)} chunks into Qdrant")
    else:
        logger.info(f"Qdrant collection ready with {searcher.count()} vectors")

    rag_engine = RAGEngine(gemini, embedder, searcher, cache)
    app_state["rag"] = rag_engine
    app_state["gemini"] = gemini
    app_state["cache"] = cache

    logger.info("Gita RAG API is ready!")
    yield

    # Shutdown
    logger.info("Shutting down...")
    await gemini.close()
    await cache.close()
    logger.info("Cleanup complete")


app = FastAPI(
    title="Gita AI RAG API",
    description="High-performance Retrieval-Augmented Generation API for the Bhagavad Gita",
    version="2.0.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Direct health endpoint (also available via router at /api/v1/health)
@app.get("/health")
async def health_check():
    from datetime import datetime, timezone

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0",
    }


# Routes
app.include_router(router, prefix="/api/v1")
